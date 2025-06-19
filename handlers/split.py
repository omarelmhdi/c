from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor, parse_page_numbers, validate_page_input
from utils.cleanup import get_temp_file_path, create_temp_file_context
from handlers.start import get_user_session

logger = logging.getLogger(__name__)

async def split_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle split PDF callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[1]
    
    if action == "start":
        await start_split_process(update, context)
    elif action == "pages":
        await split_by_pages_mode(update, context)
    elif action == "range":
        await split_by_range_mode(update, context)
    elif action == "execute":
        await execute_split(update, context)

async def start_split_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the PDF split process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_operation = "split"
    session.current_step = "select_mode"
    
    instruction_text = get_text(user_id, "messages.split_instruction")
    
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buttons.split_by_pages"), callback_data="split_pages")],
        [InlineKeyboardButton(get_text(user_id, "buttons.split_by_range"), callback_data="split_range")],
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")],
        [InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=instruction_text,
        reply_markup=reply_markup
    )

async def split_by_pages_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set split mode to specific pages"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.temp_data['split_mode'] = 'pages'
    session.current_step = 'waiting_pages_input'
    
    # Get PDF info
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        instruction_text = get_text(user_id, "messages.split_by_pages_instruction")
        instruction_text += f"\n\n📄 **Total pages:** {total_pages}"
        
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
        logger.error(f"Error getting PDF info for split: {e}")
        error_text = get_text(user_id, "errors.processing_failed")
        await update.callback_query.edit_message_text(error_text)

async def split_by_range_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set split mode to page ranges"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.temp_data['split_mode'] = 'range'
    session.current_step = 'waiting_range_input'
    
    # Get PDF info
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        instruction_text = get_text(user_id, "messages.split_by_range_instruction")
        instruction_text += f"\n\n📄 **Total pages:** {total_pages}"
        
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
        logger.error(f"Error getting PDF info for split: {e}")
        error_text = get_text(user_id, "errors.processing_failed")
        await update.callback_query.edit_message_text(error_text)

async def handle_split_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user input for split operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if (session.current_operation != "split" or 
        session.current_step not in ['waiting_pages_input', 'waiting_range_input']):
        return False
    
    user_input = update.message.text.strip()
    
    try:
        processor = PDFProcessor()
        pdf_info = processor.get_pdf_info(session.current_files[0]['path'])
        total_pages = pdf_info['pages']
        
        if session.current_step == 'waiting_pages_input':
            # Validate page input
            is_valid, error_msg = validate_page_input(user_input, total_pages)
            
            if not is_valid:
                await update.message.reply_text(error_msg)
                return True
            
            # Parse pages
            pages = parse_page_numbers(user_input, total_pages)
            session.temp_data['pages_to_split'] = pages
            
            # Show confirmation
            confirmation_text = f"📄 **Pages to extract:** {', '.join(map(str, pages))}\n\nProceed with split?"
            
            keyboard = [
                [InlineKeyboardButton(get_text(user_id, "buttons.confirm"), callback_data="split_execute")],
                [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text=confirmation_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        elif session.current_step == 'waiting_range_input':
            # Validate range input
            try:
                pages_per_file = int(user_input)
                if pages_per_file <= 0 or pages_per_file > total_pages:
                    raise ValueError()
            except ValueError:
                error_text = f"❌ Invalid input. Please enter a number between 1 and {total_pages}."
                await update.message.reply_text(error_text)
                return True
            
            session.temp_data['pages_per_file'] = pages_per_file
            
            # Calculate number of files
            num_files = (total_pages + pages_per_file - 1) // pages_per_file
            
            # Show confirmation
            confirmation_text = f"📄 **Split into:** {num_files} files with {pages_per_file} pages each\n\nProceed with split?"
            
            keyboard = [
                [InlineKeyboardButton(get_text(user_id, "buttons.confirm"), callback_data="split_execute")],
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
        logger.error(f"Error handling split input: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.message.reply_text(error_text)
        return True

async def execute_split(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the PDF split operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    # Show processing message
    processing_text = get_text(user_id, "messages.processing")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        split_mode = session.temp_data.get('split_mode')
        
        # Create temporary directory for output files
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            output_files = []
            
            if split_mode == 'pages':
                pages = session.temp_data.get('pages_to_split', [])
                output_files = processor.split_pdf_by_pages(input_path, pages, temp_dir)
            
            elif split_mode == 'range':
                pages_per_file = session.temp_data.get('pages_per_file', 1)
                output_files = processor.split_pdf_by_range(input_path, pages_per_file, temp_dir)
            
            if output_files:
                # Send each split file
                for i, output_file in enumerate(output_files):
                    if os.path.exists(output_file):
                        filename = f"split_part_{i+1}.pdf"
                        
                        with open(output_file, 'rb') as split_file:
                            await context.bot.send_document(
                                chat_id=user_id,
                                document=split_file,
                                filename=filename
                            )
                
                # Send completion message
                completion_text = get_text(user_id, "messages.split_completed")
                await context.bot.send_message(
                    chat_id=user_id,
                    text=completion_text
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
        logger.error(f"Error splitting PDF: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)