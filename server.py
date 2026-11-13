import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = os.environ.get("DB_PATH", "kswap.db")

def connect_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                coins INTEGER NOT NULL DEFAULT 0,
                energy INTEGER NOT NULL DEFAULT 1000
            )
        """)

@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "game": "K-SWAP",
        "database": "ready"
    })

@app.route("/player", methods=["POST"])
def get_player():
    data = request.get_json(silent=True) or {}
    player_id = str(data.get("player_id", "")).strip()

    if not player_id or len(player_id) > 100:
        return jsonify({"error": "Invalid player_id"}), 400

    with connect_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO players (player_id) VALUES (?)",
            (player_id,)
        )
        player = conn.execute(
            "SELECT player_id, coins, energy FROM players WHERE player_id = ?",
            (player_id,)
        ).fetchone()

    return jsonify(dict(player))

@app.route("/health")
def health():
    return jsonify({"ok": True})

init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
