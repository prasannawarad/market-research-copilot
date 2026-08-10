-- ============================================================================
-- Market Research Copilot - Lakebase schema
-- Run this once against your Lakebase Postgres database before the pipeline.
-- Embedding dimension is 384 (sentence-transformers/all-MiniLM-L6-v2),
-- matching Day 2. Change VECTOR(384) if you swap models.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ── Carried over from Day 1-3 (created here if you're starting fresh) ───────

CREATE TABLE IF NOT EXISTS watchlist (
    id          SERIAL PRIMARY KEY,
    email       VARCHAR(255) NOT NULL,
    symbol      VARCHAR(10)  NOT NULL,
    latest_price DECIMAL(12, 2),
    updated_at  TIMESTAMPTZ,
    CONSTRAINT unique_user_symbol UNIQUE (email, symbol)
);
CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlist (symbol);

CREATE TABLE IF NOT EXISTS ticker_news_documents (
    id            TEXT PRIMARY KEY,
    ticker        TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT,
    author        TEXT,
    article_url   TEXT,
    publisher_name TEXT,
    keywords      JSONB,
    sentiment     TEXT,
    sentiment_reasoning TEXT,
    published_utc TIMESTAMPTZ,
    payload       JSONB NOT NULL,
    synced_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_news_ticker ON ticker_news_documents (ticker);

CREATE TABLE IF NOT EXISTS ticker_news_chunk_embeddings (
    id           TEXT PRIMARY KEY,
    article_id   TEXT NOT NULL,
    ticker       TEXT NOT NULL,
    chunk_index  INT  NOT NULL,
    chunk_text   TEXT NOT NULL,
    embedding    VECTOR(384) NOT NULL,
    model_name   TEXT NOT NULL,
    embedded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chunk_emb_hnsw
    ON ticker_news_chunk_embeddings USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_chunk_emb_ticker
    ON ticker_news_chunk_embeddings (ticker);

-- ── New for the capstone ───────────────────────────────────────────────────

-- Daily OHLCV bars, one row per ticker per session. Written by the Spark job.
CREATE TABLE IF NOT EXISTS price_bars (
    ticker      TEXT NOT NULL,
    bar_date    DATE NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      BIGINT,
    vwap        DOUBLE PRECISION,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, bar_date)
);
CREATE INDEX IF NOT EXISTS idx_price_bars_date ON price_bars (bar_date DESC);

-- Derived technical features. Every column here is produced by a Spark
-- window function, not by application code.
CREATE TABLE IF NOT EXISTS ticker_metrics (
    ticker            TEXT NOT NULL,
    bar_date          DATE NOT NULL,
    close             DOUBLE PRECISION,
    daily_return      DOUBLE PRECISION,
    ma_5              DOUBLE PRECISION,
    ma_20             DOUBLE PRECISION,
    volatility_20d    DOUBLE PRECISION,
    volume_zscore_20d DOUBLE PRECISION,
    drawdown_from_high DOUBLE PRECISION,
    trend             TEXT,
    computed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (ticker, bar_date)
);
CREATE INDEX IF NOT EXISTS idx_metrics_date ON ticker_metrics (bar_date DESC);

-- Output of the Spark join between news and same-day price action:
-- "which headlines coincided with a material move".
CREATE TABLE IF NOT EXISTS news_price_signals (
    article_id     TEXT NOT NULL,
    ticker         TEXT NOT NULL,
    bar_date       DATE NOT NULL,
    title          TEXT,
    sentiment      TEXT,
    daily_return   DOUBLE PRECISION,
    abs_return     DOUBLE PRECISION,
    volume_zscore_20d DOUBLE PRECISION,
    signal_strength TEXT,
    computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (article_id, bar_date)
);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON news_price_signals (ticker, bar_date DESC);

-- Agent + human write targets.
CREATE TABLE IF NOT EXISTS research_notes (
    note_id    SERIAL PRIMARY KEY,
    email      TEXT NOT NULL,
    ticker     TEXT NOT NULL,
    note_text  TEXT NOT NULL,
    author     TEXT NOT NULL DEFAULT 'human',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notes_ticker ON research_notes (ticker, created_at DESC);

CREATE TABLE IF NOT EXISTS analysis_reports (
    report_id   SERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    question    TEXT NOT NULL,
    answer      TEXT NOT NULL,
    citations   JSONB,
    model_name  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_reports_ticker ON analysis_reports (ticker, created_at DESC);

-- Tracks "what's changed since you last looked", for the agent's
-- flag_moves_since_last_visit tool.
CREATE TABLE IF NOT EXISTS user_visits (
    email       TEXT PRIMARY KEY,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Verify ─────────────────────────────────────────────────────────────────
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
