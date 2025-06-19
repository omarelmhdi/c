import os
from typing import List

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "7304877490:AAHO8s7p9iiOdneThwuHj-m5ZTHEOXffT4c")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-vercel-app.vercel.app")

# Admin configuration
ADMIN_IDS: List[int] = [
    7089656746,
]

# File handling
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
TEMP_DIR = "/tmp"
CLEANUP_INTERVAL = 3600  # 1 hour in seconds
FILE_RETENTION_TIME = 1800  # 30 minutes in seconds

# PDF processing
MAX_PDF_PAGES = 1000
COMPRESSION_QUALITY = 85
IMAGE_DPI = 200

# Database (for user stats)
USER_DATA_FILE = os.path.join(TEMP_DIR, "user_data.json")
ERROR_LOG_FILE = os.path.join(TEMP_DIR, "error_log.json")

# Supported languages
SUPPORTED_LANGUAGES = ["en", "ar"]
DEFAULT_LANGUAGE = "en"

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 10
MAX_REQUESTS_PER_HOUR = 100

# Feature flags
FEATURES = {
    "merge": True,
    "split": True,
    "delete_pages": True,
    "rotate": True,
    "reorder": True,
    "compress": True,
    "extract_text": True,
    "extract_images": True,
    "convert": True,
    "admin_panel": True,
}

# Error messages
ERROR_MESSAGES = {
    "file_too_large": "File size exceeds the maximum limit of 50MB.",
    "invalid_pdf": "The uploaded file is not a valid PDF.",
    "processing_error": "An error occurred while processing your file.",
    "rate_limit": "You've exceeded the rate limit. Please try again later.",
    "admin_only": "This command is only available to administrators.",
}

# Success messages
SUCCESS_MESSAGES = {
    "file_processed": "Your file has been processed successfully!",
    "operation_completed": "Operation completed successfully!",
    "settings_updated": "Settings have been updated.",
}

# Webhook configuration for Vercel
VERCEL_CONFIG = {
    "runtime": "python3.9",
    "maxDuration": 30,
}