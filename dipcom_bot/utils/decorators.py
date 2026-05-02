from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
import os
import logging

logger = logging.getLogger(__name__)

# Load admin IDs from environment
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '').split(',') if id.strip()]

def admin_required(func):
    """Decorator to check if user is admin"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Access denied. This command is only for admins.")
            logger.warning(f"Unauthorized admin access attempt by user {user_id}")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def error_handler(func):
    """Decorator for error handling"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            error_message = "❌ An error occurred. Please try again later."
            if update and update.effective_message:
                await update.effective_message.reply_text(error_message)
            raise
    return wrapper