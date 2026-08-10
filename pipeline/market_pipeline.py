# Databricks notebook source
# MAGIC %md
# MAGIC # Market Research Copilot - Spark Pipeline
# MAGIC
# MAGIC End-to-end batch pipeline. Everything below the ingest step runs in Spark:
# MAGIC
# MAGIC 1. **Read** the `watchlist` table from Lakebase (JDBC) to get the ticker universe.
# MAGIC 2. **Ingest** daily OHLCV bars and news articles from the Massive API
# MAGIC    (driver-side and rate limited - the free tier allows 5 requests/minute).
# MAGIC 3. **Transform in Spark**: window functions compute daily returns, 5/20-day
# MAGIC    moving averages, 20-day realised volatility, a volume z-score, and drawdown
# MAGIC    from the trailing high.
# MAGIC 4. **Join in Spark**: news articles are joined to same-day price action to
# MAGIC    produce `news_price_signals` - headlines that coincided with material moves.
# MAGIC 5. **Embed in Spark**: article chunks are embedded with a pandas UDF, so the
# MAGIC    sentence-transformer runs distributed across executors rather than on the driver.
# MAGIC 6. **Write**: partitioned Delta tables in Unity Catalog (analytics) and an
# MAGIC    upsert into Lakebase via `foreachPartition` (serving).
# MAGIC
# MAGIC Delta is the analytics store; Lakebase is the operational store the app and
# MAGIC agent read from. Same data, two shapes, on purpose.

# COMMAND ----------

# DBTITLE 1,Install dependencies
# MAGIC %pip uninstall -y psycopg2 psycopg2-binary
# MAGIC %pip install -q 'databricks-sdk>=0.118.0' psycopg2-binary sentence-transformers trafilatura requests pandas

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Config
dbutils.widgets.text("catalog", "main", "Unity Catalog")
dbutils.widgets.text("schema", "market_research", "Delta schema")
dbutils.widgets.text("lookback_days", "90", "Days of daily bars to ingest")
dbutils.widgets.text("news_limit", "10", "Max news articles per ticker")
dbutils.widgets.text("embedding_model", "sentence-transformers/all-MiniLM-L6-v2", "Embedding model")
dbutils.widgets.text("max_requests_per_minute", "5", "Massive free-tier rate limit")
dbutils.widgets.text("chunk_size", "800", "Chunk size (chars)")
dbutils.widgets.text("chunk_overlap", "100", "Chunk overlap (chars)")
dbutils.widgets.text("move_threshold", "0.03", "Abs daily return counted as a material move")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
LOOKBACK_DAYS = int(dbutils.widgets.get("lookback_days"))
NEWS_LIMIT = int(dbutils.widgets.get("news_limit"))
EMBEDDING_MODEL_NAME = dbutils.widgets.get("embedding_model")
MAX_RPM = int(dbutils.widgets.get("max_requests_per_minute"))
CHUNK_SIZE = int(dbutils.widgets.get("chunk_size"))
CHUNK_OVERLAP = int(dbutils.widgets.get("chunk_overlap"))
MOVE_THRESHOLD = float(dbutils.widgets.get("move_threshold"))

EMBEDDING_DIM = 384 if "MiniLM" in EMBEDDING_MODEL_NAME or "bge-small" in EMBEDDING_MODEL_NAME else 768

spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
print(f"Delta target: {CATALOG}.{SCHEMA}   embedding dim: {EMBEDDING_DIM}")

# COMMAND ----------

# DBTITLE 1,Secrets and Lakebase connection
import base64
import json
import time
from datetime import date, datetime, timedelta, timezone

import psycopg2
import requests
from psycopg2.extras import execute_values


def _secret(scope: str, key: str) -> str:
    return base64.b64decode(dbutils.secrets.get(scope=scope, key=key)).decode("utf-8")


LAKEBASE_URL = _secret("database", "lakebase-url")
MASSIVE_API_KEY = _secret("massive", "api-key")
MASSIVE_BASE = "https://api.massive.com"


def lakebase_read(query: str):
    """Read a Lakebase table into a Spark DataFrame over JDBC."""
    from urllib.parse import urlparse

    u = urlparse(LAKEBASE_URL)
    jdbc = f"jdbc:postgresql://{u.hostname}:{u.port or 5432}{u.path}?sslmode=require"
    return (
        spark.read.format("jdbc")
        .option("url", jdbc)
        .option("driver", "org.postgresql.Driver")
        .option("user", u.username)
        .option("password", u.password)
        .option("query", query)
        .load()
    )


print("secrets loaded")

# COMMAND ----------

# MAGIC %md ## 1. Ticker universe from Lakebase

# COMMAND ----------

watchlist_df = lakebase_read("SELECT DISTINCT symbol FROM watchlist WHERE symbol IN ('AAPL', 'MSFT', 'NVDA')")
TICKERS = sorted(r["symbol"].strip().upper() for r in watchlist_df.collect())[:3]

if not TICKERS:
    TICKERS = ["AAPL", "MSFT", "NVDA"]
    print("watchlist empty - falling back to a default universe")

print(f"{len(TICKERS)} tickers: {', '.join(TICKERS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ingest from Massive (driver-side, rate limited)
# MAGIC
# MAGIC The free Massive tier permits 5 requests per minute, so this stays on the
# MAGIC driver with a throttle. Everything downstream is distributed.

# COMMAND ----------

_session = requests.Session()
_session.headers.update({"Authorization": f"Bearer {MASSIVE_API_KEY}"})
_last_call = [0.0]
_MIN_GAP = 60.0 / MAX_RPM


def massive_get(path: str, params: dict | None = None) -> dict:
    wait = _MIN_GAP - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    resp = _session.get(f"{MASSIVE_BASE}{path}", params=params, timeout=30)
    _last_call[0] = time.time()
    if resp.status_code == 429:
        time.sleep(20)
        return massive_get(path, params)
    resp.raise_for_status()
    return resp.json()


end = date.today()
start = end - timedelta(days=LOOKBACK_DAYS)

bar_rows, news_rows = [], []

for t in TICKERS:
    try:
        data = massive_get(
            f"/v2/aggs/ticker/{t}/range/1/day/{start.isoformat()}/{end.isoformat()}",
            {"adjusted": "true", "sort": "asc", "limit": 50000},
        )
        for r in data.get("results", []) or []:
            bar_rows.append({
                "ticker": t,
                "bar_date": datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc).date(),
                "open": float(r.get("o", 0.0)),
                "high": float(r.get("h", 0.0)),
                "low": float(r.get("l", 0.0)),
                "close": float(r.get("c", 0.0)),
                "volume": int(r.get("v", 0)),
                "vwap": float(r.get("vw", 0.0) or 0.0),
            })
    except Exception as e:  # noqa: BLE001 - one bad ticker must not kill the run
        print(f"  bars {t}: {e}")

    try:
        news = massive_get("/v2/reference/news", {
            "ticker": t, "limit": NEWS_LIMIT, "order": "desc", "sort": "published_utc",
        }).get("results", []) or []
        for a in news:
            insights = a.get("insights") or []
            sentiment = insights[0].get("sentiment") if insights else None
            reasoning = insights[0].get("sentiment_reasoning") if insights else None
            news_rows.append({
                "id": a.get("id"),
                "ticker": t,
                "title": a.get("title") or "",
                "description": a.get("description"),
                "author": a.get("author"),
                "article_url": a.get("article_url"),
                "publisher_name": (a.get("publisher") or {}).get("name"),
                "keywords": json.dumps(a.get("keywords") or []),
                "sentiment": sentiment,
                "sentiment_reasoning": reasoning,
                "published_utc": a.get("published_utc"),
                "payload": json.dumps(a),
            })
    except Exception as e:  # noqa: BLE001
        print(f"  news {t}: {e}")

print(f"ingested {len(bar_rows)} bars, {len(news_rows)} articles")

# COMMAND ----------

# MAGIC %md ## 3. Spark transform - technical features via window functions

# COMMAND ----------

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import (ArrayType, DateType, DoubleType, FloatType,
                               IntegerType, LongType, StringType, StructField,
                               StructType)

bars_schema = StructType([
    StructField("ticker", StringType()),
    StructField("bar_date", DateType()),
    StructField("open", DoubleType()),
    StructField("high", DoubleType()),
    StructField("low", DoubleType()),
    StructField("close", DoubleType()),
    StructField("volume", LongType()),
    StructField("vwap", DoubleType()),
])

bars = spark.createDataFrame(bar_rows, schema=bars_schema).dropDuplicates(["ticker", "bar_date"])
bars = bars.repartition(8, "ticker").cache()
print(f"bars partitions: {bars.rdd.getNumPartitions()}  rows: {bars.count()}")

(bars.write.mode("overwrite").format("delta")
     .partitionBy("ticker")
     .saveAsTable(f"{CATALOG}.{SCHEMA}.price_bars"))

# Per-ticker ordered windows
w_ticker = Window.partitionBy("ticker").orderBy("bar_date")
w_5 = w_ticker.rowsBetween(-4, 0)
w_20 = w_ticker.rowsBetween(-19, 0)
w_all = w_ticker.rowsBetween(Window.unboundedPreceding, 0)

metrics = (
    bars
    .withColumn("prev_close", F.lag("close").over(w_ticker))
    .withColumn("daily_return",
                F.when(F.col("prev_close") > 0,
                       (F.col("close") - F.col("prev_close")) / F.col("prev_close")))
    .withColumn("ma_5", F.avg("close").over(w_5))
    .withColumn("ma_20", F.avg("close").over(w_20))
    # 20-day realised volatility, annualised (252 trading days)
    .withColumn("volatility_20d", F.stddev("daily_return").over(w_20) * F.sqrt(F.lit(252.0)))
    .withColumn("vol_mean_20", F.avg("volume").over(w_20))
    .withColumn("vol_std_20", F.stddev("volume").over(w_20))
    .withColumn("volume_zscore_20d",
                F.when(F.col("vol_std_20") > 0,
                       (F.col("volume") - F.col("vol_mean_20")) / F.col("vol_std_20")))
    .withColumn("running_high", F.max("close").over(w_all))
    .withColumn("drawdown_from_high",
                F.when(F.col("running_high") > 0,
                       (F.col("close") - F.col("running_high")) / F.col("running_high")))
    .withColumn("trend",
                F.when(F.col("ma_5") > F.col("ma_20"), F.lit("up"))
                 .when(F.col("ma_5") < F.col("ma_20"), F.lit("down"))
                 .otherwise(F.lit("flat")))
    .select("ticker", "bar_date", "close", "daily_return", "ma_5", "ma_20",
            "volatility_20d", "volume_zscore_20d", "drawdown_from_high", "trend")
    .cache()
)

(metrics.write.mode("overwrite").format("delta")
        .partitionBy("ticker")
        .saveAsTable(f"{CATALOG}.{SCHEMA}.ticker_metrics"))

display(metrics.orderBy(F.col("bar_date").desc()).limit(10))

# COMMAND ----------

# MAGIC %md ## 4. Spark join - headlines against same-day price action

# COMMAND ----------

news_schema = StructType([
    StructField("id", StringType()),
    StructField("ticker", StringType()),
    StructField("title", StringType()),
    StructField("description", StringType()),
    StructField("author", StringType()),
    StructField("article_url", StringType()),
    StructField("publisher_name", StringType()),
    StructField("keywords", StringType()),
    StructField("sentiment", StringType()),
    StructField("sentiment_reasoning", StringType()),
    StructField("published_utc", StringType()),
    StructField("payload", StringType()),
])

news = (
    spark.createDataFrame(news_rows, schema=news_schema)
    .filter(F.col("id").isNotNull())
    .dropDuplicates(["id"])
    .withColumn("published_ts", F.to_timestamp("published_utc"))
    .withColumn("bar_date", F.to_date("published_ts"))
    .cache()
)
print(f"articles: {news.count()}")

(news.write.mode("overwrite").format("delta")
     .saveAsTable(f"{CATALOG}.{SCHEMA}.ticker_news_documents"))

signals = (
    news.alias("n")
    .join(metrics.alias("m"),
          (F.col("n.ticker") == F.col("m.ticker")) & (F.col("n.bar_date") == F.col("m.bar_date")),
          "inner")
    .withColumn("abs_return", F.abs(F.col("m.daily_return")))
    .withColumn("signal_strength",
                F.when(F.col("abs_return") >= MOVE_THRESHOLD * 2, F.lit("strong"))
                 .when(F.col("abs_return") >= MOVE_THRESHOLD, F.lit("material"))
                 .otherwise(F.lit("routine")))
    .select(
        F.col("n.id").alias("article_id"),
        F.col("n.ticker").alias("ticker"),
        F.col("n.bar_date").alias("bar_date"),
        F.col("n.title").alias("title"),
        F.col("n.sentiment").alias("sentiment"),
        F.col("m.daily_return").alias("daily_return"),
        F.col("abs_return"),
        F.col("m.volume_zscore_20d").alias("volume_zscore_20d"),
        F.col("signal_strength"),
    )
    .cache()
)

(signals.write.mode("overwrite").format("delta")
        .saveAsTable(f"{CATALOG}.{SCHEMA}.news_price_signals"))

print(f"signals: {signals.count()}")
display(signals.orderBy(F.col("abs_return").desc()).limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Spark embeddings - article bodies chunked and embedded on executors
# MAGIC
# MAGIC The sentence-transformer is loaded once per executor (module-level cache),
# MAGIC then applied with a pandas UDF so batches move as Arrow columns.

# COMMAND ----------

import pandas as pd
from pyspark.sql.functions import pandas_udf


@F.udf(returnType=StringType())
def fetch_body(url):
    """Strip nav/ads/boilerplate from the article HTML on the executor."""
    if not url:
        return None
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception:  # noqa: BLE001
        return None


@F.udf(returnType=ArrayType(StringType()))
def chunk_text(text):
    if not text:
        return []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    return [text[i:i + CHUNK_SIZE] for i in range(0, len(text), step)][:20]


bodies = (
    news.select("id", "ticker", "title", "description", "article_url")
    .repartition(16)
    .withColumn("body", fetch_body(F.col("article_url")))
    # Fall back to title + description when the body can't be extracted
    .withColumn("source_text",
                F.coalesce(F.col("body"),
                           F.concat_ws(". ", F.col("title"), F.col("description"))))
    .withColumn("chunks", chunk_text(F.col("source_text")))
    .select("id", "ticker", F.posexplode("chunks").alias("chunk_index", "chunk_text"))
    .filter(F.length("chunk_text") > 50)
)

_model = {}


@pandas_udf(ArrayType(FloatType()))
def embed(texts: pd.Series) -> pd.Series:
    from sentence_transformers import SentenceTransformer
    if "m" not in _model:
        _model["m"] = SentenceTransformer(EMBEDDING_MODEL_NAME)
    vectors = _model["m"].encode(
        texts.fillna("").tolist(), batch_size=32, show_progress_bar=False, normalize_embeddings=True
    )
    return pd.Series([v.tolist() for v in vectors])


chunk_embeddings = (
    bodies
    .withColumn("embedding", embed(F.col("chunk_text")))
    .withColumn("id", F.concat_ws(":", F.col("id"), F.col("chunk_index")))
    .withColumnRenamed("id", "chunk_id")
    .withColumn("model_name", F.lit(EMBEDDING_MODEL_NAME))
    .cache()
)

print(f"chunks embedded: {chunk_embeddings.count()}")

(chunk_embeddings.write.mode("overwrite").format("delta")
                 .saveAsTable(f"{CATALOG}.{SCHEMA}.ticker_news_chunk_embeddings"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6. Serve to Lakebase
# MAGIC
# MAGIC `foreachPartition` opens one Postgres connection per Spark partition and
# MAGIC batch-upserts with `execute_values`, so the write is distributed too.

# COMMAND ----------

def upsert_partition(sql: str):
    """Build a foreachPartition function that upserts rows with the given SQL."""

    def _run(rows):
        buf = [tuple(r) for r in rows]
        if not buf:
            return
        conn = psycopg2.connect(LAKEBASE_URL)
        try:
            with conn.cursor() as cur:
                execute_values(cur, sql, buf, page_size=500)
            conn.commit()
        finally:
            conn.close()

    return _run


PRICE_SQL = """
INSERT INTO price_bars (ticker, bar_date, open, high, low, close, volume, vwap)
VALUES %s
ON CONFLICT (ticker, bar_date) DO UPDATE SET
  open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low,
  close = EXCLUDED.close, volume = EXCLUDED.volume, vwap = EXCLUDED.vwap,
  ingested_at = now()
"""

METRICS_SQL = """
INSERT INTO ticker_metrics (ticker, bar_date, close, daily_return, ma_5, ma_20,
                            volatility_20d, volume_zscore_20d, drawdown_from_high, trend)
VALUES %s
ON CONFLICT (ticker, bar_date) DO UPDATE SET
  close = EXCLUDED.close, daily_return = EXCLUDED.daily_return,
  ma_5 = EXCLUDED.ma_5, ma_20 = EXCLUDED.ma_20,
  volatility_20d = EXCLUDED.volatility_20d,
  volume_zscore_20d = EXCLUDED.volume_zscore_20d,
  drawdown_from_high = EXCLUDED.drawdown_from_high,
  trend = EXCLUDED.trend, computed_at = now()
"""

NEWS_SQL = """
INSERT INTO ticker_news_documents (id, ticker, title, description, author, article_url,
                                   publisher_name, keywords, sentiment, sentiment_reasoning,
                                   published_utc, payload)
VALUES %s
ON CONFLICT (id) DO UPDATE SET
  title = EXCLUDED.title, description = EXCLUDED.description,
  sentiment = EXCLUDED.sentiment, synced_at = now()
"""

SIGNALS_SQL = """
INSERT INTO news_price_signals (article_id, ticker, bar_date, title, sentiment,
                                daily_return, abs_return, volume_zscore_20d, signal_strength)
VALUES %s
ON CONFLICT (article_id, bar_date) DO UPDATE SET
  daily_return = EXCLUDED.daily_return, abs_return = EXCLUDED.abs_return,
  signal_strength = EXCLUDED.signal_strength, computed_at = now()
"""

CHUNK_SQL = """
INSERT INTO ticker_news_chunk_embeddings (id, article_id, ticker, chunk_index,
                                          chunk_text, embedding, model_name)
VALUES %s
ON CONFLICT (id) DO UPDATE SET
  chunk_text = EXCLUDED.chunk_text, embedding = EXCLUDED.embedding, embedded_at = now()
"""

bars.select("ticker", "bar_date", "open", "high", "low", "close", "volume", "vwap") \
    .foreachPartition(upsert_partition(PRICE_SQL))

metrics.select("ticker", "bar_date", "close", "daily_return", "ma_5", "ma_20",
               "volatility_20d", "volume_zscore_20d", "drawdown_from_high", "trend") \
       .foreachPartition(upsert_partition(METRICS_SQL))

news.select("id", "ticker", "title", "description", "author", "article_url",
            "publisher_name", "keywords", "sentiment", "sentiment_reasoning",
            "published_utc", "payload") \
    .foreachPartition(upsert_partition(NEWS_SQL))

signals.foreachPartition(upsert_partition(SIGNALS_SQL))

# pgvector needs the literal '[0.1,0.2,...]' form, so format the array as a string
(chunk_embeddings
    .select(
        F.col("chunk_id").alias("id"),
        F.regexp_replace(F.col("chunk_id"), ":[0-9]+$", "").alias("article_id"),
        "ticker", "chunk_index", "chunk_text",
        F.concat(F.lit("["), F.concat_ws(",", F.col("embedding")), F.lit("]")).alias("embedding"),
        "model_name",
    )
    .foreachPartition(upsert_partition(CHUNK_SQL)))

print("Lakebase serving tables updated")

# COMMAND ----------

# MAGIC %md ## 7. Verify

# COMMAND ----------

conn = psycopg2.connect(LAKEBASE_URL)
with conn.cursor() as cur:
    for t in ["price_bars", "ticker_metrics", "ticker_news_documents",
              "news_price_signals", "ticker_news_chunk_embeddings"]:
        cur.execute(f"SELECT count(*) FROM {t}")
        print(f"  {t:<32} {cur.fetchone()[0]:>7} rows")
conn.close()

print("\nDelta tables:")
display(spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}"))
