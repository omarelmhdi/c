import os
import asyncio
import time
import logging
from typing import List
from config.settings import TEMP_DIR, CLEANUP_INTERVAL, FILE_RETENTION_TIME

logger = logging.getLogger(__name__)

class FileCleanupManager:
    """Manages automatic cleanup of temporary files"""
    
    def __init__(self):
        self.running = False
        self.cleanup_task = None
    
    async def start_cleanup_task(self):
        """Start the automatic cleanup task"""
        if not self.running:
            self.running = True
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("File cleanup task started")
    
    async def stop_cleanup_task(self):
        """Stop the automatic cleanup task"""
        self.running = False
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("File cleanup task stopped")
    
    async def _cleanup_loop(self):
        """Main cleanup loop"""
        while self.running:
            try:
                await self.cleanup_old_files()
                await asyncio.sleep(CLEANUP_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def cleanup_old_files(self):
        """Clean up old temporary files"""
        try:
            if not os.path.exists(TEMP_DIR):
                return
            
            current_time = time.time()
            cleaned_files = 0
            
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                
                # Skip directories and system files
                if not os.path.isfile(file_path) or filename.startswith('.'):
                    continue
                
                # Check file age
                file_age = current_time - os.path.getmtime(file_path)
                
                if file_age > FILE_RETENTION_TIME:
                    try:
                        os.remove(file_path)
                        cleaned_files += 1
                        logger.debug(f"Cleaned up old file: {filename}")
                    except OSError as e:
                        logger.warning(f"Failed to remove file {filename}: {e}")
            
            if cleaned_files > 0:
                logger.info(f"Cleaned up {cleaned_files} old temporary files")
        
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
    
    def cleanup_user_files(self, user_id: int):
        """Clean up files for a specific user"""
        try:
            if not os.path.exists(TEMP_DIR):
                return
            
            user_prefix = f"user_{user_id}_"
            cleaned_files = 0
            
            for filename in os.listdir(TEMP_DIR):
                if filename.startswith(user_prefix):
                    file_path = os.path.join(TEMP_DIR, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            cleaned_files += 1
                    except OSError as e:
                        logger.warning(f"Failed to remove user file {filename}: {e}")
            
            if cleaned_files > 0:
                logger.info(f"Cleaned up {cleaned_files} files for user {user_id}")
        
        except Exception as e:
            logger.error(f"Error cleaning up user files: {e}")
    
    def get_temp_file_path(self, user_id: int, filename: str) -> str:
        """Generate a temporary file path for a user"""
        timestamp = int(time.time())
        safe_filename = self._sanitize_filename(filename)
        temp_filename = f"user_{user_id}_{timestamp}_{safe_filename}"
        return os.path.join(TEMP_DIR, temp_filename)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        # Remove path separators and dangerous characters
        dangerous_chars = ['/', '\\', '..', ':', '*', '?', '"', '<', '>', '|']
        safe_name = filename
        
        for char in dangerous_chars:
            safe_name = safe_name.replace(char, '_')
        
        # Limit length
        if len(safe_name) > 100:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:95] + ext
        
        return safe_name
    
    def ensure_temp_dir(self):
        """Ensure temporary directory exists"""
        try:
            os.makedirs(TEMP_DIR, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create temp directory: {e}")
    
    def get_disk_usage(self) -> dict:
        """Get disk usage statistics for temp directory"""
        try:
            if not os.path.exists(TEMP_DIR):
                return {'total_files': 0, 'total_size': 0}
            
            total_files = 0
            total_size = 0
            
            for filename in os.listdir(TEMP_DIR):
                file_path = os.path.join(TEMP_DIR, filename)
                if os.path.isfile(file_path):
                    total_files += 1
                    total_size += os.path.getsize(file_path)
            
            return {
                'total_files': total_files,
                'total_size': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2)
            }
        
        except Exception as e:
            logger.error(f"Error getting disk usage: {e}")
            return {'total_files': 0, 'total_size': 0}

# Global cleanup manager instance
cleanup_manager = FileCleanupManager()

async def cleanup_old_files():
    """Convenience function to start cleanup task"""
    cleanup_manager.ensure_temp_dir()
    await cleanup_manager.start_cleanup_task()

def cleanup_user_files(user_id: int):
    """Convenience function to clean up user files"""
    cleanup_manager.cleanup_user_files(user_id)

def get_temp_file_path(user_id: int, filename: str) -> str:
    """Convenience function to get temp file path"""
    return cleanup_manager.get_temp_file_path(user_id, filename)

def ensure_temp_dir():
    """Convenience function to ensure temp directory exists"""
    cleanup_manager.ensure_temp_dir()

def get_disk_usage() -> dict:
    """Convenience function to get disk usage"""
    return cleanup_manager.get_disk_usage()

class TempFileContext:
    """Context manager for temporary files with automatic cleanup"""
    
    def __init__(self, user_id: int, filename: str):
        self.user_id = user_id
        self.filename = filename
        self.file_path = None
        self.files_to_cleanup = []
    
    def __enter__(self):
        self.file_path = get_temp_file_path(self.user_id, self.filename)
        self.files_to_cleanup.append(self.file_path)
        return self.file_path
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        for file_path in self.files_to_cleanup:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError as e:
                logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    def add_file(self, file_path: str):
        """Add additional file for cleanup"""
        self.files_to_cleanup.append(file_path)

def create_temp_file_context(user_id: int, filename: str) -> TempFileContext:
    """Create a temporary file context manager"""
    return TempFileContext(user_id, filename)

# File size utilities
def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def check_file_size(file_path: str, max_size: int) -> bool:
    """Check if file size is within limits"""
    try:
        return os.path.getsize(file_path) <= max_size
    except OSError:
        return False

def get_file_extension(filename: str) -> str:
    """Get file extension safely"""
    return os.path.splitext(filename)[1].lower()

def is_pdf_file(filename: str) -> bool:
    """Check if file is a PDF based on extension"""
    return get_file_extension(filename) == '.pdf'

def is_image_file(filename: str) -> bool:
    """Check if file is an image based on extension"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    return get_file_extension(filename) in image_extensions