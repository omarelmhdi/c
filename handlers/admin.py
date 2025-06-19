from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import logging
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
from utils.i18n import get_text
from utils.cleanup import get_disk_usage
from handlers.start import get_user_session, user_sessions
from config.settings import ADMIN_IDS, USER_DATA_FILE, ERROR_LOG_FILE

logger = logging.getLogger(__name__)

# Admin data storage
admin_data = {
    'user_stats': {},
    'error_logs': [],
    'bot_stats': {
        'start_time': datetime.now(),
        'total_operations': 0,
        'total_files_processed': 0
    }
}

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS

def load_admin_data():
    """Load admin data from files"""
    global admin_data
    
    # Load user data
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, 'r') as f:
                admin_data['user_stats'] = json.load(f)
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
    
    # Load error logs
    if os.path.exists(ERROR_LOG_FILE):
        try:
            with open(ERROR_LOG_FILE, 'r') as f:
                admin_data['error_logs'] = json.load(f)
        except Exception as e:
            logger.error(f"Error loading error logs: {e}")

def save_admin_data():
    """Save admin data to files"""
    try:
        # Save user data
        os.makedirs(os.path.dirname(USER_DATA_FILE), exist_ok=True)
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(admin_data['user_stats'], f, indent=2)
        
        # Save error logs (keep only last 100 entries)
        admin_data['error_logs'] = admin_data['error_logs'][-100:]
        os.makedirs(os.path.dirname(ERROR_LOG_FILE), exist_ok=True)
        with open(ERROR_LOG_FILE, 'w') as f:
            json.dump(admin_data['error_logs'], f, indent=2)
    
    except Exception as e:
        logger.error(f"Error saving admin data: {e}")

def log_user_activity(user_id: int, operation: str, success: bool = True):
    """Log user activity"""
    user_id_str = str(user_id)
    
    if user_id_str not in admin_data['user_stats']:
        admin_data['user_stats'][user_id_str] = {
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'operations': {},
            'total_operations': 0,
            'errors': 0
        }
    
    user_stats = admin_data['user_stats'][user_id_str]
    user_stats['last_seen'] = datetime.now().isoformat()
    
    if operation not in user_stats['operations']:
        user_stats['operations'][operation] = {'success': 0, 'error': 0}
    
    if success:
        user_stats['operations'][operation]['success'] += 1
        admin_data['bot_stats']['total_operations'] += 1
        admin_data['bot_stats']['total_files_processed'] += 1
    else:
        user_stats['operations'][operation]['error'] += 1
        user_stats['errors'] += 1
    
    user_stats['total_operations'] += 1
    
    save_admin_data()

def log_error(user_id: int, operation: str, error_message: str):
    """Log error"""
    error_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'operation': operation,
        'error': error_message
    }
    
    admin_data['error_logs'].append(error_entry)
    log_user_activity(user_id, operation, success=False)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        error_text = get_text(user_id, "messages.admin_only")
        await update.message.reply_text(error_text)
        return
    
    welcome_text = get_text(user_id, "messages.admin_welcome")
    
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buttons.user_stats"), callback_data="admin_stats")],
        [InlineKeyboardButton(get_text(user_id, "buttons.broadcast"), callback_data="admin_broadcast")],
        [InlineKeyboardButton(get_text(user_id, "buttons.error_logs"), callback_data="admin_errors")],
        [InlineKeyboardButton("💾 System Info", callback_data="admin_system")],
        [InlineKeyboardButton("🔄 Reload Data", callback_data="admin_reload")],
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=welcome_text,
        reply_markup=reply_markup
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        error_text = get_text(user_id, "messages.admin_only")
        await query.edit_message_text(error_text)
        return
    
    action = query.data.split('_')[1]
    
    if action == "stats":
        await show_stats(update, context)
    elif action == "broadcast":
        await start_broadcast(update, context)
    elif action == "errors":
        await show_error_logs(update, context)
    elif action == "system":
        await show_system_info(update, context)
    elif action == "reload":
        await reload_admin_data(update, context)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user_id = update.effective_user.id
    
    # Calculate statistics
    total_users = len(admin_data['user_stats'])
    total_operations = admin_data['bot_stats']['total_operations']
    total_errors = sum(user['errors'] for user in admin_data['user_stats'].values())
    
    # Calculate uptime
    uptime = datetime.now() - admin_data['bot_stats']['start_time']
    uptime_str = str(uptime).split('.')[0]  # Remove microseconds
    
    # Active users (last 24 hours)
    active_users = 0
    yesterday = datetime.now() - timedelta(days=1)
    
    for user_stats in admin_data['user_stats'].values():
        last_seen = datetime.fromisoformat(user_stats['last_seen'])
        if last_seen > yesterday:
            active_users += 1
    
    # Most popular operations
    operation_counts = {}
    for user_stats in admin_data['user_stats'].values():
        for op, counts in user_stats['operations'].items():
            if op not in operation_counts:
                operation_counts[op] = 0
            operation_counts[op] += counts['success']
    
    popular_ops = sorted(operation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    stats_text = get_text(
        user_id, 
        "messages.stats_message",
        total_users=total_users,
        files_processed=total_operations,
        errors=total_errors,
        uptime=uptime_str
    )
    
    stats_text += f"\n\n📊 **Additional Stats:**\n"
    stats_text += f"👥 Active users (24h): {active_users}\n"
    stats_text += f"💾 Current sessions: {len(user_sessions)}\n"
    
    if popular_ops:
        stats_text += f"\n🔥 **Popular Operations:**\n"
        for op, count in popular_ops:
            stats_text += f"• {op}: {count}\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 Detailed Stats", callback_data="admin_detailed")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")],
        [InlineKeyboardButton(get_text(user_id, "buttons.back_to_menu"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast message process"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    session.current_operation = "admin_broadcast"
    session.current_step = "waiting_message"
    
    instruction_text = get_text(user_id, "messages.broadcast_instruction")
    
    keyboard = [
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")],
        [InlineKeyboardButton(get_text(user_id, "buttons.cancel"), callback_data="menu_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=instruction_text,
        reply_markup=reply_markup
    )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message input"""
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if (session.current_operation != "admin_broadcast" or 
        session.current_step != "waiting_message"):
        return False
    
    if not is_admin(user_id):
        return False
    
    broadcast_message = update.message.text
    
    # Send confirmation
    confirmation_text = f"📢 **Broadcast Preview:**\n\n{broadcast_message}\n\n"
    confirmation_text += f"Send this message to {len(admin_data['user_stats'])} users?"
    
    keyboard = [
        [InlineKeyboardButton("✅ Send Broadcast", callback_data="admin_send_broadcast")],
        [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    session.temp_data['broadcast_message'] = broadcast_message
    
    await update.message.reply_text(
        text=confirmation_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return True

async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute broadcast message"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    session = get_user_session(user_id)
    
    if not is_admin(user_id):
        return
    
    broadcast_message = session.temp_data.get('broadcast_message', '')
    
    if not broadcast_message:
        error_text = "❌ No broadcast message found."
        await query.edit_message_text(error_text)
        return
    
    # Show progress message
    progress_text = "📢 Sending broadcast message..."
    await query.edit_message_text(progress_text)
    
    # Send to all users
    sent_count = 0
    failed_count = 0
    
    for user_id_str in admin_data['user_stats'].keys():
        try:
            target_user_id = int(user_id_str)
            await context.bot.send_message(
                chat_id=target_user_id,
                text=broadcast_message
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id_str}: {e}")
            failed_count += 1
    
    # Send completion message
    completion_text = get_text(
        user_id,
        "messages.broadcast_completed",
        count=sent_count
    )
    
    if failed_count > 0:
        completion_text += f"\n⚠️ Failed to send to {failed_count} users."
    
    keyboard = [
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=completion_text,
        reply_markup=reply_markup
    )
    
    # Reset session
    session.reset()

async def show_error_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recent error logs"""
    user_id = update.effective_user.id
    
    if not admin_data['error_logs']:
        no_errors_text = get_text(user_id, "messages.no_errors")
        
        keyboard = [
            [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text=no_errors_text,
            reply_markup=reply_markup
        )
        return
    
    # Show last 10 errors
    recent_errors = admin_data['error_logs'][-10:]
    
    errors_text = "📋 **Recent Errors:**\n\n"
    
    for i, error in enumerate(reversed(recent_errors), 1):
        timestamp = datetime.fromisoformat(error['timestamp']).strftime('%Y-%m-%d %H:%M')
        errors_text += f"{i}. **{timestamp}**\n"
        errors_text += f"   User: {error['user_id']}\n"
        errors_text += f"   Operation: {error['operation']}\n"
        errors_text += f"   Error: {error['error'][:100]}...\n\n"
    
    keyboard = [
        [InlineKeyboardButton("📄 Export Logs", callback_data="admin_export_logs")],
        [InlineKeyboardButton("🗑️ Clear Logs", callback_data="admin_clear_logs")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=errors_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system information"""
    user_id = update.effective_user.id
    
    # Get disk usage
    disk_info = get_disk_usage()
    
    # Get memory usage (simplified)
    import psutil
    memory = psutil.virtual_memory()
    
    system_text = "💾 **System Information:**\n\n"
    system_text += f"🗂️ **Temp Files:**\n"
    system_text += f"   Count: {disk_info['total_files']}\n"
    system_text += f"   Size: {disk_info.get('total_size_mb', 0):.2f} MB\n\n"
    
    system_text += f"💾 **Memory Usage:**\n"
    system_text += f"   Used: {memory.percent}%\n"
    system_text += f"   Available: {memory.available // (1024*1024)} MB\n\n"
    
    system_text += f"🔧 **Bot Status:**\n"
    system_text += f"   Active Sessions: {len(user_sessions)}\n"
    system_text += f"   Total Users: {len(admin_data['user_stats'])}\n"
    
    keyboard = [
        [InlineKeyboardButton("🧹 Cleanup Temp Files", callback_data="admin_cleanup")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=system_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def reload_admin_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reload admin data from files"""
    user_id = update.effective_user.id
    
    load_admin_data()
    
    success_text = "✅ Admin data reloaded successfully!"
    
    keyboard = [
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        text=success_text,
        reply_markup=reply_markup
    )

# Initialize admin data on import
load_admin_data()