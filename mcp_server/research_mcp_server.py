"""
Market Research MCP server.

Exposes the tools a Databricks Agent Bricks agent uses to research tickers and
take real actions against Lakebase. Same hosting pattern as Day 3's Alpaca
server: FastMCP over streamable HTTP, deployed as a Databricks App.

Read tools:   search_ticker_news, get_ticker_metrics, compare_tickers,
              get_watchlist, get_research_notes, flag_moves_since_last_visit
Write tools:  add_to_watchlist, remove_from_watchlist, save_research_note,
              save_analysis_report

Add this server AND Day 3's Alpaca server to the same agent to get research
plus paper-trade execution in one loop.
"""

import json
import os
from datetime import datetime, timezone

from fastmcp import FastMCP

from lakebase import run_query, run_returning, run_write

mcp = FastMCP("market-research")

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_EMAIL = os.environ.get("DEFAULT_EMAIL", "waradprasanna@gmail.com")

_model = None


def _embed(text: str) -> str:
    """Embed a query and format it the way pgvector expects."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    vec = _model.encode([text], normalize_embeddings=True)[0]
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def _json(obj) -> str:
    return json.dumps(obj, default=str, indent=2)


# ── Read tools ─────────────────────────────────────────────────────────────

@mcp.tool
def search_ticker_news(query: str, ticker: str = "", limit: int = 5) -> str:
    """
    Semantic search across news article chunks using pgvector cosine similarity.

    Use this for meaning-based questions such as "companies exposed to rising
    interest rates" rather than exact keyword lookup. Optionally restrict to a
    single ticker. Returns the matching passages with their source article and
    similarity score, so answers can be cited.
    """
    embedding = _embed(query)
    sql = """
        SELECT c.ticker, c.article_id, c.chunk_text,
               1 - (c.embedding <=> %s::vector) AS similarity,
               d.title, d.article_url, d.published_utc, d.sentiment
        FROM ticker_news_chunk_embeddings c
        LEFT JOIN ticker_news_documents d ON d.id = c.article_id
        {where}
        ORDER BY c.embedding <=> %s::vector
        LIMIT %s
    """
    if ticker:
        rows = run_query(
            sql.format(where="WHERE c.ticker = %s"),
            (embedding, ticker.upper(), embedding, limit),
        )
    else:
        rows = run_query(sql.format(where=""), (embedding, embedding, limit))
    return _json(rows)


@mcp.tool
def get_ticker_metrics(ticker: str, days: int = 30) -> str:
    """
    Recent daily technical metrics for one ticker, newest first: close, daily
    return, 5- and 20-day moving averages, 20-day annualised volatility, volume
    z-score, drawdown from the trailing high, and trend (up/down/flat).

    All values are computed by the Spark pipeline, not at query time.

    daily_return, volatility_20d, and drawdown_from_high are raw decimals
    (0.0374 = 3.74%), NOT percentages — do not append a % sign to them.
    Each has a companion _pct field (daily_return_pct, volatility_20d_pct,
    drawdown_from_high_pct) already multiplied by 100 and rounded to 2dp —
    use those when rendering a percentage to the user.
    """
    rows = run_query(
        """SELECT bar_date, close, daily_return,
                  ROUND((daily_return * 100)::numeric, 2) AS daily_return_pct,
                  ma_5, ma_20, volatility_20d,
                  ROUND((volatility_20d * 100)::numeric, 2) AS volatility_20d_pct,
                  volume_zscore_20d, drawdown_from_high,
                  ROUND((drawdown_from_high * 100)::numeric, 2) AS drawdown_from_high_pct,
                  trend
           FROM ticker_metrics WHERE ticker = %s
           ORDER BY bar_date DESC LIMIT %s""",
        (ticker.upper(), days),
    )
    return _json(rows)


@mcp.tool
def compare_tickers(tickers: str, days: int = 30) -> str:
    """
    Compare several tickers side by side over a recent window. Pass a
    comma-separated list, e.g. "AAPL,MSFT,NVDA". Returns period return,
    average annualised volatility, latest close, and current trend for each.

    volatility_20d is a raw decimal (0.0374 = 3.74%) — do not append a %
    sign to it. volatility_20d_pct is the same value already multiplied by
    100 and rounded to 2dp; use that when rendering a percentage. Note
    period_return is a raw summed decimal too (not covered by a _pct twin
    here) — multiply by 100 yourself before showing it as a percentage.
    """
    symbols = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not symbols:
        return _json({"error": "no tickers supplied"})
    rows = run_query(
        """
        WITH windowed AS (
            SELECT ticker, bar_date, close, daily_return, volatility_20d, trend,
                   ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY bar_date DESC) AS rn
            FROM ticker_metrics
            WHERE ticker = ANY(%s)
        ), recent AS (
            SELECT * FROM windowed WHERE rn <= %s
        )
        SELECT ticker,
               MAX(CASE WHEN rn = 1 THEN close END)            AS latest_close,
               MAX(CASE WHEN rn = 1 THEN trend END)            AS trend,
               MAX(CASE WHEN rn = 1 THEN volatility_20d END)   AS volatility_20d,
               ROUND((MAX(CASE WHEN rn = 1 THEN volatility_20d END) * 100)::numeric, 2)
                                                                AS volatility_20d_pct,
               SUM(daily_return)                               AS period_return,
               COUNT(*)                                        AS trading_days
        FROM recent GROUP BY ticker ORDER BY period_return DESC NULLS LAST
        """,
        (symbols, days),
    )
    return _json(rows)


@mcp.tool
def get_news_price_signals(ticker: str = "", limit: int = 10) -> str:
    """
    Headlines that coincided with a material same-day price move, produced by
    the Spark join between news and price action. Each row carries the daily
    return, volume z-score, and a signal_strength of strong/material/routine.
    Rows are ordered strongest signal first, so read them top-down.
    Use this to explain *why* a stock moved.

    daily_return is a raw decimal (0.0374 = 3.74%) — do not append a % sign
    to it. daily_return_pct is the same value already multiplied by 100 and
    rounded to 2dp; use that when rendering a percentage.
    """
    rank = """CASE signal_strength
                WHEN 'strong' THEN 0 WHEN 'material' THEN 1 WHEN 'routine' THEN 2 ELSE 3 END"""
    if ticker:
        rows = run_query(
            f"""SELECT ticker, bar_date, title, sentiment, daily_return,
                      ROUND((daily_return * 100)::numeric, 2) AS daily_return_pct,
                      volume_zscore_20d, signal_strength
               FROM news_price_signals WHERE ticker = %s
               ORDER BY {rank}, abs_return DESC, bar_date DESC LIMIT %s""",
            (ticker.upper(), limit),
        )
    else:
        rows = run_query(
            f"""SELECT ticker, bar_date, title, sentiment, daily_return,
                      ROUND((daily_return * 100)::numeric, 2) AS daily_return_pct,
                      volume_zscore_20d, signal_strength
               FROM news_price_signals
               WHERE signal_strength IN ('strong', 'material')
               ORDER BY {rank}, abs_return DESC, bar_date DESC LIMIT %s""",
            (limit,),
        )
    return _json(rows)


@mcp.tool
def get_watchlist(email: str = "") -> str:
    """List the tickers currently on a user's watchlist."""
    rows = run_query(
        "SELECT symbol, latest_price, updated_at FROM watchlist WHERE email = %s ORDER BY symbol",
        (email or DEFAULT_EMAIL,),
    )
    return _json(rows)


@mcp.tool
def get_research_notes(ticker: str = "", email: str = "", limit: int = 20) -> str:
    """Retrieve saved research notes, optionally filtered to a single ticker."""
    if ticker:
        rows = run_query(
            """SELECT note_id, ticker, note_text, author, created_at
               FROM research_notes WHERE email = %s AND ticker = %s
               ORDER BY created_at DESC LIMIT %s""",
            (email or DEFAULT_EMAIL, ticker.upper(), limit),
        )
    else:
        rows = run_query(
            """SELECT note_id, ticker, note_text, author, created_at
               FROM research_notes WHERE email = %s
               ORDER BY created_at DESC LIMIT %s""",
            (email or DEFAULT_EMAIL, limit),
        )
    return _json(rows)


@mcp.tool
def flag_moves_since_last_visit(email: str = "") -> str:
    """
    What changed on the user's watchlist since they last checked in: notable
    moves and any headlines tied to them. Also advances their last-seen
    timestamp, so this both reads and writes.

    daily_return is a raw decimal (0.0374 = 3.74%) — do not append a % sign
    to it. daily_return_pct is the same value already multiplied by 100 and
    rounded to 2dp; use that when rendering a percentage.
    """
    who = email or DEFAULT_EMAIL
    seen = run_query("SELECT last_seen_at FROM user_visits WHERE email = %s", (who,))
    since = seen[0]["last_seen_at"] if seen else None

    moves = run_query(
        """SELECT m.ticker, m.bar_date, m.close, m.daily_return,
                  ROUND((m.daily_return * 100)::numeric, 2) AS daily_return_pct, m.trend
           FROM ticker_metrics m
           JOIN watchlist w ON w.symbol = m.ticker AND w.email = %s
           WHERE (%s::timestamptz IS NULL OR m.bar_date >= %s::timestamptz::date)
             AND abs(m.daily_return) >= 0.03
           ORDER BY abs(m.daily_return) DESC LIMIT 20""",
        (who, since, since),
    )
    headlines = run_query(
        """SELECT s.ticker, s.bar_date, s.title, s.daily_return,
                  ROUND((s.daily_return * 100)::numeric, 2) AS daily_return_pct, s.signal_strength
           FROM news_price_signals s
           JOIN watchlist w ON w.symbol = s.ticker AND w.email = %s
           WHERE s.signal_strength IN ('strong', 'material')
             AND (%s::timestamptz IS NULL OR s.bar_date >= %s::timestamptz::date)
           ORDER BY s.abs_return DESC LIMIT 20""",
        (who, since, since),
    )

    run_write(
        """INSERT INTO user_visits (email, last_seen_at) VALUES (%s, now())
           ON CONFLICT (email) DO UPDATE SET last_seen_at = now()""",
        (who,),
    )
    return _json({"since": since, "notable_moves": moves, "related_headlines": headlines})


# ── Write tools ────────────────────────────────────────────────────────────

@mcp.tool
def add_to_watchlist(symbol: str, email: str = "") -> str:
    """Add a ticker to the user's watchlist in Lakebase. This is a write."""
    sym = symbol.strip().upper()
    if not sym or len(sym) > 10:
        return _json({"ok": False, "error": f"invalid symbol: {symbol!r}"})
    run_write(
        """INSERT INTO watchlist (email, symbol, updated_at)
           VALUES (%s, %s, now())
           ON CONFLICT (email, symbol) DO UPDATE SET updated_at = now()""",
        (email or DEFAULT_EMAIL, sym),
    )
    return _json({"ok": True, "symbol": sym, "action": "added_to_watchlist"})


@mcp.tool
def remove_from_watchlist(symbol: str, email: str = "") -> str:
    """Remove a ticker from the user's watchlist. This is a write."""
    n = run_write(
        "DELETE FROM watchlist WHERE email = %s AND symbol = %s",
        (email or DEFAULT_EMAIL, symbol.strip().upper()),
    )
    return _json({"ok": n > 0, "symbol": symbol.strip().upper(), "removed": n})


@mcp.tool
def save_research_note(ticker: str, note_text: str, email: str = "") -> str:
    """
    Save a research note against a ticker. Use this to record a thesis, a risk,
    or a conclusion the user should see later. This is a write.
    """
    if not note_text.strip():
        return _json({"ok": False, "error": "note_text is empty"})
    rows = run_returning(
        """INSERT INTO research_notes (email, ticker, note_text, author)
           VALUES (%s, %s, %s, 'agent') RETURNING note_id, created_at""",
        (email or DEFAULT_EMAIL, ticker.strip().upper(), note_text.strip()),
    )
    return _json({"ok": True, "note": rows[0] if rows else None})

@mcp.tool
def save_analysis_report(
    ticker: str,
    question: str,
    answer: str,
    citations: str = "",
    email: str = "",
) -> str:
    """
    Persist a full analysis: the question asked, the answer given, and the
    article URLs or metrics it rests on. Pass citations as a JSON array string.
    This is a write.

    The authenticated/default app user owns the report. The email argument is
    kept for MCP compatibility but is not trusted for ownership.
    """
    try:
        cites = json.loads(citations) if citations else []
    except json.JSONDecodeError:
        cites = [citations]

    rows = run_returning(
        """INSERT INTO analysis_reports
           (email, ticker, question, answer, citations, model_name)
           VALUES (%s, %s, %s, %s, %s::jsonb, %s)
           RETURNING report_id, created_at""",
        (
            DEFAULT_EMAIL,
            ticker.strip().upper(),
            question,
            answer,
            json.dumps(cites),
            os.environ.get("AGENT_MODEL", "agent-bricks"),
        ),
    )

    return _json({"ok": True, "report": rows[0] if rows else None})


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
    )
