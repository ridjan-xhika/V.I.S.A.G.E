import os
import io
import sys
import time
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, ContextTypes
from telegram.constants import ChatAction
import cv2
from pyngrok import ngrok

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules
try:
    import main
except ImportError:
    print("⚠️  Warning: Streaming functionality not available")
    main = None

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
    """Initialize V.I.S.A.G.E with facial detection capabilities"""
    welcome_msg = (
        "🤖 Welcome to V.I.S.A.G.E!\n"
        "Visual Intelligence Surveillance and General Engagement\n"
        "👤 Now with Facial Detection!\n\n"
        "🎯 System initialized and ready for commands.\n"
        "Use /help to see all available commands."
    )
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Show enhanced help message with facial detection features"""
    help_text = (
        "🎮 Available Commands:\n\n"
        "📷 Camera Functions:\n"
        "/snapshot – Capture snapshot with face detection\n"
        "/snapshot_raw – Capture snapshot without face detection\n"
        "/video – Record video clip with face detection\n"
        "/video_raw – Record video clip without face detection\n\n"
        "👤 Face Detection:\n"
        "/toggle_faces – Enable/disable face detection\n"
        "/face_stats – Show face detection statistics\n\n"
        "🎥 Live Streaming:\n"
        "/start_stream – Start live video streaming\n"
        "/stop_stream – Stop live video streaming\n"
        "/live – Get live stream URL and access info\n\n"
        "⚙️ System Functions:\n"
        "/status – Show system status and performance\n"
        "/performance – Show detailed performance metrics\n"
        "/toggle_processing – Enable/disable frame processing\n"
        "/purge <n> – Delete last n messages (default: 50)\n"
        "/help – Show this help message\n\n"
        "💡 Tips:\n"
        "• Face detection works in real-time on live stream\n"
        "• Use /performance to monitor FPS and system load\n"
        "• Toggle processing off for maximum performance"
    )
    await update.message.reply_text(help_text)

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide live stream URL with face detection info"""
    if main is None:
        await update.message.reply_text("❌ Streaming functionality not available.")
        return
        
    if not getattr(main, 'streaming_active', False):
        await update.message.reply_text(
            "📴 Live stream is not active.\n"
            "Use /start_stream to begin streaming with face detection."
        )
        return
    
    local_ip = main.get_local_ip()
    stream_url = f"http://{local_ip}:5000"
    
    try:
        public_url = ngrok.get_tunnels()[0].public_url if ngrok.get_tunnels() else stream_url
    except:
        public_url = stream_url
    
    face_status = "✅ Active" if getattr(main.camera_instance, 'face_detection_enabled', False) else "❌ Disabled"
    
    access_info = (
        f"*🎥 Live Stream Active*\n\n"
        f"👤 *Face Detection:* {face_status}\n"
        f"🌐 *Local URL:* {stream_url}\n"
        f"🌍 *Public URL:* {public_url}\n\n"
        f"[🔗 Click here to watch]({public_url})"
    )
    
    await update.message.reply_text(access_info, parse_mode='Markdown')

async def start_stream(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start live video stream with face detection"""
    if main is None:
        await update.message.reply_text("❌ Streaming functionality not available.")
        return
        
    if getattr(main, 'streaming_active', False):
        await update.message.reply_text("✅ Live stream is already active!\nUse /live to get access info.")
        return
    
    status_msg = await update.message.reply_text("🎬 Initializing live stream with face detection...")
    
    try:
        main.start_streaming()
        
        face_status = "✅ Enabled" if getattr(main.camera_instance, 'face_detection_enabled', False) else "⚠️ Disabled"
        
        await status_msg.edit_text(
            "✅ *Live Stream Started!*\n\n"
            "🎥 Stream is now active and ready\n"
            f"👤 Face Detection: {face_status}\n"
            "📱 Use /live to get access URLs\n"
            "🌐 Web interface running on port 5000\n\n"
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

async def toggle_faces(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle face detection on/off"""
    if main is None or not hasattr(main, 'camera_instance') or main.camera_instance is None:
        await update.message.reply_text("❌ Camera not available.")
        return
    
    if hasattr(main.camera_instance, 'toggle_face_detection'):
        enabled = main.camera_instance.toggle_face_detection()
        status = "✅ Enabled" if enabled else "❌ Disabled" 
        await update.message.reply_text(f"👤 Face Detection: {status}")
    else:
        await update.message.reply_text("❌ Face detection not supported by current camera.")

async def toggle_processing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Toggle frame processing for performance optimization"""
    if main is None or not hasattr(main, 'camera_instance') or main.camera_instance is None:
        await update.message.reply_text("❌ Camera not available.")
        return
    
    if hasattr(main.camera_instance, 'toggle_processing'):
        enabled = main.camera_instance.toggle_processing()
        status = "✅ Enabled" if enabled else "❌ Disabled"
        perf_note = "\n💡 Disabling processing improves performance but removes face detection." if not enabled else ""
        await update.message.reply_text(f"🎨 Frame Processing: {status}{perf_note}")
    else:
        await update.message.reply_text("❌ Processing toggle not supported.")

async def face_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show face detection statistics"""
    if main is None or not hasattr(main, 'camera_instance') or main.camera_instance is None:
        await update.message.reply_text("❌ Camera not available.")
        return
    
    try:
        stats = main.camera_instance.get_stats()
        
        face_status = "✅ Active" if stats.get('face_detection_enabled', False) else "❌ Disabled"
        processing_status = "✅ Active" if stats.get('processing_enabled', False) else "❌ Disabled"
        dnn_status = "✅ Available" if stats.get('use_dnn', False) else "❌ Using Haar Cascades"
        
        stats_text = (
            f"👤 *Face Detection Statistics*\n\n"
            f"🔍 *Detection:* {face_status}\n"
            f"🎨 *Processing:* {processing_status}\n"
            f"🧠 *DNN Model:* {dnn_status}\n"
            f"📊 *Current FPS:* {stats.get('actual_fps', 0):.1f}\n"
            f"🎯 *Target FPS:* {stats.get('target_fps', 0)}\n"
            f"📈 *Frames Processed:* {stats.get('frame_count', 0)}\n"
            f"⚠️ *Errors:* {stats.get('error_count', 0)}"
        )
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting face stats: {str(e)}")

async def performance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed performance metrics"""
    if main is None or not hasattr(main, 'camera_instance') or main.camera_instance is None:
        await update.message.reply_text("❌ Camera not available.")
        return
    
    try:
        stats = main.camera_instance.get_stats()
        
        actual_fps = stats.get('actual_fps', 0)
        target_fps = stats.get('target_fps', 30)
        efficiency = (actual_fps / target_fps * 100) if target_fps > 0 else 0
        
        performance_emoji = "🟢" if efficiency > 80 else "🟡" if efficiency > 60 else "🔴"
        
        perf_text = (
            f"📊 *Performance Metrics*\n\n"
            f"{performance_emoji} *Efficiency:* {efficiency:.1f}%\n"
            f"⚡ *Actual FPS:* {actual_fps:.1f}\n"
            f"🎯 *Target FPS:* {target_fps}\n"
            f"📈 *Total Frames:* {stats.get('frame_count', 0):,}\n"
            f"❌ *Error Count:* {stats.get('error_count', 0)}\n"
            f"📷 *Camera Status:* {'✅ Open' if stats.get('camera_open', False) else '❌ Closed'}\n"
            f"🎨 *Processing:* {'✅ Active' if stats.get('processing_enabled', False) else '❌ Disabled'}\n"
            f"👤 *Face Detection:* {'✅ Active' if stats.get('face_detection_enabled', False) else '❌ Disabled'}\n\n"
            f"💡 *Tips:*\n"
            f"• Green (>80%): Excellent performance\n"
            f"• Yellow (60-80%): Good performance\n"
            f"• Red (<60%): Consider optimizing"
        )
        
        await update.message.reply_text(perf_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting performance metrics: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show comprehensive system status"""
    if main is None:
        await update.message.reply_text("❌ Main system not available.")
        return
    
    # Get streaming status
    streaming_status = "✅ Active" if getattr(main, 'streaming_active', False) else "❌ Inactive"
    
    # Get camera status
    camera_status = "❌ Not Available"
    if hasattr(main, 'camera_instance') and main.camera_instance is not None:
        try:
            stats = main.camera_instance.get_stats()
            camera_status = "✅ Connected" if stats.get('camera_open', False) else "⚠️ Disconnected"
        except:
            camera_status = "⚠️ Error"
    
    # Get face detection status
    face_detection_status = "❌ Disabled"
    if hasattr(main, 'camera_instance') and main.camera_instance is not None:
        try:
            stats = main.camera_instance.get_stats()
            face_detection_status = "✅ Active" if stats.get('face_detection_enabled', False) else "❌ Disabled"
        except:
            face_detection_status = "⚠️ Unknown"
    
    status_text = (
        f"🤖 *V.I.S.A.G.E System Status*\n\n"
        f"🎥 *Live Stream:* {streaming_status}\n"
        f"📷 *Camera:* {camera_status}\n"
        f"👤 *Face Detection:* {face_detection_status}\n"
        f"🌐 *Bot:* ✅ Online\n"
        f"⏰ *Uptime:* {time.strftime('%H:%M:%S', time.gmtime(time.time()))}\n\n"
        f"📱 Use /live for stream access\n"
        f"📊 Use /performance for detailed metrics\n"
        f"❓ Use /help for all commands"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def snapshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture a snapshot with face detection"""
    if main is None or not hasattr(main, 'camera_instance') or main.camera_instance is None:
        await update.message.reply_text("❌ Camera not available.")
        return
    
    await update.message.reply_chat_action(ChatAction.UPLOAD_PHOTO)
    status_msg = await update.message.reply_text("📸 Capturing snapshot with face detection...")
    
    try:
        # Capture frame with face detection
        ret, frame = main.camera_instance.read_processed_frame()
        if not ret or frame is None:
            await status_msg.edit_text("❌ Failed to capture snapshot.")
            return
        
        # Convert to bytes
        _, buffer = cv2.imencode('.jpg', frame)
        photo_bytes = io.BytesIO(buffer.tobytes())
        
        # Send photo
        await update.message.reply_photo(
            photo=photo_bytes,
            caption="📸 Snapshot with face detection overlay"
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error capturing snapshot: {str(e)}")

async def snapshot_raw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Capture a raw snapshot without face detection"""
    if main is None or not hasattr(main, 'camera_instance') or main.camera_instance is None:
        await update.message.reply_text("❌ Camera not available.")
        return
    
    await update.message.reply_chat_action(ChatAction.UPLOAD_PHOTO)
    status_msg = await update.message.reply_text("📸 Capturing raw snapshot...")
    
    try:
        # Capture raw frame
        ret, frame = main.camera_instance.read_raw_frame()
        if not ret or frame is None:
            await status_msg.edit_text("❌ Failed to capture snapshot.")
            return
        
        # Convert to bytes
        _, buffer = cv2.imencode('.jpg', frame)
        photo_bytes = io.BytesIO(buffer.tobytes())
        
        # Send photo
        await update.message.reply_photo(
            photo=photo_bytes,
            caption="📸 Raw snapshot (no processing)"
        )
        await status_msg.delete()
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Error capturing raw snapshot: {str(e)}")

async def record_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record a short video clip with face detection"""
    if main is None or not hasattr(main, 'camera_instance') or main.camera_instance is None:
        await update.message.reply_text("❌ Camera not available.")
        return
    
    # Get duration from command args (default 5 seconds)
    duration = 5
    if context.args and len(context.args) > 0:
        try:
            duration = min(max(int(context.args[0]), 1), 30)  # Limit 1-30 seconds
        except ValueError:
            pass
    
    await update.message.reply_chat_action(ChatAction.RECORD_VIDEO)
    status_msg = await update.message.reply_text(f"🎥 Recording {duration}s video with face detection...")
    
    # This would need to be implemented in the camera module
    await status_msg.edit_text("⚠️ Video recording feature coming soon!")

async def purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete recent messages (admin function)"""
    try:
        # Get number of messages to delete (default 50, max 100)
        count = 50
        if context.args and len(context.args) > 0:
            count = min(max(int(context.args[0]), 1), 100)
        
        await update.message.reply_text(f"🗑️ Message purge feature would delete {count} messages.")
        # Implementation would require chat admin permissions
        
    except ValueError:
        await update.message.reply_text("❌ Please provide a valid number (1-100).")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors gracefully"""
    print(f"Exception while handling an update: {context.error}")
    
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ An error occurred while processing your request.\n"
            "Please try again or use /help for available commands."
        )

def run_bot():
    """Main function to run the Telegram bot"""
    print("🤖 Starting V.I.S.A.G.E Telegram Bot...")
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("live", live))
    application.add_handler(CommandHandler("start_stream", start_stream))
    application.add_handler(CommandHandler("stop_stream", stop_stream))
    application.add_handler(CommandHandler("toggle_faces", toggle_faces))
    application.add_handler(CommandHandler("toggle_processing", toggle_processing))
    application.add_handler(CommandHandler("face_stats", face_stats))
    application.add_handler(CommandHandler("performance", performance))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("snapshot", snapshot))
    application.add_handler(CommandHandler("snapshot_raw", snapshot_raw))
    application.add_handler(CommandHandler("video", record_video))
    application.add_handler(CommandHandler("video_raw", record_video))  # Placeholder
    application.add_handler(CommandHandler("purge", purge))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    print("✅ V.I.S.A.G.E Bot initialized successfully!")
    print("🚀 Bot is now running...")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    run_bot()