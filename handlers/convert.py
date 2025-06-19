from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import os
from utils.i18n import get_text
from utils.pdf_tools import PDFProcessor
from utils.cleanup import get_temp_file_path, is_image_file
from handlers.start import get_user_session
from config.settings import MAX_FILE_SIZE

logger = logging.getLogger(__name__)

async def convert_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle convert callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    action = query.data.split('_')[1]
    
    if action == "start":
        await start_convert_process(update, context)
    elif action == "pdf2images":
        await convert_pdf_to_images(update, context)
    elif action == "images2pdf":
        await start_images_to_pdf(update, context)
    elif action == "create":
        await create_pdf_from_images(update, context)
    elif action == "clear":
        await clear_image_list(update, context)

async def start_convert_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the convert process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.current_operation = "convert"
    session.current_step = "select_type"
    
    instruction_text = get_text(user_id, "messages.convert_instruction")
    
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buttons.pdf_to_images"), callback_data="convert_pdf2images")],
        [InlineKeyboardButton(get_text(user_id, "buttons.images_to_pdf"), callback_data="convert_images2pdf")],
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")],
        [InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=instruction_text,
        reply_markup=reply_markup
    )

async def convert_pdf_to_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Convert PDF to images"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not session.current_files:
        error_text = get_text(user_id, "messages.send_pdf")
        await update.callback_query.edit_message_text(error_text)
        return
    
    session.current_step = "converting_pdf"
    
    # Show processing message
    processing_text = get_text(user_id, "messages.pdf_to_images_instruction")
    await update.callback_query.edit_message_text(processing_text)
    
    try:
        processor = PDFProcessor()
        input_path = session.current_files[0]['path']
        
        # Create temporary directory for images
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert PDF to images
            image_files = processor.pdf_to_images(input_path, temp_dir)
            
            if image_files:
                # Send each image (limit to 10 for direct sending)
                for i, image_path in enumerate(image_files[:10]):
                    if os.path.exists(image_path):
                        try:
                            with open(image_path, 'rb') as image_file:
                                await context.bot.send_photo(
                                    chat_id=user_id,
                                    photo=image_file,
                                    caption=f"Page {i+1} of {len(image_files)}"
                                )
                        except Exception as img_error:
                            logger.error(f"Error sending image {i+1}: {img_error}")
                            continue
                
                # If more than 10 images, create a ZIP file
                if len(image_files) > 10:
                    zip_path = get_temp_file_path(user_id, "pdf_pages_as_images.zip")
                    success = processor.create_zip_archive(image_files, zip_path)
                    
                    if success and os.path.exists(zip_path):
                        with open(zip_path, 'rb') as zip_file:
                            await context.bot.send_document(
                                chat_id=user_id,
                                document=zip_file,
                                filename="pdf_pages_as_images.zip",
                                caption=f"All {len(image_files)} pages as images"
                            )
                
                # Send completion message
                completion_text = get_text(user_id, "messages.convert_completed")
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
        logger.error(f"Error converting PDF to images: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)

async def start_images_to_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start images to PDF conversion"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.current_step = "collecting_images"
    session.temp_data['image_files'] = []
    
    instruction_text = get_text(user_id, "messages.images_to_pdf_instruction")
    
    await show_images_to_pdf_status(update, context, instruction_text)

async def show_images_to_pdf_status(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str = None):
    """Show current images to PDF status"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    image_files = session.temp_data.get('image_files', [])
    
    if not message_text:
        if image_files:
            message_text = f"🖼️ **Images added:** {len(image_files)}\n\nSend more images or create PDF."
        else:
            message_text = get_text(user_id, "messages.images_to_pdf_instruction")
    
    # Add image list to message
    if image_files:
        message_text += "\n\n🖼️ **Images to convert:**\n"
        for i, image_info in enumerate(image_files, 1):
            message_text += f"{i}. {image_info['name']}\n"
    
    keyboard = []
    
    if image_files:
        keyboard.append([InlineKeyboardButton("📄 Create PDF", callback_data="convert_create")])
        keyboard.append([InlineKeyboardButton("🗑️ Clear All", callback_data="convert_clear")])
    
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

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image upload for conversion"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if (session.current_operation == "convert" and 
        session.current_step == "collecting_images"):
        
        # Check file size
        if update.message.photo:
            # Get the largest photo size
            photo = update.message.photo[-1]
            file_size = photo.file_size
            file_id = photo.file_id
            filename = f"image_{len(session.temp_data.get('image_files', []))+1}.jpg"
        else:
            return False
        
        if file_size > MAX_FILE_SIZE:
            error_text = get_text(user_id, "messages.file_too_large")
            await update.message.reply_text(error_text)
            return True
        
        try:
            # Download image
            file = await context.bot.get_file(file_id)
            file_path = get_temp_file_path(user_id, filename)
            await file.download_to_drive(file_path)
            
            # Add to image list
            if 'image_files' not in session.temp_data:
                session.temp_data['image_files'] = []
            
            image_info = {
                'path': file_path,
                'name': filename,
                'size': file_size
            }
            
            session.temp_data['image_files'].append(image_info)
            
            # Show updated status
            await show_images_to_pdf_status(update, context)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling image upload: {e}")
            error_text = get_text(user_id, "errors.general")
            await update.message.reply_text(error_text)
            return True
    
    return False

async def create_pdf_from_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create PDF from collected images"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    image_files = session.temp_data.get('image_files', [])
    
    if not image_files:
        error_text = "❌ No images to convert. Please send images first."
        await update.callback_query.edit_message_text(error_text)
        return
    
    # Show processing message
    processing_text = get_text(user_id, "messages.processing")
    processing_text += f"\n\n🖼️ Converting {len(image_files)} images to PDF..."
    await update.callback_query.edit_message_text(
        text=processing_text,
        parse_mode='Markdown'
    )
    
    try:
        processor = PDFProcessor()
        image_paths = [img['path'] for img in image_files]
        output_path = get_temp_file_path(user_id, "images_to_pdf.pdf")
        
        # Convert images to PDF
        success = processor.images_to_pdf(image_paths, output_path)
        
        if success and os.path.exists(output_path):
            # Send PDF file
            with open(output_path, 'rb') as pdf_file:
                await context.bot.send_document(
                    chat_id=user_id,
                    document=pdf_file,
                    filename="images_to_pdf.pdf",
                    caption=get_text(user_id, "messages.convert_completed")
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
        logger.error(f"Error creating PDF from images: {e}")
        error_text = get_text(user_id, "errors.general")
        await update.callback_query.edit_message_text(error_text)

async def clear_image_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all images from conversion list"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    # Clear image files
    session.temp_data['image_files'] = []
    
    # Show updated status
    instruction_text = get_text(user_id, "messages.images_to_pdf_instruction")
    await show_images_to_pdf_status(update, context, instruction_text)