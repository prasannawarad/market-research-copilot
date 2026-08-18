<!-- generated-by: gsd-doc-writer -->
# Market Research Copilot

An AI stock-market research assistant built on Databricks. A Spark pipeline
ingests market data and news, computes technical features and news/price
signals, and embeds article text for semantic retrieval. A Databricks App
gives a human the same view an AI agent has, and the agent reaches the same
data through an MCP server whose tools **read and write** back to the same
store — so a research conclusion the agent reaches shows up in the app,
not just in a chat transcript.

Originally built as the capstone for DataExpert.io Academy's *"The Rise of
the AI Data Engineer"* bootcamp, on top of the author's boot camp Days 1–3
([day 1](https://github.com/prasannawarad/databricks-lakebase-app-day-1-prasanna),
[day 2](https://github.com/prasannawarad/databricks-lakebase-app-day-2-prasanna),
[day 3](https://github.com/prasannawarad/databricks-lakebase-app-day-3-prasanna)).
`lakebase.py`, `massive_client.py`, and `setup_secrets.py` are carried over
unchanged; the Spark pipeline, the signals join, the research MCP tools, and
the frontend are new.

## Architecture

```
Massive API  ──►  Spark pipeline (pipeline/market_pipeline_serverless.py)
(bars + news)         │
                      ├─ window functions ─► returns, MA5/MA20, 20d volatility,
                      │                      volume z-score, drawdown, trend
                      ├─ join news × metrics ─► news_price_signals
                      ├─ pandas UDF ─► chunk embeddings (distributed)
                      │
                      ├──► Delta / Unity Catalog   (analytics, partitioned by ticker)
                      └──► Lakebase Postgres       (serving, pgvector + HNSW)
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
        app/ (Databricks App)         mcp_server/ (Databricks App)
        Flask + vanilla JS            FastMCP over streamable HTTP
        watchlist, semantic search,   11 tools, 4 of them writes
        signals, notes, reports              ▲
                                             │ MCP
                                    Agent Bricks agent
                                    (+ Day 3's Alpaca server for trades)
```

## Example in action

This is the part of the architecture that's hardest to get right: most
agent demos are read-only. Here, the agent's answer is persisted back to
the same Lakebase tables the human UI reads, and shows up there without a
redeploy.

**Question posed to the Agent Bricks agent:**

> "AMD fell 7% on August 5 despite positive coverage of its data center
> growth. Using the price metrics and news signals, explain the
> disconnect."

**What made this answerable:** the Spark pipeline's `news_price_signals`
join had already flagged that day's AMD move as `strong` — a large
same-day price drop coinciding with trading volume roughly 2.5 standard
deviations above normal, landing right after AMD reported record quarterly
revenue (Data Center segment revenue more than doubled to $6.7B).

**What the agent did:** it pulled about 30 days of price metrics via
`get_ticker_metrics`, retrieved the flagged move via
`get_news_price_signals`, and searched the article corpus semantically via
`search_ticker_news` rather than by keyword. Its answer, taken verbatim
from the deployed app's Agent Reports tab:

> "The disconnect between AMD's positive data center growth and its stock
> price decline can be explained by the company's flat gross margin
> guidance for Q3 and nearly tripled capital spending, which is pressuring
> profitability. Additionally, the announcement that SpaceX would use
> Nvidia's AI chips exclusively raised investor concerns about AMD's
> competitive position in the AI market."

The answer cited several fool.com articles surfaced by the semantic search,
not just the headline that prompted the question.

**The write-back:** the agent then called `save_analysis_report`, which
wrote the row to Lakebase's `analysis_reports` table. It appeared in the
app's Agent Reports tab after a refresh — the same round trip described in
Runbook step 8, now demonstrated on a real research question instead of a
smoke test.

## Capstone requirements

| Requirement | Where it lives |
|---|---|
| Spark data pipeline | `pipeline/market_pipeline_serverless.py` — window functions, a DataFrame join, a pandas UDF, partitioned Delta writes, and a distributed upsert to Lakebase |
| Third-party API | Massive (daily aggregates + news); Alpaca paper trading via the Day 3 server |
| Unstructured data | Article bodies extracted with trafilatura, chunked, embedded with all-MiniLM-L6-v2, stored in pgvector with an HNSW index |
| Databricks App frontend | `app/` — watchlist with live metrics, semantic search, signals table, notes, agent reports |
| AI agent that does things | `mcp_server/research_mcp_server.py` — 7 read tools and 4 write tools (`add_to_watchlist`, `remove_from_watchlist`, `save_research_note`, `save_analysis_report`) |

## What the Spark job actually computes

Not a `for` loop with a Spark wrapper. Per ticker, ordered by date:

- `daily_return` — `lag` over a per-ticker window
- `ma_5`, `ma_20` — rolling averages over `rowsBetween(-4,0)` and `(-19,0)`
- `volatility_20d` — 20-day return stddev, annualised by √252
- `volume_zscore_20d` — volume against its own trailing mean and stddev
- `drawdown_from_high` — close against a running max over an unbounded window
- `trend` — MA5 vs MA20 crossover state (`up` / `down` / flat)
- `news_price_signals` — inner join of articles to same-day metrics, bucketed
  `strong` / `material` / `routine` by absolute move against a configurable
  threshold

## Why Lakebase writes go through a generated SQL file

Databricks serverless compute blocks JDBC writes to Lakebase and psycopg2
connections crash the driver kernel if opened directly during the Spark
job. Instead, `emit()` (`pipeline/market_pipeline_serverless.py`) batches
each target table's rows into `INSERT ... ON CONFLICT DO UPDATE`
statements and writes them to a SQL file in a Unity Catalog volume; that
file is then run to load Lakebase. It's a workaround for a serverless
constraint, not a stylistic choice — see the module's header comment for
the full list of serverless limitations this pipeline works around (no
`.cache()`, no executor outbound internet, no JDBC writes).

## Lakebase tables

`watchlist`, `ticker_news_documents`, `ticker_news_chunk_embeddings`,
`price_bars`, `ticker_metrics`, `news_price_signals`, `research_notes`,
`analysis_reports`, `user_visits`. Full DDL in `sql/01_schema.sql`.

## Runbook

**1. Schema** — run `sql/01_schema.sql` in the Lakebase SQL editor.

**2. Secrets** — reuse Day 2's. Confirm both exist:
```bash
databricks secrets list-secrets database   # lakebase-url
databricks secrets list-secrets massive    # api-key
```

**3. Seed the watchlist** — the pipeline reads its ticker universe from
Lakebase, and falls back to AAPL/MSFT/NVDA/AMZN/GOOGL if empty:
```sql
INSERT INTO watchlist (email, symbol, updated_at) VALUES
  ('you@example.com','AAPL',now()), ('you@example.com','MSFT',now()),
  ('you@example.com','NVDA',now()), ('you@example.com','AMZN',now()),
  ('you@example.com','GOOGL',now())
ON CONFLICT (email, symbol) DO NOTHING;
```

**4. Run the pipeline** — import `pipeline/market_pipeline_serverless.py` as
a notebook, attach a cluster (DBR 15.4+), Run All. Roughly 8–12 minutes for
5 tickers; the Massive free tier is 5 requests/minute, so ingest is
throttled on purpose. The last cell prints row counts per table.

**5. Deploy the app**
```bash
databricks sync app /Workspace/Users/<you>/market-copilot-app
databricks apps deploy market-copilot --source-code-path /Workspace/Users/<you>/market-copilot-app
```

**6. Deploy the MCP server**
```bash
databricks sync mcp_server /Workspace/Users/<you>/market-copilot-mcp
databricks apps deploy market-copilot-mcp --source-code-path /Workspace/Users/<you>/market-copilot-mcp
```

**7. Wire up the agent** — in Agent Bricks, add an external MCP tool pointing
at `https://<mcp-app-url>/mcp`. Add Day 3's Alpaca server as a second tool
if you want the agent to trade as well as research.

**8. Verify** — `https://<app-url>/healthz` returns `{"status":"ok"}`. Then
in the app: add a ticker, run a semantic search, check the signals tab,
save a note. Ask the agent something like *"What's driving NVDA lately?
Save your conclusion as a research note."* — the note should appear in the
app's Notes tab without a redeploy. (See "Example in action" above for a
real end-to-end run of this loop.)

## Demo script (3 minutes)

1. Home page — the stats strip shows real row counts from the pipeline.
2. Watchlist — metrics came from Spark window functions, not from the app.
3. Semantic search — query by meaning, not keywords; note the similarity scores.
4. News signals — headlines joined to same-day moves, ranked by size.
5. Agent — ask it to research a ticker and save a note; refresh the Notes tab.
6. Delta side — `SELECT * FROM main.market_research.ticker_metrics` in a notebook.

## Notes and limits

- Massive's free tier is 5 requests/minute and end-of-day only, so ingest is
  batch by design. `max_requests_per_minute` is a widget if your tier differs.
- `fetch_body` runs `trafilatura` on executors; clusters without outbound
  internet fall back to title + description, which still embeds fine.
- Embedding dimension is 384. Change `VECTOR(384)` in the schema if you swap
  models — pgvector requires an exact match.
- No credentials in source or `app.yaml`; everything resolves through Databricks
  secret scopes at runtime.
- No automated test suite and no CI pipeline — verification is the manual
  runbook step above (`/healthz` plus a walkthrough of each UI tab).
