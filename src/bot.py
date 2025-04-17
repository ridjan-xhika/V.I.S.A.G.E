import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import time
import opencv

load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the .env file")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! I am your bot. Use /help to see available commands.")

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Available commands:\n/start - Start the bot\n/help - Show this help message")

async def purge(update: Update, context: CallbackContext) -> None:
    bot = context.application.bot
    chat_id = update.message.chat_id

    await update.message.reply_text(f"Starting purge in chat: {chat_id}...")
    
    try:
        async for message in bot.get_chat_history(chat.id):
            try:
                await bot.delete_message(chat.id, message.message_id)
            except Exception as e:
                await update.message.reply_text(f"Error deleting message {message.message_id}: {e}")
    except Exception as e:
        await update.message.reply_text(f"Error accessing chat: {e}")

async def status(update: Update, context: CallbackContext) -> None:
    start = time.perf_counter()
    await update.message.reply_text("Bot is ruasync def nning and ready to assist you!")
    latence = time.perf_counter() - start
    await update.message.reply_text(f"Latency: {latence:.2f} seconds")

async def snapshot(update: Update, context: CallbackContext) -> None:


def run_bot():
    global app 
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("status", status))

    print("Bot is running...")
    app.run_polling()
