import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("bot")

TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("Missing TELEGRAM_TOKEN environment variable.")

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    name = user.first_name if user and user.first_name else "there"
    await update.message.reply_text(
        f"Hey {name}! I'm alive via long polling on Railway. Type /help."
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/start - Greet\n"
        "/echo <text> - Echoes your text\n"
        "Just send any message and I'll echo it."
    )

async def echo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        await update.message.reply_text(" ".join(context.args))
    else:
        await update.message.reply_text("Usage: /echo <text>")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Echo any non-command text message
    if update.message and update.message.text:
        await update.message.reply_text(update.message.text)

# --- App ---
def main() -> None:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("echo", echo_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))

    logger.info("Starting bot with long polling...")
    # This will automatically reconnect on transient network errors
    app.run_polling()

if __name__ == "__main__":
    main()