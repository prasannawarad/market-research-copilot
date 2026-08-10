# Databricks notebook source
# MAGIC %md
# MAGIC # Market Research Copilot — Spark Pipeline (Serverless / Free Edition)
# MAGIC
# MAGIC Rewritten for Databricks Free Edition, where **serverless is the only
# MAGIC compute available**. That imposes four hard constraints, and every design
# MAGIC choice below follows from one of them:
# MAGIC
# MAGIC | Constraint | Consequence |
# MAGIC |---|---|
# MAGIC | `.cache()` / `persist` unsupported | materialize through Delta and re-read instead |
# MAGIC | Executors have no outbound internet | all API calls and article fetches run on the driver |
# MAGIC | Executors have a read-only filesystem | the embedding model is staged to a UC Volume first |
# MAGIC | No JDBC writes, psycopg2 crashes the kernel | Lakebase is loaded from a generated SQL file |
# MAGIC
# MAGIC What still runs distributed: the window functions, the news/price join, and
# MAGIC the pandas UDF that embeds article chunks. Those are the Spark requirement
# MAGIC and they are untouched.
# MAGIC
# MAGIC **Run All, top to bottom.** No cell needs a decision from you.

# COMMAND ----------

# DBTITLE 1,Install dependencies
# MAGIC %pip install -q 'databricks-sdk>=0.30.0' sentence-transformers trafilatura requests pandas

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,Config
dbutils.widgets.text("catalog", "workspace", "Unity Catalog")
dbutils.widgets.text("schema", "market_research", "Delta schema")
dbutils.widgets.text("tickers", "AAPL,MSFT,NVDA", "Tickers (comma separated)")
dbutils.widgets.text("lookback_days", "90", "Days of daily bars")
dbutils.widgets.text("news_limit", "10", "Max news articles per ticker")
dbutils.widgets.text("embedding_model", "sentence-transformers/all-MiniLM-L6-v2", "Embedding model")
dbutils.widgets.text("max_requests_per_minute", "5", "Massive free-tier rate limit")
dbutils.widgets.text("max_tickers", "3", "Cap on tickers (Massive rate limit)")
dbutils.widgets.text("chunk_size", "800", "Chunk size (chars)")
dbutils.widgets.text("chunk_overlap", "100", "Chunk overlap (chars)")
dbutils.widgets.text("move_threshold", "0.03", "Abs daily return counted as material")
dbutils.widgets.dropdown("fetch_article_bodies", "false", ["true", "false"], "Fetch full article bodies")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
TICKER_OVERRIDE = [t.strip().upper() for t in dbutils.widgets.get("tickers").split(",") if t.strip()]
LOOKBACK_DAYS = int(dbutils.widgets.get("lookback_days"))
NEWS_LIMIT = int(dbutils.widgets.get("news_limit"))
EMBEDDING_MODEL_NAME = dbutils.widgets.get("embedding_model")
MAX_RPM = int(dbutils.widgets.get("max_requests_per_minute"))
MAX_TICKERS = int(dbutils.widgets.get("max_tickers"))
CHUNK_SIZE = int(dbutils.widgets.get("chunk_size"))
CHUNK_OVERLAP = int(dbutils.widgets.get("chunk_overlap"))
MOVE_THRESHOLD = float(dbutils.widgets.get("move_threshold"))
FETCH_BODIES = dbutils.widgets.get("fetch_article_bodies") == "true"

T = f"{CATALOG}.{SCHEMA}"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/artifacts"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {T}")
spark.sql(f"CREATE VOLUME IF NOT EXISTS {T}.artifacts")

print(f"Delta target : {T}")
print(f"Volume       : {VOLUME_PATH}")
print(f"Tickers      : {', '.join(TICKER_OVERRIDE)}")

# COMMAND ----------

# DBTITLE 1,Secrets
def _secret(scope: str, key: str) -> str:
    return dbutils.secrets.get(scope=scope, key=key)

LAKEBASE_URL = _secret("database", "lakebase-url")
MASSIVE_API_KEY = _secret("massive", "api-key")
MASSIVE_BASE = "https://api.massive.com"
print("secrets loaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Stage the embedding model into a UC Volume
# MAGIC
# MAGIC Executors have a read-only filesystem, so a Hugging Face download from a
# MAGIC worker fails with `OSError: Read-only file system`. The driver downloads
# MAGIC once into the Volume; workers then load from a path that already exists and
# MAGIC never touch the network.

# COMMAND ----------

import os
import shutil

MODEL_PATH = f"{VOLUME_PATH}/minilm-l6-v2"

os.environ["HF_HOME"] = "/tmp/hf"
os.environ["HF_HUB_CACHE"] = "/tmp/hf/hub"
os.environ["HF_HUB_DISABLE_XET"] = "1"          # xet cache is what blows up on read-only FS
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.makedirs("/tmp/hf/hub", exist_ok=True)

if not os.path.exists(f"{MODEL_PATH}/config.json"):
    from sentence_transformers import SentenceTransformer
    _staged = SentenceTransformer(EMBEDDING_MODEL_NAME, cache_folder="/tmp/hf")
    _staged.save("/tmp/minilm")
    shutil.copytree("/tmp/minilm", MODEL_PATH, dirs_exist_ok=True)
    del _staged
    print("model downloaded and staged")
else:
    print("model already staged")

_files = sorted(os.listdir(MODEL_PATH))
print(MODEL_PATH, "->", _files[:8])
assert "config.json" in _files, "model staging failed - stop and check Volume permissions"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Ticker universe
# MAGIC
# MAGIC Serverless blocks JDBC reads against Lakebase on some workspaces, so the
# MAGIC watchlist read is attempted and falls back to the widget list.

# COMMAND ----------

TICKERS = TICKER_OVERRIDE

try:
    from urllib.parse import urlparse
    u = urlparse(LAKEBASE_URL)
    jdbc = f"jdbc:postgresql://{u.hostname}:{u.port or 5432}{u.path}?sslmode=require"
    wl = (spark.read.format("jdbc")
          .option("url", jdbc).option("driver", "org.postgresql.Driver")
          .option("user", u.username).option("password", u.password)
          .option("query", "SELECT DISTINCT symbol FROM watchlist").load())
    found = sorted({r["symbol"].strip().upper() for r in wl.collect()})
    if found:
        TICKERS = found
        print(f"universe from Lakebase watchlist ({len(found)} symbols)")
except Exception as e:
    print(f"watchlist read unavailable ({type(e).__name__}) - using widget list")

# Cap for the Massive free tier: 2 calls per ticker at 5 requests/minute, so
# every extra ticker costs ~24 seconds of pure throttle. Raise max_tickers
# once you are not against a deadline.
if len(TICKERS) > MAX_TICKERS:
    print(f"capping {len(TICKERS)} -> {MAX_TICKERS} "
          f"(would cost ~{len(TICKERS) * 24}s in throttle)")
    TICKERS = TICKERS[:MAX_TICKERS]

print(f"{len(TICKERS)} tickers: {', '.join(TICKERS)}")
print(f"estimated ingest time: ~{len(TICKERS) * 24}s of API throttle")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Ingest from Massive (driver only)
# MAGIC
# MAGIC Executors have no outbound internet on serverless, so every HTTP call in
# MAGIC this notebook happens here. The free tier allows 5 requests/minute, so this
# MAGIC is throttled deliberately — expect roughly 25 seconds per ticker.

# COMMAND ----------

import json
import time
from datetime import date, datetime, timedelta, timezone

import requests

_session = requests.Session()
_session.headers.update({"Authorization": f"Bearer {MASSIVE_API_KEY}"})
_last = [0.0]
_GAP = 60.0 / MAX_RPM


def massive_get(path, params=None, _retries=2):
    wait = _GAP - (time.time() - _last[0])
    if wait > 0:
        time.sleep(wait)
    r = _session.get(f"{MASSIVE_BASE}{path}", params=params, timeout=30)
    _last[0] = time.time()
    if r.status_code == 429 and _retries:
        time.sleep(20)
        return massive_get(path, params, _retries - 1)
    r.raise_for_status()
    return r.json()


end, start = date.today(), date.today() - timedelta(days=LOOKBACK_DAYS)
bar_rows, news_rows = [], []

for t in TICKERS:
    try:
        data = massive_get(
            f"/v2/aggs/ticker/{t}/range/1/day/{start.isoformat()}/{end.isoformat()}",
            {"adjusted": "true", "sort": "asc", "limit": 50000},
        )
        for r in data.get("results") or []:
            bar_rows.append({
                "ticker": t,
                "bar_date": datetime.fromtimestamp(r["t"] / 1000, tz=timezone.utc).date(),
                "open": float(r.get("o") or 0), "high": float(r.get("h") or 0),
                "low": float(r.get("l") or 0), "close": float(r.get("c") or 0),
                "volume": int(r.get("v") or 0), "vwap": float(r.get("vw") or 0),
            })
    except Exception as e:
        print(f"  bars {t}: {e}")

    try:
        for a in massive_get("/v2/reference/news", {
            "ticker": t, "limit": NEWS_LIMIT, "order": "desc", "sort": "published_utc",
        }).get("results") or []:
            ins = (a.get("insights") or [{}])[0]
            news_rows.append({
                "id": a.get("id"), "ticker": t,
                "title": a.get("title") or "", "description": a.get("description"),
                "author": a.get("author"), "article_url": a.get("article_url"),
                "publisher_name": (a.get("publisher") or {}).get("name"),
                "keywords": json.dumps(a.get("keywords") or []),
                "sentiment": ins.get("sentiment"),
                "sentiment_reasoning": ins.get("sentiment_reasoning"),
                "published_utc": a.get("published_utc"), "payload": json.dumps(a),
            })
    except Exception as e:
        print(f"  news {t}: {e}")

print(f"ingested {len(bar_rows)} bars, {len(news_rows)} articles")
assert bar_rows, "no bars returned - check the Massive key and ticker symbols"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Article bodies (driver, optional)
# MAGIC
# MAGIC Off by default. `trafilatura` on an executor silently returns nothing, so
# MAGIC it runs here with a thread pool when enabled. With it off, chunks come from
# MAGIC title + description, which still embeds and searches fine.

# COMMAND ----------

bodies_by_id = {}

if FETCH_BODIES:
    from concurrent.futures import ThreadPoolExecutor

    def _body(row):
        try:
            import trafilatura
            html = trafilatura.fetch_url(row["article_url"])
            if not html:
                return row["id"], None
            return row["id"], trafilatura.extract(
                html, include_comments=False, include_tables=False)
        except Exception:
            return row["id"], None

    targets = [r for r in news_rows if r.get("article_url")]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for aid, text in pool.map(_body, targets):
            if text:
                bodies_by_id[aid] = text
    print(f"fetched {len(bodies_by_id)}/{len(targets)} article bodies")
else:
    print("body fetch disabled - embedding title + description")

for r in news_rows:
    body = bodies_by_id.get(r["id"])
    r["source_text"] = body or ". ".join(
        x for x in [r.get("title"), r.get("description")] if x)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Spark transform — technical features via window functions
# MAGIC
# MAGIC No `.cache()` on serverless. Each stage writes to Delta and the next stage
# MAGIC reads that table back, which materializes the result exactly once.

# COMMAND ----------

from pyspark.sql import Window
from pyspark.sql import functions as F
from pyspark.sql.types import (ArrayType, DateType, DoubleType, FloatType,
                               IntegerType, LongType, StringType, StructField,
                               StructType)

bars_schema = StructType([
    StructField("ticker", StringType()), StructField("bar_date", DateType()),
    StructField("open", DoubleType()), StructField("high", DoubleType()),
    StructField("low", DoubleType()), StructField("close", DoubleType()),
    StructField("volume", LongType()), StructField("vwap", DoubleType()),
])

(spark.createDataFrame(bar_rows, schema=bars_schema)
      .dropDuplicates(["ticker", "bar_date"])
      .repartition(8, "ticker")
      .write.mode("overwrite").format("delta")
      .saveAsTable(f"{T}.price_bars"))

bars = spark.table(f"{T}.price_bars")
print(f"price_bars: {bars.count()} rows")

w = Window.partitionBy("ticker").orderBy("bar_date")

metrics_df = (
    bars
    .withColumn("prev_close", F.lag("close").over(w))
    .withColumn("daily_return",
                F.when(F.col("prev_close") > 0,
                       (F.col("close") - F.col("prev_close")) / F.col("prev_close")))
    .withColumn("ma_5", F.avg("close").over(w.rowsBetween(-4, 0)))
    .withColumn("ma_20", F.avg("close").over(w.rowsBetween(-19, 0)))
    .withColumn("volatility_20d",
                F.stddev("daily_return").over(w.rowsBetween(-19, 0)) * F.sqrt(F.lit(252.0)))
    .withColumn("vol_mean_20", F.avg("volume").over(w.rowsBetween(-19, 0)))
    .withColumn("vol_std_20", F.stddev("volume").over(w.rowsBetween(-19, 0)))
    .withColumn("volume_zscore_20d",
                F.when(F.col("vol_std_20") > 0,
                       (F.col("volume") - F.col("vol_mean_20")) / F.col("vol_std_20")))
    .withColumn("running_high",
                F.max("close").over(w.rowsBetween(Window.unboundedPreceding, 0)))
    .withColumn("drawdown_from_high",
                F.when(F.col("running_high") > 0,
                       (F.col("close") - F.col("running_high")) / F.col("running_high")))
    .withColumn("trend",
                F.when(F.col("ma_5") > F.col("ma_20"), F.lit("up"))
                 .when(F.col("ma_5") < F.col("ma_20"), F.lit("down"))
                 .otherwise(F.lit("flat")))
    .select("ticker", "bar_date", "close", "daily_return", "ma_5", "ma_20",
            "volatility_20d", "volume_zscore_20d", "drawdown_from_high", "trend")
)

metrics_df.write.mode("overwrite").format("delta").saveAsTable(f"{T}.ticker_metrics")
metrics = spark.table(f"{T}.ticker_metrics")
print(f"ticker_metrics: {metrics.count()} rows")
display(metrics.orderBy(F.col("bar_date").desc()).limit(10))

# COMMAND ----------

# MAGIC %md ## 6. Spark join — headlines against same-day price action

# COMMAND ----------

news_schema = StructType([
    StructField("id", StringType()), StructField("ticker", StringType()),
    StructField("title", StringType()), StructField("description", StringType()),
    StructField("author", StringType()), StructField("article_url", StringType()),
    StructField("publisher_name", StringType()), StructField("keywords", StringType()),
    StructField("sentiment", StringType()), StructField("sentiment_reasoning", StringType()),
    StructField("published_utc", StringType()), StructField("payload", StringType()),
    StructField("source_text", StringType()),
])

(spark.createDataFrame(news_rows, schema=news_schema)
      .filter(F.col("id").isNotNull())
      .dropDuplicates(["id"])
      .withColumn("bar_date", F.to_date(F.to_timestamp("published_utc")))
      .write.mode("overwrite").format("delta")
      .saveAsTable(f"{T}.ticker_news_documents"))

news = spark.table(f"{T}.ticker_news_documents")
print(f"articles: {news.count()}")

(news.alias("n")
     .join(metrics.alias("m"),
           (F.col("n.ticker") == F.col("m.ticker")) & (F.col("n.bar_date") == F.col("m.bar_date")),
           "inner")
     .withColumn("abs_return", F.abs(F.col("m.daily_return")))
     .withColumn("signal_strength",
                 F.when(F.col("abs_return") >= MOVE_THRESHOLD * 2, F.lit("strong"))
                  .when(F.col("abs_return") >= MOVE_THRESHOLD, F.lit("material"))
                  .otherwise(F.lit("routine")))
     .select(F.col("n.id").alias("article_id"), F.col("n.ticker").alias("ticker"),
             F.col("n.bar_date").alias("bar_date"), F.col("n.title").alias("title"),
             F.col("n.sentiment").alias("sentiment"),
             F.col("m.daily_return").alias("daily_return"), F.col("abs_return"),
             F.col("m.volume_zscore_20d").alias("volume_zscore_20d"), F.col("signal_strength"))
     .write.mode("overwrite").format("delta")
     .saveAsTable(f"{T}.news_price_signals"))

signals = spark.table(f"{T}.news_price_signals")
print(f"news_price_signals: {signals.count()}")
display(signals.orderBy(F.col("abs_return").desc()).limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7. Spark embeddings — pandas UDF on executors
# MAGIC
# MAGIC The model path is captured as a closure variable rather than a notebook
# MAGIC global; notebook globals do not always serialize into the UDF on
# MAGIC serverless, which surfaces as `NameError: name 'MODEL_PATH' is not defined`
# MAGIC inside the Python worker.

# COMMAND ----------

import pandas as pd
from pyspark.sql.functions import pandas_udf

_CHUNK, _OVER = CHUNK_SIZE, CHUNK_OVERLAP


@F.udf(returnType=ArrayType(StringType()))
def chunk_text(text):
    if not text:
        return []
    step = _CHUNK - _OVER
    return [text[i:i + _CHUNK] for i in range(0, len(text), step)][:20]


chunks = (
    news.select("id", "ticker", "source_text")
        .withColumn("chunks", chunk_text(F.col("source_text")))
        .select("id", "ticker", F.posexplode("chunks").alias("chunk_index", "chunk_text"))
        .filter(F.length("chunk_text") > 50)
        .repartition(8)
)

chunks.write.mode("overwrite").format("delta").saveAsTable(f"{T}.news_chunks_staging")
chunks = spark.table(f"{T}.news_chunks_staging")
n_chunks = chunks.count()
print(f"chunks to embed: {n_chunks}")

_model = {}


def _make_embed(model_dir: str):
    @pandas_udf(ArrayType(FloatType()))
    def _embed(texts: pd.Series) -> pd.Series:
        import os
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HOME"] = "/tmp/hf"
        os.environ["HF_HUB_DISABLE_XET"] = "1"
        from sentence_transformers import SentenceTransformer
        if "m" not in _model:
            _model["m"] = SentenceTransformer(model_dir)
        vecs = _model["m"].encode(texts.fillna("").tolist(), batch_size=32,
                                  show_progress_bar=False, normalize_embeddings=True)
        return pd.Series([v.tolist() for v in vecs])
    return _embed


embed = _make_embed(MODEL_PATH)

embedded = (
    chunks
    .withColumn("embedding", embed(F.col("chunk_text")))
    .withColumn("chunk_id", F.concat_ws(":", F.col("id"), F.col("chunk_index")))
    .withColumnRenamed("id", "article_id")
    .withColumn("model_name", F.lit(EMBEDDING_MODEL_NAME))
    .select("chunk_id", "article_id", "ticker", "chunk_index", "chunk_text",
            "embedding", "model_name")
)

try:
    (embedded.write.mode("overwrite").format("delta")
             .saveAsTable(f"{T}.ticker_news_chunk_embeddings"))
    print("embedded distributed via pandas UDF")
except Exception as exc:
    # Fallback: embed on the driver. Every other Spark operation is unaffected.
    print(f"distributed embedding failed ({type(exc).__name__}: {exc}) - falling back to driver")
    pdf = chunks.toPandas()
    from sentence_transformers import SentenceTransformer
    _m = SentenceTransformer(MODEL_PATH)
    pdf["embedding"] = [v.tolist() for v in _m.encode(
        pdf["chunk_text"].tolist(), batch_size=32, normalize_embeddings=True)]
    pdf["chunk_id"] = pdf["id"].astype(str) + ":" + pdf["chunk_index"].astype(str)
    pdf["model_name"] = EMBEDDING_MODEL_NAME
    pdf = pdf.rename(columns={"id": "article_id"})[
        ["chunk_id", "article_id", "ticker", "chunk_index", "chunk_text",
         "embedding", "model_name"]]
    (spark.createDataFrame(pdf).write.mode("overwrite").format("delta")
          .saveAsTable(f"{T}.ticker_news_chunk_embeddings"))

emb = spark.table(f"{T}.ticker_news_chunk_embeddings")
print(f"ticker_news_chunk_embeddings: {emb.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8. Serve to Lakebase
# MAGIC
# MAGIC Serverless blocks all three write paths that normally work here:
# MAGIC `foreachPartition` needs executor network access, `spark.write.jdbc`
# MAGIC returns `UNSUPPORTED_DATA_SOURCE_WRITE`, and driver-side `psycopg2` aborts
# MAGIC the Python kernel with SIGABRT.
# MAGIC
# MAGIC So the pipeline emits a SQL load file into the Volume instead. It is
# MAGIC idempotent (`ON CONFLICT DO UPDATE`), casts the vector column with
# MAGIC `::vector`, and runs in the Lakebase SQL editor in seconds.

# COMMAND ----------

from datetime import date as _date, datetime as _dt


def lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, (_date, _dt)):
        return "'" + v.isoformat() + "'"
    return "'" + str(v).replace("'", "''") + "'"


def emit(df, table, cols, conflict, updates, casts=None, batch=200):
    casts = casts or {}
    rows = df.select(*cols).collect()
    if not rows:
        return f"-- {table}: no rows\n\n"
    out = [f"-- {table}: {len(rows)} rows"]
    for i in range(0, len(rows), batch):
        values = []
        for r in rows[i:i + batch]:
            cells = []
            for c in cols:
                v = r[c]
                if c in casts and v is not None:
                    if casts[c] == "vector":
                        cells.append("'[" + ",".join(f"{float(x):.6f}" for x in v) + "]'::vector")
                    else:
                        cells.append(f"{lit(v)}::{casts[c]}")
                else:
                    cells.append(lit(v))
            values.append("(" + ",".join(cells) + ")")
        out.append(
            f"INSERT INTO {table} ({','.join(cols)}) VALUES\n" + ",\n".join(values) +
            f"\nON CONFLICT ({conflict}) DO UPDATE SET {updates};"
        )
    return "\n".join(out) + "\n\n"


parts = [
    "-- Market Research Copilot: Lakebase load\n"
    "-- Generated by the Spark pipeline. Idempotent; safe to re-run.\n\n",

    emit(bars, "price_bars",
         ["ticker", "bar_date", "open", "high", "low", "close", "volume", "vwap"],
         "ticker, bar_date",
         "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, "
         "close=EXCLUDED.close, volume=EXCLUDED.volume, vwap=EXCLUDED.vwap, ingested_at=now()"),

    emit(metrics, "ticker_metrics",
         ["ticker", "bar_date", "close", "daily_return", "ma_5", "ma_20",
          "volatility_20d", "volume_zscore_20d", "drawdown_from_high", "trend"],
         "ticker, bar_date",
         "close=EXCLUDED.close, daily_return=EXCLUDED.daily_return, ma_5=EXCLUDED.ma_5, "
         "ma_20=EXCLUDED.ma_20, volatility_20d=EXCLUDED.volatility_20d, "
         "volume_zscore_20d=EXCLUDED.volume_zscore_20d, "
         "drawdown_from_high=EXCLUDED.drawdown_from_high, trend=EXCLUDED.trend, computed_at=now()"),

    emit(news, "ticker_news_documents",
         ["id", "ticker", "title", "description", "author", "article_url",
          "publisher_name", "keywords", "sentiment", "sentiment_reasoning",
          "published_utc", "payload"],
         "id",
         "title=EXCLUDED.title, description=EXCLUDED.description, "
         "sentiment=EXCLUDED.sentiment, synced_at=now()",
         casts={"keywords": "jsonb", "payload": "jsonb", "published_utc": "timestamptz"}),

    emit(signals, "news_price_signals",
         ["article_id", "ticker", "bar_date", "title", "sentiment", "daily_return",
          "abs_return", "volume_zscore_20d", "signal_strength"],
         "article_id, bar_date",
         "daily_return=EXCLUDED.daily_return, abs_return=EXCLUDED.abs_return, "
         "signal_strength=EXCLUDED.signal_strength, computed_at=now()"),

    emit(emb.withColumnRenamed("chunk_id", "id"), "ticker_news_chunk_embeddings",
         ["id", "article_id", "ticker", "chunk_index", "chunk_text", "embedding", "model_name"],
         "id",
         "chunk_text=EXCLUDED.chunk_text, embedding=EXCLUDED.embedding, embedded_at=now()",
         casts={"embedding": "vector"}, batch=50),
]

SQL_OUT = f"{VOLUME_PATH}/lakebase_load.sql"
with open(SQL_OUT, "w") as f:
    f.write("".join(parts))

size = os.path.getsize(SQL_OUT)
print(f"wrote {SQL_OUT}  ({size:,} bytes)")
print("\nNext: Catalog -> {}.{} -> artifacts -> download lakebase_load.sql".format(CATALOG, SCHEMA))
print("Then paste it into the Lakebase SQL editor and run.")
if size > 2_000_000:
    print("\nWARNING: over 2MB - the SQL editor may struggle. Split on the '-- table:' comments.")

# COMMAND ----------

# MAGIC %md ## 9. Verify

# COMMAND ----------

print("Delta tables\n" + "-" * 46)
for t in ["price_bars", "ticker_metrics", "ticker_news_documents",
          "news_price_signals", "ticker_news_chunk_embeddings"]:
    print(f"  {t:<32} {spark.table(f'{T}.{t}').count():>7} rows")

print("\nSample metrics (Spark window output)")
display(spark.sql(f"""
    SELECT ticker, bar_date, ROUND(close,2) AS close,
           ROUND(daily_return*100,2) AS pct, ROUND(ma_5,2) AS ma_5, ROUND(ma_20,2) AS ma_20,
           ROUND(volatility_20d*100,1) AS vol_pct, trend
    FROM {T}.ticker_metrics ORDER BY bar_date DESC, ticker LIMIT 15
"""))

print("Load file ready at:", SQL_OUT)