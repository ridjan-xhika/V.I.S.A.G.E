import os
import io
import sys
import time
import asyncio  # Add this import
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes
from telegram.constants import ChatAction
import cv2
from pyngrok import ngrok

# Add parent directory to path to import from main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import streaming functions from main
try:
    import main
except ImportError:
    print("⚠️  Warning: Streaming functionality not available")
    main = None

# Import camera module
try:
    from . import camera
except ImportError:
    try:
        import camera
    except ImportError:
        print("⚠️  Warning: Camera module not found")
        camera = None

load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in the .env file")

async def start(update: Update, context: CallbackContext) -> None:
    """Initialize V.I.S.A.G.E and display available commands"""
    welcome_msg = (
        "🤖 Welcome to V.I.S.A.G.E!\n"
        "Visual Intelligence Surveillance and General Engagement\n\n"
        "🎯 System initialized and ready for commands.\n"
        "Use /help to see all available commands."
    )
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Show help message with all available commands"""
    help_text = (
        "🎮 Available Commands:\n\n"
        "📷 Camera Functions:\n"
        "/snapshot – Capture and send a snapshot\n"
        "/video – Record and send a short video clip\n\n"
        "🎥 Live Streaming:\n"
        "/start_stream – Start live video streaming\n"
        "/stop_stream – Stop live video streaming\n"
        "/live – Get live stream URL and access info\n\n"
        "⚙️ System Functions:\n"
        "/status – Show system status and performance\n"
        "/purge <n> – Delete last n messages (default: 50)\n"
        "/help – Show this help message\n\n"
        "💡 Tips:\n"
        "• Live streaming works on your local network\n"
        "• Use /status to check all system components\n"
        "• Video clips are automatically deleted after sending"
    )
    await update.message.reply_text(help_text)

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide live stream URL and access information"""
    if main is None:
        await update.message.reply_text("❌ Streaming functionality not available.")
        return
        
    if not getattr(main, 'streaming_active', False):
        await update.message.reply_text(
            "📴 Live stream is not active.\n"
            "Use /start_stream to begin streaming first."
        )
        return
    
    local_ip = main.get_local_ip()
    stream_url = f"http://{local_ip}:5000"
    public_url = ngrok.get_tunnels()[0].public_url
    
    access_info = (
        f"*Live stream is now on!*  \n"
        f"Title: *{stream_url}*  \n"
        f"Host: *{stream_url}*  \n"
        f"[Click here to watch]({public_url})"
    )
    
    await update.message.reply_text(access_info, parse_mode='Markdown')

async def start_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start the live video stream"""
    if main is None:
        await update.message.reply_text("❌ Streaming functionality not available.")
        return
        
    if getattr(main, 'streaming_active', False):
        await update.message.reply_text("✅ Live stream is already active!\nUse /live to get access info.")
        return
    
    # Send initial message
    status_msg = await update.message.reply_text("🎬 Initializing live stream...")
    
    try:
        main.start_streaming()
        
        # Update message with success
        await status_msg.edit_text(
            "✅ *Live Stream Started!*\n\n"
            "🎥 Stream is now active and ready\n"
            "📱 Use /live to get access URLs\n"
            "🌐 Web interface is running on port 5000\n\n"
            "⏱️ Stream initialization complete!"
        , parse_mode='Markdown')
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to start stream: {str(e)}")

async def stop_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop the live video stream"""
    if main is None:
        await update.message.reply_text("❌ Streaming functionality not available.")
        return
        
    if not getattr(main, 'streaming_active', False):
        await update.message.reply_text("📴 Live stream is not currently active.")
        return
    
    main.stop_streaming()
    
    await update.message.reply_text(
        "🛑 *Live Stream Stopped*\n\n"
        "📴 Stream has been deactivated\n"
        "💾 Resources have been freed\n"
        "🔄 Use /start_stream to resume streaming"
    , parse_mode='Markdown')

async def purge(update: Update, context: CallbackContext) -> None:
    """Delete the last n messages in the chat"""
    bot = context.bot
    chat_id = update.effective_chat.id
    
    # Get number of messages to delete
    try:
        n = int(context.args[0]) if context.args else 50
        n = min(n, 100)  # Limit to prevent abuse
    except (IndexError, ValueError):
        n = 50
    
    # Send status message
    status_msg = await update.message.reply_text(f"🗑️ Purging {n} messages...")
    
    last_id = update.message.message_id
    deleted = 0
    
    # Delete messages
    for msg_id in range(last_id - 1, max(1, last_id - n - 1), -1):
        try:
            await bot.delete_message(chat_id, msg_id)
            deleted += 1
            time.sleep(0.1)  # Rate limiting
        except Exception:
            continue
    
    # Update status
    try:
        await status_msg.edit_text(f"✅ Successfully purged {deleted} messages.")
        # Auto-delete this message after 5 seconds
        asyncio.create_task(auto_delete_message(bot, chat_id, status_msg.message_id, 5))
    except Exception:
        pass

async def auto_delete_message(bot, chat_id, message_id, delay):
    """Auto-delete a message after specified delay"""
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except:
        pass

async def snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture and send a snapshot from the camera"""
    # Send loading message with chat action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    status_msg = await update.message.reply_text("📸 Capturing snapshot...")
    
    try:
        # Get frame from camera
        frame = None
        if camera and hasattr(camera, 'take_snapshot'):
            frame = camera.take_snapshot()
        elif main and hasattr(main, 'camera_instance') and main.camera_instance:
            if hasattr(main.camera_instance, 'get_current_frame'):
                frame = main.camera_instance.get_current_frame()
        
        # Fallback to direct camera access
        if frame is None:
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            if not ret:
                frame = None
        
        if frame is None:
            await status_msg.edit_text("❌ No snapshot available. Camera may not be accessible.")
            return
        
        # Encode frame as JPEG
        success, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not success:
            await status_msg.edit_text("❌ Failed to encode the snapshot.")
            return
        
        # Send photo
        bio = io.BytesIO(buf.tobytes())
        bio.name = f'snapshot_{int(time.time())}.jpg'
        bio.seek(0)
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=bio,
            caption=f"📷 Snapshot captured at {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        # Delete status message
        try:
            await status_msg.delete()
        except:
            pass
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Error capturing snapshot: {str(e)}")

async def status(update: Update, context: CallbackContext) -> None:
    """Show the current status of the V.I.S.A.G.E system"""
    start_time = time.perf_counter()
    
    # Send initial status message
    status_msg = await update.message.reply_text("🔍 Checking system status...")
    
    # Gather system information
    status_lines = ["🤖 *V.I.S.A.G.E System Status*\n"]
    
    # Bot status
    status_lines.append("✅ *Bot:* Online and responding")
    
    # Camera status
    camera_status = "✅ Active" if camera else "❌ Module not found"
    status_lines.append(f"📷 *Camera:* {camera_status}")
    
    # Streaming status
    if main is not None:
        streaming_status = "✅ Active" if getattr(main, 'streaming_active', False) else "📴 Inactive"
        status_lines.append(f"🎥 *Live Stream:* {streaming_status}")
        status_lines.append("🌐 *Web Server:* ✅ Running (Port 5000)")
        
        if getattr(main, 'streaming_active', False):
            local_ip = main.get_local_ip()
            status_lines.append(f"📡 *Stream URL:* http://{local_ip}:5000")
    else:
        status_lines.append("🎥 *Live Stream:* ❌ Not Available")
    
    # Performance metrics
    response_time = time.perf_counter() - start_time
    status_lines.append(f"\n⚡ *Response Time:* {response_time:.3f}s")
    status_lines.append(f"🖥️ *Server:* {os.name.upper()}")
    status_lines.append(f"🕒 *Uptime:* Since last restart")
    
    # Network info
    if main:
        local_ip = main.get_local_ip()
        status_lines.append(f"🌐 *Local IP:* {local_ip}")
    
    status_text = "\n".join(status_lines)
    
    try:
        await status_msg.edit_text(status_text, parse_mode='Markdown')
    except Exception:
        # Fallback without markdown if parsing fails
        await status_msg.edit_text(status_text.replace('*', ''))

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record and send a short video clip"""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.RECORD_VIDEO)
    status_msg = await update.message.reply_text("🎬 Recording video clip...")
    
    try:
        # Record video clip
        if camera and hasattr(camera, 'record_clip'):
            clip_path = camera.record_clip(duration=5.0, fps=30)
        else:
            # Fallback recording method
            clip_path = record_video_clip(duration=5.0)
        
        if not clip_path or not os.path.exists(clip_path):
            await status_msg.edit_text("❌ Failed to record video clip.")
            return
        
        await status_msg.edit_text("📤 Uploading video...")
        
        # Send video
        with open(clip_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video_file,
                caption=f"🎥 5-second clip recorded at {time.strftime('%Y-%m-%d %H:%M:%S')}",
                supports_streaming=True
            )
        
        # Clean up
        try:
            os.remove(clip_path)
            await status_msg.delete()
        except:
            pass
            
    except Exception as e:
        await status_msg.edit_text(f"❌ Error recording video: {str(e)}")

def record_video_clip(duration=5.0, fps=30):
    """Fallback method to record video clip"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        
        # Set properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, fps)
        
        # Prepare video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        filename = f'clip_{int(time.time())}.mp4'
        
        ret, frame = cap.read()
        if not ret:
            cap.release()
            return None
        
        height, width, _ = frame.shape
        out = cv2.VideoWriter(filename, fourcc, fps, (width, height))
        
        # Record frames
        start_time = time.time()
        frame_count = 0
        target_frames = int(duration * fps)
        
        while frame_count < target_frames:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
                frame_count += 1
            
            # Control frame rate
            elapsed = time.time() - start_time
            expected_time = frame_count / fps
            if elapsed < expected_time:
                time.sleep(expected_time - elapsed)
        
        # Cleanup
        cap.release()
        out.release()
        
        return filename if os.path.exists(filename) else None
        
    except Exception as e:
        print(f"Video recording error: {e}")
        return None

def run_bot():
    """Initialize and run the Telegram bot"""
    global app
    
    print("🤖 Initializing Telegram bot...")
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    command_handlers = [
        ("start", start),
        ("help", help_command),
        ("status", status),
        ("snapshot", snapshot),
        ("video", video),
        ("purge", purge),
        ("live", live),
        ("start_stream", start_stream),
        ("stop_stream", stop_stream),
    ]
    
    for command, handler in command_handlers:
        app.add_handler(CommandHandler(command, handler))
    
    print("✅ Bot handlers registered")
    print("🚀 Starting bot polling...")
    print("💬 Bot is now ready to receive commands!")
    
    # Start polling
    try:
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        print(f"❌ Bot polling error: {e}")
        raise

if __name__ == "__main__":
    run_bot()