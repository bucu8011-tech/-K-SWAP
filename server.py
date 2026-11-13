
import os
import sqlite3
import json
import hmac
import hashlib
import urllib.parse
import secrets
import time
import urllib.request

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {
        "origins": "https://bucu8011-tech.github.io"
    }}
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
                telegram_id TEXT UNIQUE,
                coins INTEGER NOT NULL DEFAULT 0,
                energy INTEGER NOT NULL DEFAULT 1000
            )
        """)

        columns = [
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(players)"
            ).fetchall()
        ]

        if "telegram_id" not in columns:
            conn.execute(
                "ALTER TABLE players ADD COLUMN telegram_id TEXT"
            )

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_players_telegram_id
            ON players(telegram_id)
            WHERE telegram_id IS NOT NULL
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


def validate_init_data(init_data):
    if not BOT_TOKEN or not init_data:
        return None

    try:
        parsed = dict(
            urllib.parse.parse_qsl(
                init_data,
                keep_blank_values=True
            )
        )

        received_hash = parsed.pop("hash", "")
        if not received_hash:
            return None

        auth_date = int(parsed.get("auth_date", "0"))
        if auth_date <= 0 or abs(time.time() - auth_date) > 86400:
            return None

        data_check_string = "\n".join(
            f"{key}={value}"
            for key, value in sorted(parsed.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            BOT_TOKEN.encode("utf-8"),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(
            calculated_hash,
            received_hash
        ):
            return None

        user = json.loads(parsed.get("user", "{}"))
        if not user.get("id"):
            return None

        return user

    except Exception:
        return None


def get_authenticated_user():
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    return validate_init_data(init_data)


def configure_webhook():
    base_url = os.environ.get(
        "RENDER_EXTERNAL_URL", ""
    ).rstrip("/")

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


@app.route("/auth", methods=["POST"])
def authenticate():
    data = request.get_json(silent=True) or {}
    user = validate_init_data(
        data.get("init_data", "")
    )

    if not user:
        return jsonify({"error": "Telegram authentication failed"}), 401

    telegram_id = str(user["id"])

    with connect_db() as conn:
        player = conn.execute(
            """
            SELECT player_id, coins, energy
            FROM players
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        ).fetchone()

        if player is None:
            player_id = "K" + secrets.token_hex(5).upper()

            conn.execute(
                """
                INSERT INTO players
                (player_id, telegram_id, coins, energy)
                VALUES (?, ?, 0, 1000)
                """,
                (player_id, telegram_id)
            )

            player = conn.execute(
                """
                SELECT player_id, coins, energy
                FROM players
                WHERE telegram_id = ?
                """,
                (telegram_id,)
            ).fetchone()

    return jsonify(dict(player))


@app.route("/player", methods=["GET"])
def read_player():
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    telegram_id = str(user["id"])

    with connect_db() as conn:
        player = conn.execute(
            """
            SELECT player_id, coins, energy
            FROM players
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        ).fetchone()

    if player is None:
        return jsonify({"error": "Player not found"}), 404

    return jsonify(dict(player))


@app.route("/player", methods=["POST"])
def save_player():
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    telegram_id = str(user["id"])
    data = request.get_json(silent=True) or {}

    try:
        coins = int(data.get("coins"))
        energy = int(data.get("energy"))

        if coins < 0 or energy < 0 or energy > 1000:
            raise ValueError()

    except (ValueError, TypeError):
        return jsonify({"error": "Invalid game values"}), 400

    with connect_db() as conn:
        conn.execute(
            """
            UPDATE players
            SET coins = ?, energy = ?
            WHERE telegram_id = ?
            """,
            (coins, energy, telegram_id)
        )

        player = conn.execute(
            """
            SELECT player_id, coins, energy
            FROM players
            WHERE telegram_id = ?
            """,
            (telegram_id,)
        ).fetchone()

    if player is None:
        return jsonify({"error": "Player not found"}), 404

    return jsonify(dict(player))


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


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    if not WEBHOOK_SECRET:
        return jsonify({"error": "Webhook not configured"}), 503

    supplied_secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token", ""
    )

    if not hmac.compare_digest(
        supplied_secret,
        WEBHOOK_SECRET
    ):
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
