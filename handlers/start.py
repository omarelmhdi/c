from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
from utils.i18n import set_user_language, get_user_language, get_text, get_available_languages, detect_language
from utils.cleanup import cleanup_user_files, get_temp_file_path, is_pdf_file
from config.settings import MAX_FILE_SIZE, FEATURES

logger = logging.getLogger(__name__)

# User session data
user_sessions = {}

class UserSession:
    """Manage user session data"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.current_operation = None
        self.current_files = []
        self.current_step = None
        self.temp_data = {}
    
    def reset(self):
        """Reset session data"""
        self.current_operation = None
        self.current_files = []
        self.current_step = None
        self.temp_data = {}
        cleanup_user_files(self.user_id)

def get_user_session(user_id: int) -> UserSession:
    """Get or create user session"""
    if user_id not in user_sessions:
        user_sessions[user_id] = UserSession(user_id)
    return user_sessions[user_id]

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Reset user session
    session = get_user_session(user_id)
    session.reset()
    
    # Auto-detect language if not set
    current_lang = get_user_language(user_id)
    if not current_lang:
        # Try to detect from user's language_code
        if update.effective_user.language_code:
            if update.effective_user.language_code.startswith('ar'):
                set_user_language(user_id, 'ar')
            else:
                set_user_language(user_id, 'en')
        else:
            set_user_language(user_id, 'en')
    
    # Show language selection
    await show_language_selection(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user_id = update.effective_user.id
    help_text = get_text(user_id, "commands.help")
    
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            text=help_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cancel command"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    session.reset()
    
    cancel_text = get_text(user_id, "commands.cancel")
    
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=cancel_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=cancel_text,
            reply_markup=reply_markup
        )

async def show_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu"""
    start_text = get_text(update.effective_user.id, "commands.start")
    
    languages = get_available_languages()
    keyboard = []
    
    for lang_code, lang_name in languages.items():
        keyboard.append([InlineKeyboardButton(lang_name, callback_data=f"lang_{lang_code}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=start_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=start_text,
            reply_markup=reply_markup
        )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle language selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    lang_code = query.data.split('_')[1]
    
    # Set user language
    set_user_language(user_id, lang_code)
    
    # Show confirmation and main menu
    confirmation_text = get_text(user_id, "messages.language_selected")
    await query.edit_message_text(text=confirmation_text)
    
    # Show main menu after a short delay
    await show_main_menu(update, context)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu with PDF operations"""
    user_id = update.effective_user.id
    menu_text = get_text(user_id, "messages.send_pdf")
    
    keyboard = []
    
    # Add feature buttons if enabled
    if FEATURES.get("merge", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.merge_pdf"), callback_data="menu_merge")])
    
    if FEATURES.get("split", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.split_pdf"), callback_data="menu_split")])
    
    if FEATURES.get("delete_pages", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.delete_pages"), callback_data="menu_delete")])
    
    if FEATURES.get("rotate", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.rotate_pages"), callback_data="menu_rotate")])
    
    if FEATURES.get("reorder", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.reorder_pages"), callback_data="menu_reorder")])
    
    if FEATURES.get("compress", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.compress_pdf"), callback_data="menu_compress")])
    
    if FEATURES.get("extract_text", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.extract_text"), callback_data="menu_extract_text")])
    
    if FEATURES.get("extract_images", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.extract_images"), callback_data="menu_extract_images")])
    
    if FEATURES.get("convert", True):
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.convert_pdf"), callback_data="menu_convert")])
    
    # Add utility buttons
    keyboard.append([
        InlineKeyboardButton("🌐 Language", callback_data="menu_language"),
        InlineKeyboardButton("❓ Help", callback_data="menu_help")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=menu_text,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=menu_text,
            reply_markup=reply_markup
        )

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu callbacks"""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split('_')[1]
    
    if action == "main":
        await show_main_menu(update, context)
    elif action == "language":
        await show_language_selection(update, context)
    elif action == "help":
        await help_command(update, context)
    elif action in ["merge", "split", "delete", "rotate", "reorder", "compress", "extract_text", "extract_images", "convert"]:
        # These will be handled by their respective modules
        pass

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle PDF file upload"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Check file size
    if update.message.document.file_size > MAX_FILE_SIZE:
        error_text = get_text(user_id, "messages.file_too_large")
        await update.message.reply_text(error_text)
        return
    
    # Check if it's a PDF file
    if not is_pdf_file(update.message.document.file_name):
        error_text = get_text(user_id, "messages.invalid_pdf")
        await update.message.reply_text(error_text)
        return
    
    try:
        # Download file
        file = await context.bot.get_file(update.message.document.file_id)
        file_path = get_temp_file_path(user_id, update.message.document.file_name)
        await file.download_to_drive(file_path)
        
        # Add to session
        session.current_files.append({
            'path': file_path,
            'name': update.message.document.file_name,
            'size': update.message.document.file_size
        })
        
        # Show file received message with operations menu
        received_text = get_text(user_id, "messages.file_received")
        
        keyboard = []
        
        # Add operation buttons
        if FEATURES.get("merge", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.merge_pdf"), callback_data="merge_start")])
        
        if FEATURES.get("split", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.split_pdf"), callback_data="split_start")])
        
        if FEATURES.get("delete_pages", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.delete_pages"), callback_data="delete_start")])
        
        if FEATURES.get("rotate", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.rotate_pages"), callback_data="rotate_start")])
        
        if FEATURES.get("reorder", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.reorder_pages"), callback_data="reorder_start")])
        
        if FEATURES.get("compress", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.compress_pdf"), callback_data="compress_start")])
        
        if FEATURES.get("extract_text", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.extract_text"), callback_data="extract_text_start")])
        
        if FEATURES.get("extract_images", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.extract_images"), callback_data="extract_images_start")])
        
        if FEATURES.get("convert", True):
            keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.convert_pdf"), callback_data="convert_start")])
        
        keyboard.append([InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=received_text,
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error handling PDF upload: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.message.reply_text(error_text)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # If user is in the middle of an operation, handle it accordingly
    if session.current_operation and session.current_step:
        # This will be handled by the specific operation handlers
        return
    
    # Auto-detect language and suggest
    detected_lang = detect_language(update.message.text)
    current_lang = get_user_language(user_id)
    
    if detected_lang != current_lang:
        # Suggest language change
        suggestion_text = f"🌐 I detected you might prefer {detected_lang.upper()}. Would you like to switch?"
        
        keyboard = [
            [InlineKeyboardButton(f"Yes, switch to {detected_lang.upper()}", callback_data=f"lang_{detected_lang}")],
            [InlineKeyboardButton("No, keep current", callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=suggestion_text,
            reply_markup=reply_markup
        )
    else:
        # Show main menu
        await show_main_menu(update, context)