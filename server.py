
import os
import sqlite3
import json
import urllib.request
import urllib.error

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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")
GAME_URL = "https://bucu8011-tech.github.io/-K-SWAP/"


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


def telegram_api(method, data):
    if not BOT_TOKEN:
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as error:
        print("Telegram API error:", error)
        return None


def send_start_message(chat_id):
    telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": "Welcome to K-SWAP!\nTap and collect game points.",
        "reply_markup": {
            "inline_keyboard": [[
                {
                    "text": "PLAY K-SWAP",
                    "web_app": {"url": GAME_URL}
                }
            ]]
        }
    })


def configure_webhook():
    base_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/")

    if BOT_TOKEN and WEBHOOK_SECRET and base_url:
        result = telegram_api("setWebhook", {
            "url": base_url + "/telegram-webhook",
            "secret_token": WEBHOOK_SECRET
        })
        print("Telegram webhook setup:", result)


@app.route("/")
def home():
    return jsonify({
        "status": "online",
        "game": "K-SWAP",
        "database": "ready"
    })


@app.route("/player", methods=["GET"])
def read_player():
    player_id = request.args.get("player_id", "").strip()

    if not player_id or len(player_id) > 100:
        return jsonify({"error": "Invalid player_id"}), 400

    with connect_db() as conn:
        player = conn.execute(
            "SELECT player_id, coins, energy FROM players WHERE player_id = ?",
            (player_id,)
        ).fetchone()

    if player is None:
        return jsonify({"error": "Player not found"}), 404

    return jsonify(dict(player))


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


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    if not WEBHOOK_SECRET:
        return jsonify({"error": "Webhook not configured"}), 503

    supplied_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if supplied_secret != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    update = request.get_json(silent=True) or {}
    message = update.get("message", {})
    text = message.get("text", "")
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if chat_id and text.startswith("/start"):
        send_start_message(chat_id)

    return jsonify({"ok": True})


@app.route("/health")
def health():
    return jsonify({"ok": True})


init_db()
configure_webhook()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
