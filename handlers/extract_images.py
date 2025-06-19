from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor
from utils.cleanup import get_temp_file_path
from handlers.start import get_user_session

logger = logging.getLogger(__name__)

async def extract_images_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle extract images callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[2]  # extract_images_start
    
    if action == "start":
        await start_extract_images_process(update, context)

async def start_extract_images_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the extract images process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_operation = "extract_images"
    session.current_step = "processing"
    
    # Show processing message
    processing_text = get_text(user_id, "messages.extract_images_instruction")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        
        # Create temporary directory for images
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract images
            image_files = processor.extract_images(input_path, temp_dir)
            
            if image_files:
                # Send each image
                for i, image_path in enumerate(image_files[:10]):  # Limit to 10 images
                    if os.path.exists(image_path):
                        try:
                            with open(image_path, 'rb') as image_file:
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=image_file,
                                    caption=f"Image {i+1} of {len(image_files)}"
                                )
                        except Exception as img_error:
                            logger.error(f"Error sending image {i+1}: {img_error}")
                            continue
                
                # If more than 10 images, create a ZIP file
                if len(image_files) > 10:
                    zip_path = get_temp_file_path(user_id, "extracted_images.zip")
                    success = processor.create_zip_archive(image_files, zip_path)
                    
                    if success and os.path.exists(zip_path):
                        with open(zip_path, 'rb') as zip_file:
                            await context.bot.send_document(
                                chat_id=user_id,
                                document=zip_file,
                                filename="extracted_images.zip",
                                caption=f"All {len(image_files)} extracted images"
                            )
                
                # Send completion message
                completion_text = get_text(
                    user_id, 
                    "messages.extract_images_completed",
                    count=len(image_files)
                )
                
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
                # No images found
                error_text = "❌ No images found in the PDF. The PDF might contain only text or vector graphics."
                
                keyboard = [
                    [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.callback_query.edit_message_text(
                    text=error_text,
                    reply_markup=reply_markup
                )
    
    except Exception as e:
        logger.error(f"Error extracting images: {e}")
        error_text = get_text(user_id, "errors.general")
        
        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=error_text,
            reply_markup=reply_markup
        )