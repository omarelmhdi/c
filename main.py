from fastapi import FastAPI, Request, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import asyncio
import logging
import os
from config.settings import BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH, PORT, DEBUG
from handlers.start import start_command, help_command, cancel_command, callback_handler, handle_pdf_upload
from handlers.merge import merge_callback, handle_merge_files
from handlers.split import split_callback, handle_split_input
from handlers.delete_pages import delete_callback, handle_delete_input
from handlers.rotate import rotate_callback, handle_rotate_input, handle_rotate_all
from handlers.reorder import reorder_callback, handle_reorder_input
from handlers.compress import compress_callback
from handlers.extract_text import extract_text_callback
from handlers.extract_images import extract_images_callback
from handlers.convert import convert_callback, handle_image
from handlers.admin import admin_panel, admin_callback, handle_broadcast_message, execute_broadcast
from handlers.language import language_callback
from utils.i18n import setup_i18n, detect_user_language
from utils.cleanup import cleanup_old_files, schedule_cleanup

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO if not DEBUG else logging.DEBUG
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Telegram PDF Bot",
    description="Professional PDF editing bot for Telegram",
    version="1.0.0"
)

# Initialize Telegram bot application
bot_app = None

async def setup_bot():
    """Setup the Telegram bot application"""
    global bot_app
    
    # Create application
    bot_app = Application.builder().token(BOT_TOKEN).build()
    
    # Setup i18n
    setup_i18n()
    
    # Add handlers
    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("cancel", cancel_command))
    bot_app.add_handler(CommandHandler("admin", admin_panel))
    
    # Callback query handlers
    bot_app.add_handler(CallbackQueryHandler(callback_handler, pattern="^menu_"))
    bot_app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    bot_app.add_handler(CallbackQueryHandler(merge_callback, pattern="^merge_"))
    bot_app.add_handler(CallbackQueryHandler(split_callback, pattern="^split_"))
    bot_app.add_handler(CallbackQueryHandler(delete_callback, pattern="^delete_"))
    bot_app.add_handler(CallbackQueryHandler(rotate_callback, pattern="^rotate_"))
    bot_app.add_handler(CallbackQueryHandler(handle_rotate_all, pattern="^rotate_all$"))
    bot_app.add_handler(CallbackQueryHandler(reorder_callback, pattern="^reorder_"))
    bot_app.add_handler(CallbackQueryHandler(compress_callback, pattern="^compress_"))
    bot_app.add_handler(CallbackQueryHandler(extract_text_callback, pattern="^extract_text_"))
    bot_app.add_handler(CallbackQueryHandler(extract_images_callback, pattern="^extract_images_"))
    bot_app.add_handler(CallbackQueryHandler(convert_callback, pattern="^convert_"))
    bot_app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))
    bot_app.add_handler(CallbackQueryHandler(execute_broadcast, pattern="^admin_send_broadcast$"))
    
    # Message handlers
    bot_app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf_upload))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    
    # Initialize bot
    await bot_app.initialize()
    await bot_app.start()
    
    # Set webhook
    if WEBHOOK_URL:
        webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}"
        await bot_app.bot.set_webhook(webhook_url)
        logger.info(f"Webhook set to: {webhook_url}")
    
    logger.info("Bot setup completed")

async def handle_text_messages(update: Update, context):
    """Handle text messages for various operations"""
    # Try different handlers in order
    handlers = [
        handle_merge_files,
        handle_split_input,
        handle_delete_input,
        handle_rotate_input,
        handle_reorder_input,
        handle_broadcast_message
    ]
    
    for handler in handlers:
        try:
            if await handler(update, context):
                return  # Handler processed the message
        except Exception as e:
            logger.error(f"Error in text handler {handler.__name__}: {e}")
            continue
    
    # If no handler processed the message, detect language and show help
    user_id = update.effective_user.id
    if update.message and update.message.text:
        detect_user_language(user_id, update.message.text)
    
    # Show help message
    from handlers.start import show_main_menu
    await show_main_menu(update, context)

@app.on_event("startup")
async def startup_event():
    """Initialize bot on startup"""
    await setup_bot()
    # Start cleanup task
    asyncio.create_task(schedule_cleanup())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if bot_app:
        await bot_app.stop()
        await bot_app.shutdown()

@app.post(WEBHOOK_PATH)
async def webhook(request: Request):
    """Handle incoming webhook updates"""
    try:
        # Get request body
        body = await request.body()
        
        # Parse update
        update = Update.de_json(body.decode('utf-8'), bot_app.bot)
        
        if update:
            # Process update
            await bot_app.process_update(update)
            return {"status": "ok"}
        else:
            logger.warning("Received invalid update")
            raise HTTPException(status_code=400, detail="Invalid update")
            
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Telegram PDF Bot is running!",
        "status": "active",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "bot_status": "running" if bot_app else "stopped"
    }

@app.get("/stats")
async def get_stats():
    """Get bot statistics"""
    try:
        from handlers.admin import admin_data
        return {
            "total_users": len(admin_data['user_stats']),
            "total_operations": admin_data['bot_stats']['total_operations'],
            "total_files_processed": admin_data['bot_stats']['total_files_processed']
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {"error": "Unable to fetch stats"}

if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=PORT,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug"
    )