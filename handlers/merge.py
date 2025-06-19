from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor
from utils.cleanup import get_temp_file_path, is_pdf_file
from handlers.start import get_user_session
from config.settings import MAX_FILE_SIZE

logger = logging.getLogger(__name__)

async def merge_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle merge PDF callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[1]
    
    if action == "start":
        await start_merge_process(update, context)
    elif action == "add":
        await add_file_to_merge(update, context)
    elif action == "execute":
        await execute_merge(update, context)
    elif action == "clear":
        await clear_merge_files(update, context)

async def start_merge_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the PDF merge process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.current_operation = "merge"
    session.current_step = "collecting_files"
    
    # If user already has a file, add it to merge list
    if session.current_files:
        if 'merge_files' not in session.temp_data:
            session.temp_data['merge_files'] = []
        
        # Add current file to merge list if not already there
        current_file = session.current_files[0]
        if current_file not in session.temp_data['merge_files']:
            session.temp_data['merge_files'].append(current_file)
    
    instruction_text = get_text(user_id, "messages.merge_instruction")
    
    # Show current files and options
    await show_merge_status(update, context, instruction_text)

async def show_merge_status(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str = None):
    """Show current merge status and options"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    merge_files = session.temp_data.get('merge_files', [])
    
    if not message_text:
        if merge_files:
            message_text = get_text(user_id, "messages.merge_files_added", count=len(merge_files))
        else:
            message_text = get_text(user_id, "messages.merge_instruction")
    
    # Add file list to message
    if merge_files:
        message_text += "\n\n📄 **Files to merge:**\n"
        for i, file_info in enumerate(merge_files, 1):
            message_text += f"{i}. {file_info['name']}\n"
    
    keyboard = []
    
    if len(merge_files) >= 2:
        keyboard.append([InlineKeyboardButton("🔗 Merge Files", callback_data="merge_execute")])
    
    if merge_files:
        keyboard.append([InlineKeyboardButton("🗑️ Clear All", callback_data="merge_clear")])
    
    keyboard.extend([
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")],
        [InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")]
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def add_file_to_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a file to the merge list"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Check if user uploaded a new file
    if update.message and update.message.document:
        # Validate file
        if update.message.document.file_size > MAX_FILE_SIZE:
            error_text = get_text(user_id, "messages.file_too_large")
            await update.message.reply_text(error_text)
            return
        
        if not is_pdf_file(update.message.document.file_name):
            error_text = get_text(user_id, "messages.invalid_pdf")
            await update.message.reply_text(error_text)
            return
        
        try:
            # Download file
            file = await context.bot.get_file(update.message.document.file_id)
            file_path = get_temp_file_path(user_id, update.message.document.file_name)
            await file.download_to_drive(file_path)
            
            # Add to merge list
            if 'merge_files' not in session.temp_data:
                session.temp_data['merge_files'] = []
            
            file_info = {
                'path': file_path,
                'name': update.message.document.file_name,
                'size': update.message.document.file_size
            }
            
            session.temp_data['merge_files'].append(file_info)
            
            # Show updated status
            await show_merge_status(update, context)
            
        except Exception as e:
            logger.error(f"Error adding file to merge: {e}")
            error_text = get_text(user_id, "errors.general")
            await update.message.reply_text(error_text)

async def execute_merge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the PDF merge operation"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    merge_files = session.temp_data.get('merge_files', [])
    
    if len(merge_files) < 2:
        error_text = get_text(user_id, "messages.no_pages_selected")
        await update.callback_query.edit_message_text(error_text)
        return
    
    # Show processing message
    processing_text = get_text(user_id, "messages.processing")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        # Create PDF processor
        processor = PDFProcessor()
        
        # Prepare file paths
        file_paths = [file_info['path'] for file_info in merge_files]
        output_path = get_temp_file_path(user_id, "merged_document.pdf")
        
        # Merge PDFs
        success = processor.merge_pdfs(file_paths, output_path)
        
        if success and os.path.exists(output_path):
            # Send merged file
            with open(output_path, 'rb') as merged_file:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=merged_file,
                    filename="merged_document.pdf",
                    caption=get_text(user_id, "messages.merge_completed")
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
        logger.error(f"Error merging PDFs: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)

async def clear_merge_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all files from merge list"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Clear merge files
    session.temp_data['merge_files'] = []
    
    # Show updated status
    instruction_text = get_text(user_id, "messages.merge_instruction")
    await show_merge_status(update, context, instruction_text)

# Handle file uploads during merge process
async def handle_merge_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads during merge process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if (session.current_operation == "merge" and 
        session.current_step == "collecting_files"):
        await add_file_to_merge(update, context)
        return True
    
    return False