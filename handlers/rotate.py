from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor, parse_page_numbers, validate_page_input
from utils.cleanup import get_temp_file_path
from handlers.start import get_user_session

logger = logging.getLogger(__name__)

async def rotate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rotate pages callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[1]
    
    if action == "start":
        await start_rotate_process(update, context)
    elif action in ["90", "180", "270"]:
        await set_rotation_angle(update, context, int(action))
    elif action == "execute":
        await execute_rotate(update, context)

async def start_rotate_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the rotate pages process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_operation = "rotate"
    session.current_step = "select_angle"
    
    instruction_text = get_text(user_id, "messages.rotate_instruction")
    
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buttons.rotate_90"), callback_data="rotate_90")],
        [InlineKeyboardButton(get_text(user_id, "buttons.rotate_180"), callback_data="rotate_180")],
        [InlineKeyboardButton(get_text(user_id, "buttons.rotate_270"), callback_data="rotate_270")],
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")],
        [InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=instruction_text,
        reply_markup=reply_markup
    )

async def set_rotation_angle(update: Update, context: ContextTypes.DEFAULT_TYPE, angle: int):
    """Set rotation angle and ask for pages"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.temp_data['rotation_angle'] = angle
    session.current_step = 'waiting_pages_input'
    
    # Get PDF info
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        instruction_text = get_text(user_id, "messages.rotate_pages_instruction")
        instruction_text += f"\n\n🔄 **Rotation angle:** {angle}°"
        instruction_text += f"\n📄 **Total pages:** {total_pages}"
        instruction_text += f"\n💡 **Example:** 1,3,5 or 1-3,7-9 or 'all'"
        
        keyboard = [
            [InlineKeyboardButton("🔄 All Pages", callback_data="rotate_all")],
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
        logger.error(f"Error getting PDF info for rotate: {e}")
        error_text = get_text(user_id, "errors.processing_failed")
        await update.callback_query.edit_message_text(error_text)

async def handle_rotate_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rotate all pages"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if query.data == "rotate_all":
        try:
            processor = PDFProcessor()
            pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
            total_pages = pdf_info['pages']
            
            session.temp_data['pages_to_rotate'] = list(range(1, total_pages + 1))
            
            # Show confirmation
            angle = session.temp_data.get('rotation_angle', 90)
            confirmation_text = f"🔄 **Rotate all {total_pages} pages by {angle}°**\n\nProceed with rotation?"
            
            keyboard = [
                [InlineKeyboardButton(get_text(user_id, "buttons.confirm"), callback_data="rotate_execute")],
                [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=confirmation_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling rotate all: {e}")
            error_text = get_text(user_id, "errors.general")
            await query.edit_message_text(error_text)

async def handle_rotate_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user input for rotate pages operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if (session.current_operation != "rotate" or 
        session.current_step != 'waiting_pages_input'):
        return False
    
    user_input = update.message.text.strip()
    
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        # Handle 'all' keyword
        if user_input.lower() == 'all':
            pages_to_rotate = list(range(1, total_pages + 1))
        else:
            # Validate page input
            is_valid, error_msg = validate_page_input(user_input, total_pages)
            
            if not is_valid:
                await update.message.reply_text(error_msg)
                return True
            
            # Parse pages
            pages_to_rotate = parse_page_numbers(user_input, total_pages)
        
        session.temp_data['pages_to_rotate'] = pages_to_rotate
        
        # Show confirmation
        angle = session.temp_data.get('rotation_angle', 90)
        
        if len(pages_to_rotate) == total_pages:
            confirmation_text = f"🔄 **Rotate all pages by {angle}°**\n\n"
        else:
            confirmation_text = f"🔄 **Pages to rotate:** {', '.join(map(str, pages_to_rotate))}\n"
            confirmation_text += f"🔄 **Rotation angle:** {angle}°\n\n"
        
        confirmation_text += "Proceed with rotation?"
        
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buttons.confirm"), callback_data="rotate_execute")],
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
        logger.error(f"Error handling rotate input: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.message.reply_text(error_text)
        return True

async def execute_rotate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the rotate pages operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    pages_to_rotate = session.temp_data.get('pages_to_rotate', [])
    rotation_angle = session.temp_data.get('rotation_angle', 90)
    
    if not pages_to_rotate:
        error_text = get_text(user_id, "messages.no_pages_selected")
        await update.callback_query.edit_message_text(error_text)
        return
    
    # Show processing message
    processing_text = get_text(user_id, "messages.processing")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        output_path = get_temp_file_path(user_id, "pages_rotated.pdf")
        
        # Rotate pages
        success = processor.rotate_pages(input_path, pages_to_rotate, rotation_angle, output_path)
        
        if success and os.path.exists(output_path):
            # Send processed file
            with open(output_path, 'rb') as processed_file:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=processed_file,
                    filename="pages_rotated.pdf",
                    caption=get_text(user_id, "messages.rotate_completed")
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
        logger.error(f"Error rotating pages: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)