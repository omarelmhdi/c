from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor
from utils.cleanup import get_temp_file_path
from handlers.start import get_user_session

logger = logging.getLogger(__name__)

async def reorder_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle reorder pages callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[1]
    
    if action == "start":
        await start_reorder_process(update, context)
    elif action == "execute":
        await execute_reorder(update, context)

async def start_reorder_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the reorder pages process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_operation = "reorder"
    session.current_step = "waiting_order_input"
    
    # Get PDF info
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        instruction_text = get_text(user_id, "messages.reorder_instruction")
        instruction_text += f"\n\n📄 **Total pages:** {total_pages}"
        instruction_text += f"\n📋 **Current order:** {', '.join(map(str, range(1, total_pages + 1)))}"
        instruction_text += f"\n💡 **Example:** 3,1,2,4 (moves page 3 to first position)"
        
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
        logger.error(f"Error getting PDF info for reorder: {e}")
        error_text = get_text(user_id, "errors.processing_failed")
        await update.callback_query.edit_message_text(error_text)

async def handle_reorder_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user input for reorder pages operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if (session.current_operation != "reorder" or 
        session.current_step != 'waiting_order_input'):
        return False
    
    user_input = update.message.text.strip()
    
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        # Parse new order
        try:
            new_order = [int(x.strip()) for x in user_input.split(',')]
        except ValueError:
            error_text = "❌ Invalid format. Please enter page numbers separated by commas (e.g., 3,1,2,4)."
            await update.message.reply_text(error_text)
            return True
        
        # Validate new order
        if len(new_order) != total_pages:
            error_text = f"❌ You must specify exactly {total_pages} page numbers."
            await update.message.reply_text(error_text)
            return True
        
        if set(new_order) != set(range(1, total_pages + 1)):
            error_text = f"❌ Invalid page numbers. Use each page number from 1 to {total_pages} exactly once."
            await update.message.reply_text(error_text)
            return True
        
        session.temp_data['new_order'] = new_order
        
        # Show confirmation
        confirmation_text = f"📋 **New page order:** {', '.join(map(str, new_order))}\n"
        confirmation_text += f"📄 **Original order:** {', '.join(map(str, range(1, total_pages + 1)))}\n\n"
        confirmation_text += "Proceed with reordering?"
        
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buttons.confirm"), callback_data="reorder_execute")],
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
        logger.error(f"Error handling reorder input: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.message.reply_text(error_text)
        return True

async def execute_reorder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the reorder pages operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    new_order = session.temp_data.get('new_order', [])
    
    if not new_order:
        error_text = get_text(user_id, "messages.no_pages_selected")
        await update.callback_query.edit_message_text(error_text)
        return
    
    # Show processing message
    processing_text = get_text(user_id, "messages.processing")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        output_path = get_temp_file_path(user_id, "pages_reordered.pdf")
        
        # Reorder pages
        success = processor.reorder_pages(input_path, new_order, output_path)
        
        if success and os.path.exists(output_path):
            # Send processed file
            with open(output_path, 'rb') as processed_file:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=processed_file,
                    filename="pages_reordered.pdf",
                    caption=get_text(user_id, "messages.reorder_completed")
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
        logger.error(f"Error reordering pages: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)