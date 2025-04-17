import os
import io
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes
from telegram.constants import ChatAction
import time
from src import camera
import cv2

load_dotenv()
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the .env file")

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Hello! I am your bot. Use /help to see available commands.")

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
    "Available commands:\n"
    "/start – Initialize V.I.S.A.G.E and display available commands.\n"
    "/status – Show the current status of the V.I.S.A.G.E system.\n"
    "/snapshot – Capture and send a snapshot from the camera.\n"
    "/video – Record and send a short video clip.\n"
    "/live – Stream live video from the camera.\n"
    "/purge <n> – Delete the last n messages in this chat.\n"
    "/settings – Adjust V.I.S.A.G.E system configurations.\n"
    "/help – Show this help message."
)


from telegram import Update
from telegram.ext import CallbackContext

async def purge(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    chat_id = update.effective_chat.id
    try:
        n = int(context.args[0])
    except (IndexError, ValueError):
        n = 50
    last_id = update.message.message_id
    deleted = 0
    for msg_id in range(last_id - 1, last_id - n - 1, -1):
        try:
            await bot.delete_message(chat_id, msg_id)
            deleted += 1
        except:
            continue
    await bot.send_message(chat_id, f"Purged {deleted} messages.")

async def snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    frame = camera.take_snapshot()
    if frame is None:
        await update.message.reply_text("No snapshot available yet.")
        return

    success, buf = cv2.imencode('.jpg', frame)
    if not success:
        await update.message.reply_text("Failed to encode the snapshot.")
        return

    bio = io.BytesIO(buf.tobytes())
    bio.name = 'snapshot.jpg'
    bio.seek(0)
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio)

async def status(update: Update, context: CallbackContext) -> None:
    start = time.perf_counter()
    await update.message.reply_text("Bot is ruasync def nning and ready to assist you!")
    latence = time.perf_counter() - start
    await update.message.reply_text(f"Latency: {latence:.2f} seconds")

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Recording video…")
    try:
        clip_path = camera.record_clip(duration=5.0, fps=60)
    except Exception as e:
        await update.message.reply_text(f"Error recording clip: {e}")
        return

    with open(clip_path, 'rb') as f:
        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=f,
            caption="Here’s your 5 second clip!"
        )

    os.remove(clip_path)

def run_bot():
    global app
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("purge", purge))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("snapshot", snapshot))
    app.add_handler(CommandHandler("video", video))

    print("Bot is running...")
    app.run_polling()
