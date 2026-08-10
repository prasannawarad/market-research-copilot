"""
Market Research Copilot - Databricks App frontend.

Reads the Spark pipeline's output from Lakebase and lets a human do the same
things the agent can do: manage a watchlist, search news semantically, inspect
technical metrics, and save research notes.
"""

import json
import os

from flask import Flask, jsonify, render_template, request

from lakebase import run_query, run_returning, run_write
from massive_client import MassiveClient

app = Flask(__name__)

EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_EMAIL = os.environ.get("DEFAULT_EMAIL", "demo@databricks.local")

_model = None


def _embed(text: str) -> str:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL)
    vec = _model.encode([text], normalize_embeddings=True)[0]
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def _user() -> str:
    """Databricks Apps forwards the signed-in user in this header."""
    return request.headers.get("X-Forwarded-Email") or DEFAULT_EMAIL


@app.errorhandler(Exception)
def handle_exception(err):
    app.logger.exception("request failed")
    return jsonify({"error": str(err)}), 500


@app.route("/healthz")
def healthz():
    run_query("SELECT 1 AS ok")
    return jsonify({"status": "ok", "database": "connected"})


@app.route("/")
def index():
    return render_template("index.html", user=_user())


# ── Watchlist ──────────────────────────────────────────────────────────────

@app.route("/api/watchlist", methods=["GET"])
def get_watchlist():
    rows = run_query(
        """SELECT w.symbol, w.latest_price, w.updated_at,
                  m.close, m.daily_return, m.trend, m.volatility_20d,
                  m.drawdown_from_high, m.bar_date
           FROM watchlist w
           LEFT JOIN LATERAL (
               SELECT * FROM ticker_metrics t
               WHERE t.ticker = w.symbol ORDER BY t.bar_date DESC LIMIT 1
           ) m ON TRUE
           WHERE w.email = %s ORDER BY w.symbol""",
        (_user(),),
    )
    return jsonify(rows)


@app.route("/api/watchlist", methods=["POST"])
def add_watchlist():
    symbol = (request.json or {}).get("symbol", "").strip().upper()
    if not symbol or len(symbol) > 10 or not symbol.isalpha():
        return jsonify({"error": "Enter a valid ticker symbol, e.g. AAPL"}), 400

    price = None
    try:
        data = MassiveClient().get_latest_price(symbol)
        results = data.get("results") or []
        if results:
            price = results[0].get("c")
    except Exception as exc:  # noqa: BLE001 - a rate-limited quote must not block the add
        app.logger.warning("price lookup failed for %s: %s", symbol, exc)

    run_write(
        """INSERT INTO watchlist (email, symbol, latest_price, updated_at)
           VALUES (%s, %s, %s, now())
           ON CONFLICT (email, symbol)
           DO UPDATE SET latest_price = COALESCE(EXCLUDED.latest_price, watchlist.latest_price),
                         updated_at = now()""",
        (_user(), symbol, price),
    )
    return jsonify({"ok": True, "symbol": symbol, "latest_price": price}), 201


@app.route("/api/watchlist/<symbol>", methods=["DELETE"])
def remove_watchlist(symbol):
    n = run_write("DELETE FROM watchlist WHERE email = %s AND symbol = %s",
                  (_user(), symbol.upper()))
    return jsonify({"ok": n > 0, "removed": n})


# ── Metrics and signals (Spark output) ─────────────────────────────────────

@app.route("/api/metrics/<ticker>")
def metrics(ticker):
    days = int(request.args.get("days", 60))
    rows = run_query(
        """SELECT bar_date, close, daily_return, ma_5, ma_20, volatility_20d,
                  volume_zscore_20d, drawdown_from_high, trend
           FROM ticker_metrics WHERE ticker = %s
           ORDER BY bar_date DESC LIMIT %s""",
        (ticker.upper(), days),
    )
    return jsonify(rows)


@app.route("/api/signals")
def signals():
    ticker = request.args.get("ticker", "").upper()
    if ticker:
        rows = run_query(
            """SELECT ticker, bar_date, title, sentiment, daily_return,
                      volume_zscore_20d, signal_strength
               FROM news_price_signals WHERE ticker = %s
               ORDER BY abs_return DESC LIMIT 15""",
            (ticker,),
        )
    else:
        rows = run_query(
            """SELECT ticker, bar_date, title, sentiment, daily_return,
                      volume_zscore_20d, signal_strength
               FROM news_price_signals
               WHERE signal_strength IN ('strong', 'material')
               ORDER BY bar_date DESC, abs_return DESC LIMIT 15""",
        )
    return jsonify(rows)


# ── Semantic search over news chunks ───────────────────────────────────────

@app.route("/api/search", methods=["POST"])
def search():
    body = request.json or {}
    query = (body.get("query") or "").strip()
    ticker = (body.get("ticker") or "").strip().upper()
    if not query:
        return jsonify({"error": "Enter a search query"}), 400

    embedding = _embed(query)
    sql = """
        SELECT c.ticker, c.article_id, c.chunk_text,
               ROUND((1 - (c.embedding <=> %s::vector))::numeric, 4) AS similarity,
               d.title, d.article_url, d.publisher_name, d.published_utc, d.sentiment
        FROM ticker_news_chunk_embeddings c
        LEFT JOIN ticker_news_documents d ON d.id = c.article_id
        {where}
        ORDER BY c.embedding <=> %s::vector
        LIMIT 8
    """
    if ticker:
        rows = run_query(sql.format(where="WHERE c.ticker = %s"),
                         (embedding, ticker, embedding))
    else:
        rows = run_query(sql.format(where=""), (embedding, embedding))
    return jsonify(rows)


# ── Research notes and agent reports ───────────────────────────────────────

@app.route("/api/notes", methods=["GET"])
def list_notes():
    ticker = request.args.get("ticker", "").upper()
    if ticker:
        rows = run_query(
            """SELECT note_id, ticker, note_text, author, created_at
               FROM research_notes WHERE email = %s AND ticker = %s
               ORDER BY created_at DESC LIMIT 50""",
            (_user(), ticker),
        )
    else:
        rows = run_query(
            """SELECT note_id, ticker, note_text, author, created_at
               FROM research_notes WHERE email = %s
               ORDER BY created_at DESC LIMIT 50""",
            (_user(),),
        )
    return jsonify(rows)


@app.route("/api/notes", methods=["POST"])
def add_note():
    body = request.json or {}
    ticker = (body.get("ticker") or "").strip().upper()
    note_text = (body.get("note_text") or "").strip()
    if not ticker:
        return jsonify({"error": "Pick a ticker for this note"}), 400
    if not note_text:
        return jsonify({"error": "Write something before saving"}), 400
    rows = run_returning(
        """INSERT INTO research_notes (email, ticker, note_text, author)
           VALUES (%s, %s, %s, 'human') RETURNING note_id, created_at""",
        (_user(), ticker, note_text),
    )
    return jsonify({"ok": True, "note": rows[0] if rows else None}), 201


@app.route("/api/notes/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    n = run_write("DELETE FROM research_notes WHERE email = %s AND note_id = %s",
                  (_user(), note_id))
    return jsonify({"ok": n > 0})


@app.route("/api/reports")
def list_reports():
    rows = run_query(
        """SELECT report_id, ticker, question, answer, citations, model_name, created_at
           FROM analysis_reports WHERE email = %s
           ORDER BY created_at DESC LIMIT 25""",
        (_user(),),
    )
    for r in rows:
        if isinstance(r.get("citations"), str):
            try:
                r["citations"] = json.loads(r["citations"])
            except json.JSONDecodeError:
                pass
    return jsonify(rows)


# ── Pipeline stats for the header strip ────────────────────────────────────

@app.route("/api/stats")
def stats():
    rows = run_query(
        """SELECT
             (SELECT count(*) FROM price_bars)                    AS bars,
             (SELECT count(*) FROM ticker_metrics)                AS metrics,
             (SELECT count(*) FROM ticker_news_documents)         AS articles,
             (SELECT count(*) FROM ticker_news_chunk_embeddings)  AS chunks,
             (SELECT count(*) FROM news_price_signals
               WHERE signal_strength IN ('strong','material'))    AS signals,
             (SELECT max(bar_date) FROM ticker_metrics)           AS latest_bar"""
    )
    return jsonify(rows[0] if rows else {})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=False)
