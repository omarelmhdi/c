import json
import os
from typing import Dict, Any, Optional
from config.settings import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE

# Global storage for translations
translations: Dict[str, Dict[str, Any]] = {}
user_languages: Dict[int, str] = {}  # user_id -> language_code

def setup_i18n():
    """Load all translation files"""
    global translations
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    locales_dir = os.path.join(base_dir, "locales")
    
    for lang in SUPPORTED_LANGUAGES:
        locale_file = os.path.join(locales_dir, f"{lang}.json")
        if os.path.exists(locale_file):
            with open(locale_file, 'r', encoding='utf-8') as f:
                translations[lang] = json.load(f)
        else:
            print(f"Warning: Translation file for {lang} not found")

def set_user_language(user_id: int, language: str):
    """Set language preference for a user"""
    if language in SUPPORTED_LANGUAGES:
        user_languages[user_id] = language
    else:
        user_languages[user_id] = DEFAULT_LANGUAGE

def get_user_language(user_id: int) -> str:
    """Get user's language preference"""
    return user_languages.get(user_id, DEFAULT_LANGUAGE)

def detect_language(text: str) -> str:
    """Simple language detection based on Arabic characters"""
    arabic_chars = sum(1 for char in text if '\u0600' <= char <= '\u06FF')
    total_chars = len([char for char in text if char.isalpha()])
    
    if total_chars > 0 and arabic_chars / total_chars > 0.3:
        return 'ar'
    return 'en'

def get_text(user_id: int, key: str, **kwargs) -> str:
    """Get translated text for a user"""
    lang = get_user_language(user_id)
    return get_text_by_lang(lang, key, **kwargs)

def get_text_by_lang(lang: str, key: str, **kwargs) -> str:
    """Get translated text by language code"""
    if lang not in translations:
        lang = DEFAULT_LANGUAGE
    
    # Navigate through nested keys (e.g., "commands.start")
    keys = key.split('.')
    text = translations[lang]
    
    try:
        for k in keys:
            text = text[k]
        
        # Format with provided arguments
        if kwargs:
            return text.format(**kwargs)
        return text
    
    except (KeyError, TypeError):
        # Fallback to English if key not found
        if lang != DEFAULT_LANGUAGE:
            return get_text_by_lang(DEFAULT_LANGUAGE, key, **kwargs)
        return f"Missing translation: {key}"

def get_button_text(user_id: int, button_key: str) -> str:
    """Get button text for a user"""
    return get_text(user_id, f"buttons.{button_key}")

def get_message_text(user_id: int, message_key: str, **kwargs) -> str:
    """Get message text for a user"""
    return get_text(user_id, f"messages.{message_key}", **kwargs)

def get_error_text(user_id: int, error_key: str) -> str:
    """Get error text for a user"""
    return get_text(user_id, f"errors.{error_key}")

def get_command_text(user_id: int, command_key: str) -> str:
    """Get command text for a user"""
    return get_text(user_id, f"commands.{command_key}")

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

def is_rtl_language(lang: str) -> bool:
    """Check if language is right-to-left"""
    rtl_languages = ['ar', 'he', 'fa', 'ur']
    return lang in rtl_languages

def get_language_flag(lang: str) -> str:
    """Get flag emoji for language"""
    flags = {
        'en': '🇺🇸',
        'ar': '🇸🇦',
    }
    return flags.get(lang, '🌐')

def get_available_languages() -> Dict[str, str]:
    """Get available languages with their display names"""
    languages = {}
    for lang in SUPPORTED_LANGUAGES:
        if lang in translations:
            flag = get_language_flag(lang)
            if lang == 'en':
                languages[lang] = f"{flag} English"
            elif lang == 'ar':
                languages[lang] = f"{flag} العربية"
            else:
                languages[lang] = f"{flag} {lang.upper()}"
    return languages

def validate_translation_keys():
    """Validate that all languages have the same keys"""
    if not translations:
        return
    
    base_lang = DEFAULT_LANGUAGE
    if base_lang not in translations:
        return
    
    def get_all_keys(d, prefix=''):
        keys = set()
        for k, v in d.items():
            current_key = f"{prefix}.{k}" if prefix else k
            keys.add(current_key)
            if isinstance(v, dict):
                keys.update(get_all_keys(v, current_key))
        return keys
    
    base_keys = get_all_keys(translations[base_lang])
    
    for lang, trans in translations.items():
        if lang == base_lang:
            continue
        
        lang_keys = get_all_keys(trans)
        missing_keys = base_keys - lang_keys
        extra_keys = lang_keys - base_keys
        
        if missing_keys:
            print(f"Warning: {lang} missing keys: {missing_keys}")
        if extra_keys:
            print(f"Warning: {lang} extra keys: {extra_keys}")

# Auto-validate translations on import
if translations:
    validate_translation_keys()