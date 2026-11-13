
import os
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": "https://bucu8011-tech.github.io"
        }
    }
)

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

        if "coins" in data or "energy" in data:
            try:
                coins = int(data.get("coins", 0))
                energy = int(data.get("energy", 1000))

                if coins < 0 or energy < 0 or energy > 1000:
                    return jsonify({"error": "Invalid game values"}), 400

            except (ValueError, TypeError):
                return jsonify({"error": "Invalid game values"}), 400

            conn.execute(
                """
                UPDATE players
                SET coins = ?, energy = ?
                WHERE player_id = ?
                """,
                (coins, energy, player_id)
            )

        player = conn.execute(
            """
            SELECT player_id, coins, energy
            FROM players
            WHERE player_id = ?
            """,
            (player_id,)
        ).fetchone()

    return jsonify(dict(player))


@app.route("/health")
def health():
    return jsonify({"ok": True})


init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
