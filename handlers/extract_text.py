from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor
from utils.cleanup import get_temp_file_path
from handlers.start import get_user_session

logger = logging.getLogger(__name__)

async def extract_text_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle extract text callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[2]  # extract_text_start
    
    if action == "start":
        await start_extract_text_process(update, context)

async def start_extract_text_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the extract text process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_operation = "extract_text"
    session.current_step = "processing"
    
    # Show processing message
    processing_text = get_text(user_id, "messages.extract_text_instruction")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        
        # Extract text
        extracted_text = processor.extract_text(input_path)
        
        if extracted_text.strip():
            # Limit text length for Telegram message
            max_length = 4000  # Telegram message limit is 4096 characters
            
            if len(extracted_text) > max_length:
                # Save full text to file and send truncated version
                text_file_path = get_temp_file_path(user_id, "extracted_text.txt")
                
                with open(text_file_path, 'w', encoding='utf-8') as text_file:
                    text_file.write(extracted_text)
                
                # Send text file
                with open(text_file_path, 'rb') as text_file:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=text_file,
                        filename="extracted_text.txt",
                        caption=get_text(user_id, "messages.extract_text_completed")
                    )
                
                # Also send truncated preview
                preview_text = f"📝 **Text Preview (first {max_length} characters):**\n\n"
                preview_text += extracted_text[:max_length] + "..."
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=preview_text,
                    parse_mode='Markdown'
                )
            
            else:
                # Send text directly
                message_text = f"📝 **Extracted Text:**\n\n{extracted_text}"
                
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode='Markdown'
                )
                
                # Also send as file for easy copying
                text_file_path = get_temp_file_path(user_id, "extracted_text.txt")
                
                with open(text_file_path, 'w', encoding='utf-8') as text_file:
                    text_file.write(extracted_text)
                
                with open(text_file_path, 'rb') as text_file:
                    await context.bot.send_document(
                        chat_id=user_id,
                        document=text_file,
                        filename="extracted_text.txt",
                        caption=get_text(user_id, "messages.extract_text_completed")
                    )
            
            # Clean up and reset session
            processor.cleanup_temp_files()
            session.reset()
            
            # Show main menu
            from handlers.start import show_main_menu
            await show_main_menu(update, context)
        
        else:
            # No text found
            error_text = "❌ No text content found in the PDF. The PDF might contain only images or be scanned."
            
            keyboard = [
                [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                text=error_text,
                reply_markup=reply_markup
            )
    
    except Exception as e:
        logger.error(f"Error extracting text: {e}")
        error_text = get_text(user_id, "errors.general")
        
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=error_text,
            reply_markup=reply_markup
        )