import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)

GAME_URL = "https://bucu8011-tech.github.io/-K-SWAP/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton(
            "PLAY K-SWAP",
            web_app=WebAppInfo(url=GAME_URL)
        )
    ]]

    await update.message.reply_text(
        "Welcome to K-SWAP!\nTap and collect game points.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    token = os.environ.get("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN is missing")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
