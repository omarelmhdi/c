import os
import io
import os
import zipfile
from typing import List, Tuple, Optional, Union
from PIL import Image
import PyPDF2
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
import tempfile
import logging
from config.settings import MAX_PDF_PAGES, COMPRESSION_QUALITY, IMAGE_DPI, TEMP_DIR

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Main class for PDF processing operations"""
    
    def __init__(self):
        self.temp_files = []
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        for file_path in self.temp_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                logger.error(f"Error cleaning up temp file {file_path}: {e}")
        self.temp_files.clear()
    
    def create_temp_file(self, suffix=".pdf") -> str:
        """Create a temporary file and track it for cleanup"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=TEMP_DIR)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def validate_pdf(self, file_path: str) -> bool:
        """Validate if file is a valid PDF"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return len(reader.pages) > 0
        except Exception as e:
            logger.error(f"PDF validation failed: {e}")
            return False
    
    def get_pdf_info(self, file_path: str) -> dict:
        """Get PDF information"""
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                return {
                    'pages': len(reader.pages),
                    'size': os.path.getsize(file_path),
                    'encrypted': reader.is_encrypted,
                    'metadata': reader.metadata
                }
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
            return {'pages': 0, 'size': 0, 'encrypted': False, 'metadata': None}
    
    def merge_pdfs(self, pdf_files: List[str], output_path: str) -> bool:
        """Merge multiple PDF files"""
        try:
            writer = PyPDF2.PdfWriter()
            
            for pdf_file in pdf_files:
                with open(pdf_file, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        writer.add_page(page)
            
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)
            
            return True
        except Exception as e:
            logger.error(f"Error merging PDFs: {e}")
            return False
    
    def split_pdf_by_pages(self, input_path: str, page_numbers: List[int], output_dir: str) -> List[str]:
        """Split PDF by specific page numbers"""
        try:
            output_files = []
            
            with open(input_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                for i, page_num in enumerate(page_numbers):
                    if 1 <= page_num <= len(reader.pages):
                        writer = PyPDF2.PdfWriter()
                        writer.add_page(reader.pages[page_num - 1])
                        
                        output_path = os.path.join(output_dir, f"page_{page_num}.pdf")
                        with open(output_path, 'wb') as output_file:
                            writer.write(output_file)
                        
                        output_files.append(output_path)
            
            return output_files
        except Exception as e:
            logger.error(f"Error splitting PDF by pages: {e}")
            return []
    
    def split_pdf_by_range(self, input_path: str, pages_per_file: int, output_dir: str) -> List[str]:
        """Split PDF into files with specified number of pages each"""
        try:
            output_files = []
            
            with open(input_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                total_pages = len(reader.pages)
                
                for start_page in range(0, total_pages, pages_per_file):
                    writer = PyPDF2.PdfWriter()
                    end_page = min(start_page + pages_per_file, total_pages)
                    
                    for page_num in range(start_page, end_page):
                        writer.add_page(reader.pages[page_num])
                    
                    output_path = os.path.join(output_dir, f"part_{start_page//pages_per_file + 1}.pdf")
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
                    
                    output_files.append(output_path)
            
            return output_files
        except Exception as e:
            logger.error(f"Error splitting PDF by range: {e}")
            return []
    
    def delete_pages(self, input_path: str, pages_to_delete: List[int], output_path: str) -> bool:
        """Delete specific pages from PDF"""
        try:
            with open(input_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                
                for page_num in range(len(reader.pages)):
                    if (page_num + 1) not in pages_to_delete:
                        writer.add_page(reader.pages[page_num])
                
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
            
            return True
        except Exception as e:
            logger.error(f"Error deleting pages: {e}")
            return False
    
    def rotate_pages(self, input_path: str, pages_to_rotate: List[int], angle: int, output_path: str) -> bool:
        """Rotate specific pages in PDF"""
        try:
            with open(input_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    if (page_num + 1) in pages_to_rotate or 'all' in [str(p).lower() for p in pages_to_rotate]:
                        page.rotate(angle)
                    writer.add_page(page)
                
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
            
            return True
        except Exception as e:
            logger.error(f"Error rotating pages: {e}")
            return False
    
    def reorder_pages(self, input_path: str, new_order: List[int], output_path: str) -> bool:
        """Reorder pages in PDF"""
        try:
            with open(input_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                writer = PyPDF2.PdfWriter()
                
                for page_num in new_order:
                    if 1 <= page_num <= len(reader.pages):
                        writer.add_page(reader.pages[page_num - 1])
                
                with open(output_path, 'wb') as output_file:
                    writer.write(output_file)
            
            return True
        except Exception as e:
            logger.error(f"Error reordering pages: {e}")
            return False
    
    def compress_pdf(self, input_path: str, output_path: str, compression_level: str = 'medium') -> Tuple[bool, dict]:
        """Compress PDF file"""
        try:
            original_size = os.path.getsize(input_path)
            
            if HAS_PYMUPDF:
                # Use PyMuPDF for better compression
                doc = fitz.open(input_path)
                
                # Compression settings based on level
                if compression_level == 'low':
                    deflate_level = 1
                elif compression_level == 'high':
                    deflate_level = 9
                else:  # medium
                    deflate_level = 6
                
                # Save with compression
                doc.save(
                    output_path,
                    garbage=4,  # Remove unused objects
                    deflate=True,
                    deflate_level=deflate_level,
                    clean=True
                )
                doc.close()
            else:
                # Fallback to PyPDF2
                with open(input_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    writer = PyPDF2.PdfWriter()
                    
                    for page in reader.pages:
                        page.compress_content_streams()
                        writer.add_page(page)
                    
                    with open(output_path, 'wb') as output_file:
                        writer.write(output_file)
            
            compressed_size = os.path.getsize(output_path)
            reduction = ((original_size - compressed_size) / original_size) * 100
            
            return True, {
                'original_size': original_size,
                'compressed_size': compressed_size,
                'reduction': round(reduction, 1)
            }
        except Exception as e:
            logger.error(f"Error compressing PDF: {e}")
            return False, {}
    
    def extract_text(self, input_path: str) -> str:
        """Extract text from PDF"""
        try:
            text = ""
            
            if HAS_PYMUPDF:
                # Use PyMuPDF for better text extraction
                doc = fitz.open(input_path)
                for page in doc:
                    text += page.get_text()
                    text += "\n\n"  # Add page separator
                doc.close()
            else:
                # Fallback to PyPDF2
                with open(input_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        text += page.extract_text() + "\n\n"
            
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def extract_images(self, input_path: str, output_dir: str) -> List[str]:
        """Extract images from PDF"""
        image_files = []
        
        try:
            if HAS_PYMUPDF:
                # Use PyMuPDF for better image extraction
                doc = fitz.open(input_path)
                
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    image_list = page.get_images()
                    
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        
                        if pix.n - pix.alpha < 4:  # GRAY or RGB
                            img_data = pix.tobytes("png")
                            img_filename = f"page_{page_num+1}_img_{img_index+1}.png"
                            img_path = os.path.join(output_dir, img_filename)
                            
                            with open(img_path, "wb") as img_file:
                                img_file.write(img_data)
                            
                            image_files.append(img_path)
                            self.temp_files.append(img_path)
                        
                        pix = None
                
                doc.close()
            else:
                # Fallback to PyPDF2 method
                with open(input_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    
                    for page_num, page in enumerate(reader.pages):
                        if '/XObject' in page['/Resources']:
                            xObject = page['/Resources']['/XObject'].get_object()
                            
                            for obj in xObject:
                                if xObject[obj]['/Subtype'] == '/Image':
                                    try:
                                        size = (xObject[obj]['/Width'], xObject[obj]['/Height'])
                                        data = xObject[obj].get_data()
                                        
                                        if xObject[obj]['/ColorSpace'] == '/DeviceRGB':
                                            mode = "RGB"
                                        else:
                                            mode = "P"
                                        
                                        img = Image.frombytes(mode, size, data)
                                        
                                        img_path = os.path.join(output_dir, f"image_page_{page_num+1}_{obj[1:]}.png")
                                        img.save(img_path)
                                        image_files.append(img_path)
                                        self.temp_files.append(img_path)
                                    except Exception as img_error:
                                        logger.error(f"Error extracting image: {img_error}")
                                        continue
            
            return image_files
        except Exception as e:
            logger.error(f"Error extracting images: {e}")
            return []
    
    def pdf_to_images(self, input_path: str, output_dir: str, dpi: int = IMAGE_DPI) -> List[str]:
        """Convert PDF pages to images"""
        image_files = []
        
        try:
            if HAS_PYMUPDF:
                # Use PyMuPDF for PDF to image conversion
                doc = fitz.open(input_path)
                
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    
                    # Create transformation matrix for DPI
                    mat = fitz.Matrix(dpi/72, dpi/72)
                    pix = page.get_pixmap(matrix=mat)
                    
                    img_filename = f"page_{page_num+1}.png"
                    img_path = os.path.join(output_dir, img_filename)
                    
                    pix.save(img_path)
                    image_files.append(img_path)
                    self.temp_files.append(img_path)
                    
                    pix = None
                
                doc.close()
            else:
                # Fallback: create placeholder images
                with open(input_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    
                    for page_num in range(len(reader.pages)):
                        # Create a placeholder image
                        img = Image.new('RGB', (595, 842), color='white')  # A4 size
                        img_path = os.path.join(output_dir, f"page_{page_num+1}.png")
                        img.save(img_path)
                        image_files.append(img_path)
                        self.temp_files.append(img_path)
            
            return image_files
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
    
    def images_to_pdf(self, image_paths: List[str], output_path: str) -> bool:
        """Convert images to PDF"""
        try:
            images = []
            
            for img_path in image_paths:
                img = Image.open(img_path)
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
            
            if images:
                images[0].save(output_path, save_all=True, append_images=images[1:])
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error converting images to PDF: {e}")
            return False
    
    def create_zip_archive(self, files: List[str], output_path: str) -> bool:
        """Create ZIP archive from multiple files"""
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in files:
                    if os.path.exists(file_path):
                        arcname = os.path.basename(file_path)
                        zipf.write(file_path, arcname)
            return True
        except Exception as e:
            logger.error(f"Error creating ZIP archive: {e}")
            return False

def parse_page_numbers(page_input: str, max_pages: int) -> List[int]:
    """Parse page numbers from user input"""
    pages = []
    
    try:
        # Handle 'all' keyword
        if page_input.lower().strip() == 'all':
            return list(range(1, max_pages + 1))
        
        # Split by commas
        parts = page_input.split(',')
        
        for part in parts:
            part = part.strip()
            
            if '-' in part:
                # Handle ranges like "1-5"
                start, end = part.split('-', 1)
                start = int(start.strip())
                end = int(end.strip())
                
                if start <= end and start >= 1 and end <= max_pages:
                    pages.extend(range(start, end + 1))
            else:
                # Handle single page numbers
                page_num = int(part)
                if 1 <= page_num <= max_pages:
                    pages.append(page_num)
        
        # Remove duplicates and sort
        return sorted(list(set(pages)))
    
    except (ValueError, IndexError):
        return []

def validate_page_input(page_input: str, max_pages: int) -> Tuple[bool, str]:
    """Validate page input and return error message if invalid"""
    if not page_input.strip():
        return False, "Page input cannot be empty"
    
    pages = parse_page_numbers(page_input, max_pages)
    
    if not pages:
        return False, f"Invalid page format. Use numbers (1,2,3) or ranges (1-5) between 1 and {max_pages}"
    
    return True, ""

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"