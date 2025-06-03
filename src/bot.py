import os
import io
import time
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes
from telegram.constants import ChatAction
import cv2
from pyngrok import ngrok

import main
try:
    from . import camera
except ImportError:
    import camera

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set")

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("🤖 V.I.S.A.G.E Online. Use /help for commands.")

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text("Commands:\n/start_stream\n/stop_stream\n/snapshot\n/status\n/video")

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not getattr(main, 'streaming_active', False):
        await update.message.reply_text("📴 Stream inactive. Use /start_stream.")
        return
    local_ip = main.get_local_ip()
    public_url = ngrok.get_tunnels()[0].public_url
    msg = f"Live Stream:\nLocal: http://{local_ip}:5000\nPublic: {public_url}"
    await update.message.reply_text(msg)

async def start_stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if main.streaming_active:
        await update.message.reply_text("✅ Stream already active.")
    else:
        main.start_streaming()
        await update.message.reply_text("🎬 Stream started.")

async def stop_stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not main.streaming_active:
        await update.message.reply_text("📴 Stream not active.")
    else:
        main.stop_streaming()
        await update.message.reply_text("🛑 Stream stopped.")

async def snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    frame = None
    if hasattr(camera, 'take_snapshot'):
        frame = camera.take_snapshot()
    elif hasattr(main, 'camera_instance') and main.camera_instance:
        frame = main.camera_instance.get_current_frame()
    if frame is None:
        await update.message.reply_text("❌ Snapshot failed.")
        return
    success, buf = cv2.imencode('.jpg', frame)
    if not success:
        await update.message.reply_text("❌ Encode failed.")
        return
    bio = io.BytesIO(buf.tobytes())
    bio.name = f'snapshot_{int(time.time())}.jpg'
    bio.seek(0)
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=bio)

async def status(update: Update, context: CallbackContext):
    lines = ["🤖 Status:"]
    lines.append("Bot: ✅ Online")
    lines.append(f"Stream: {'✅ Active' if main.streaming_active else '📴 Inactive'}")
    local_ip = main.get_local_ip()
    lines.append(f"Web: http://{local_ip}:5000")
    await update.message.reply_text('\n'.join(lines))

def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("snapshot", snapshot))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("start_stream", start_stream))
    app.add_handler(CommandHandler("stop_stream", stop_stream))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    run_bot()
