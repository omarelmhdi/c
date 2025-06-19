from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor, parse_page_numbers, validate_page_input
from utils.cleanup import get_temp_file_path
from handlers.start import get_user_session

logger = logging.getLogger(__name__)

async def delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delete pages callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[1]
    
    if action == "start":
        await start_delete_process(update, context)
    elif action == "execute":
        await execute_delete(update, context)

async def start_delete_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the delete pages process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_operation = "delete"
    session.current_step = "waiting_pages_input"
    
    # Get PDF info
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        instruction_text = get_text(user_id, "messages.delete_instruction")
        instruction_text += f"\n\n📄 **Total pages:** {total_pages}"
        instruction_text += f"\n💡 **Example:** 1,3,5 or 1-3,7-9"
        
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")],
            [InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=instruction_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error getting PDF info for delete: {e}")
        error_text = get_text(user_id, "errors.processing_failed")
        await update.callback_query.edit_message_text(error_text)

async def handle_delete_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user input for delete pages operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if (session.current_operation != "delete" or 
        session.current_step != 'waiting_pages_input'):
        return False
    
    user_input = update.message.text.strip()
    
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        # Validate page input
        is_valid, error_msg = validate_page_input(user_input, total_pages)
        
        if not is_valid:
            await update.message.reply_text(error_msg)
            return True
        
        # Parse pages
        pages_to_delete = parse_page_numbers(user_input, total_pages)
        
        if len(pages_to_delete) >= total_pages:
            error_text = "❌ Cannot delete all pages. At least one page must remain."
            await update.message.reply_text(error_text)
            return True
        
        session.temp_data['pages_to_delete'] = pages_to_delete
        
        # Calculate remaining pages
        remaining_pages = total_pages - len(pages_to_delete)
        
        # Show confirmation
        confirmation_text = f"🗑️ **Pages to delete:** {', '.join(map(str, pages_to_delete))}\n"
        confirmation_text += f"📄 **Remaining pages:** {remaining_pages}\n\n"
        confirmation_text += "Proceed with deletion?"
        
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buttons.confirm"), callback_data="delete_execute")],
            [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=confirmation_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling delete input: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.message.reply_text(error_text)
        return True

async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the delete pages operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    pages_to_delete = session.temp_data.get('pages_to_delete', [])
    
    if not pages_to_delete:
        error_text = get_text(user_id, "messages.no_pages_selected")
        await update.callback_query.edit_message_text(error_text)
        return
    
    # Show processing message
    processing_text = get_text(user_id, "messages.processing")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        output_path = get_temp_file_path(user_id, "pages_deleted.pdf")
        
        # Delete pages
        success = processor.delete_pages(input_path, pages_to_delete, output_path)
        
        if success and os.path.exists(output_path):
            # Send processed file
            with open(output_path, 'rb') as processed_file:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=processed_file,
                    filename="pages_deleted.pdf",
                    caption=get_text(user_id, "messages.delete_completed")
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
        logger.error(f"Error deleting pages: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)