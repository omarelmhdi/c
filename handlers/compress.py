from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text, format_file_size
from utils.pdf_tools import PDFProcessor
from utils.cleanup import get_temp_file_path
from handlers.start import get_user_session

logger = logging.getLogger(__name__)

async def compress_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle compress PDF callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[1]
    
    if action == "start":
        await start_compress_process(update, context)
    elif action == "execute":
        await execute_compress(update, context)
    elif action in ["low", "medium", "high"]:
        await set_compression_level(update, context, action)

async def start_compress_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the PDF compress process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_operation = "compress"
    session.current_step = "select_level"
    
    # Get current file size
    current_file = session.current_files[0]
    file_size = format_file_size(current_file['size'])
    
    instruction_text = get_text(user_id, "messages.compress_instruction")
    instruction_text += f"\n\n📄 **Current file size:** {file_size}"
    
    keyboard = [
        [InlineKeyboardButton("🗜️ Low Compression (Fast)", callback_data="compress_low")],
        [InlineKeyboardButton("🗜️ Medium Compression (Balanced)", callback_data="compress_medium")],
        [InlineKeyboardButton("🗜️ High Compression (Best)", callback_data="compress_high")],
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")],
        [InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=instruction_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def set_compression_level(update: Update, context: ContextTypes.DEFAULT_TYPE, level: str):
    """Set compression level and show confirmation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.temp_data['compression_level'] = level
    
    # Get current file size
    current_file = session.current_files[0]
    file_size = format_file_size(current_file['size'])
    
    level_descriptions = {
        'low': 'Low compression (faster processing, moderate size reduction)',
        'medium': 'Medium compression (balanced processing time and size reduction)',
        'high': 'High compression (slower processing, maximum size reduction)'
    }
    
    confirmation_text = f"🗜️ **Compression Settings**\n\n"
    confirmation_text += f"📄 **Current file size:** {file_size}\n"
    confirmation_text += f"🔧 **Compression level:** {level_descriptions[level]}\n\n"
    confirmation_text += "Proceed with compression?"
    
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buttons.confirm"), callback_data="compress_execute")],
        [InlineKeyboardButton("🔙 Change Level", callback_data="compress_start")],
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=confirmation_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def execute_compress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the PDF compression operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    compression_level = session.temp_data.get('compression_level', 'medium')
    
    # Show processing message
    processing_text = get_text(user_id, "messages.processing")
    processing_text += f"\n\n🗜️ Applying {compression_level} compression..."
    await update.callback_query.edit_message_text(
        text=processing_text,
        parse_mode='Markdown'
    )
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        output_path = get_temp_file_path(user_id, "compressed_document.pdf")
        
        # Compress PDF
        success, compression_info = processor.compress_pdf(input_path, output_path)
        
        if success and os.path.exists(output_path):
            # Format file sizes
            original_size = format_file_size(compression_info['original_size'])
            compressed_size = format_file_size(compression_info['compressed_size'])
            reduction = compression_info['reduction']
            
            # Send compressed file
            with open(output_path, 'rb') as compressed_file:
                caption = get_text(
                    user_id, 
                    "messages.compress_completed",
                    original_size=original_size,
                    compressed_size=compressed_size,
                    reduction=reduction
                )
                
                await context.bot.send_document(
                    chat_id=user_id,
                    document=compressed_file,
                    filename="compressed_document.pdf",
                    caption=caption
                )
            
            # Clean up and reset session
            processor.cleanup_temp_files()
            session.reset()
            
            # Show main menu
            from handlers.start import show_main_menu
            await show_main_menu(update, context)
            
        else:
            error_text = get_text(user_id, "errors.processing_failed")
            await update.callback_query.edit_message_text(error_text)
    
    except Exception as e:
        logger.error(f"Error compressing PDF: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)