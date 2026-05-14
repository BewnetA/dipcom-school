#!/usr/bin/env python3
"""
Telegram Resource Sharing Bot
A bot for managing educational resources with admin and user roles
"""

import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Load environment variables
load_dotenv()

# Import handlers
from handlers.admin import (
    admin_panel, 
    add_module_start, 
    add_module_name_receive,
    add_module_file_receive,
    add_module_cancel,
    broadcast_confirmation_callback,
    delete_module_start, 
    delete_module_callback,
    upload_resource_start, 
    handle_upload_callback, 
    receive_file, 
    list_modules,
    manage_users,
    enroll_user_start, 
    handle_enroll_callback,
    remove_enrollment_start,
    handle_remove_callback,
    enroll_user_restart,
    enroll_user_cancel,
    remove_enrollment_cancel,
    list_users,
    broadcast_start, 
    broadcast_message, 
    broadcast_cancel,
    broadcast_confirmation_callback, 
    view_statistics,
    handle_approval_callback,
    send_followup_start,
    handle_followup_confirm,
    set_followup_question_start,
    set_followup_question_receive,
    ADD_MODULE_NAME, 
    ADD_MODULE_FILE, 
    DELETE_MODULE, 
    UPLOAD_RESOURCE_SELECT,
    UPLOAD_FILE, 
    BROADCAST_MESSAGE, 
    ENROLL_USER, 
    REMOVE_ENROLLMENT,
    FOLLOWUP_CONFIRM,
    SET_FOLLOWUP_QUESTION
)

from handlers.user import (
    start, register_name, register_phone, view_modules, my_status,
    handle_callback, handle_followup_response, cancel,
    REGISTER_NAME, REGISTER_PHONE
)

from database import db
from utils.decorators import ADMIN_IDS

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ResourceBot:
    def __init__(self):
        self.token = os.getenv('BOT_TOKEN')
        if not self.token:
            raise ValueError("BOT_TOKEN not found in environment variables")
        
        self.admin_ids = ADMIN_IDS
        self.application = None
    
    async def setup_database(self):
        """Initialize database"""
        await db.init_db()
        logger.info("Database initialized successfully")
    
    def setup_handlers(self):
        """Setup all conversation and command handlers"""
        
        # User registration conversation
        reg_conv = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                REGISTER_PHONE: [
                    MessageHandler(filters.CONTACT, register_phone),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone)
                ],
                REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            name="registration",
            persistent=False
        )
        
        # Admin add module conversation
        add_module_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^➕ Add Module$'), add_module_start)],
            states={
                ADD_MODULE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_module_name_receive)],
                ADD_MODULE_FILE: [
                    MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO, add_module_file_receive),
                ],
            },
            fallbacks=[CommandHandler('cancel', add_module_cancel)],
            name="add_module",
            persistent=False
        )
        
        # Admin delete module conversation
        delete_module_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^🗑 Delete Module$'), delete_module_start)],
            states={
                DELETE_MODULE: [CallbackQueryHandler(delete_module_callback)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            name="delete_module",
            persistent=False,
            per_message=False,
            per_chat=True
        )
        
        # Admin upload resource conversation
        upload_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^📤 Upload$'), upload_resource_start)],
            states={
                UPLOAD_RESOURCE_SELECT: [CallbackQueryHandler(handle_upload_callback)],
                UPLOAD_FILE: [
                    MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO, receive_file),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            name="upload_resource",
            persistent=False,
            per_message=False,
            per_chat=True
        )
        
        # Admin broadcast conversation - UPDATED
        broadcast_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^📢 Broadcast$'), broadcast_start)],
            states={
                BROADCAST_MESSAGE: [
                    MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL, broadcast_message),
                    CommandHandler('cancel_broadcast', broadcast_cancel),
                    CallbackQueryHandler(broadcast_confirmation_callback, pattern='^(confirm_broadcast|cancel_broadcast)$'),
                ],
            },
            fallbacks=[CommandHandler('cancel', broadcast_cancel)],
            name="broadcast",
            persistent=False,
            per_message=False,
            per_chat=True
        )
        
        # Admin enroll user conversation
        enroll_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^✅ Enroll User$'), enroll_user_start)],
            states={
                ENROLL_USER: [
                    CallbackQueryHandler(handle_enroll_callback),
                    MessageHandler(filters.Regex('^✅ Enroll User$'), enroll_user_restart),
                    MessageHandler(filters.Regex('^🔙 Back to Admin Panel$'), admin_panel),
                    MessageHandler(filters.Regex('^🔙 Back to User Management$'), manage_users),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, enroll_user_cancel),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            name="enroll_user",
            persistent=False,
            per_message=False,
            per_chat=True
        )
        
        # Admin remove enrollment conversation
        remove_enroll_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^❌ Remove Enrollment$'), remove_enrollment_start)],
            states={
                REMOVE_ENROLLMENT: [
                    CallbackQueryHandler(handle_remove_callback),
                    MessageHandler(filters.Regex('^❌ Remove Enrollment$'), remove_enrollment_start),
                    MessageHandler(filters.Regex('^🔙 Back to Admin Panel$'), admin_panel),
                    MessageHandler(filters.Regex('^🔙 Back to User Management$'), manage_users),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, remove_enrollment_cancel),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            name="remove_enrollment",
            persistent=False,
            per_message=False,
            per_chat=True
        )

        # Admin follow-up broadcast conversation
        followup_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^📣 Follow-Up$'), send_followup_start)],
            states={
                FOLLOWUP_CONFIRM: [CallbackQueryHandler(handle_followup_confirm, pattern='^(confirm_followup_send|cancel_followup_send)$')],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            name="followup",
            persistent=False,
            per_message=False,
            per_chat=True
        )

        # Admin follow-up question edit conversation
        set_followup_question_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^✏️ Set Question$'), set_followup_question_start)],
            states={
                SET_FOLLOWUP_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_followup_question_receive)],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
            name="set_followup_question",
            persistent=False
        )
        
        # Add all handlers
        self.application.add_handler(reg_conv)
        self.application.add_handler(add_module_conv)
        self.application.add_handler(delete_module_conv)
        self.application.add_handler(upload_conv)
        self.application.add_handler(broadcast_conv)
        self.application.add_handler(enroll_conv)
        self.application.add_handler(remove_enroll_conv)
        self.application.add_handler(followup_conv)
        self.application.add_handler(set_followup_question_conv)

        # Command handlers
        self.application.add_handler(CommandHandler('admin', admin_panel))
        self.application.add_handler(CommandHandler('status', my_status))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.Regex('^📚 View Modules$'), view_modules))
        self.application.add_handler(MessageHandler(filters.Regex('^ℹ️ My Status$'), my_status))
        self.application.add_handler(MessageHandler(filters.Regex('^📊 Admin Panel$'), admin_panel))
        self.application.add_handler(MessageHandler(filters.Regex('^👥 Users$'), manage_users))
        self.application.add_handler(MessageHandler(filters.Regex('^📋 Modules$'), list_modules))
        self.application.add_handler(MessageHandler(filters.Regex('^👥 View Users$'), manage_users))
        self.application.add_handler(MessageHandler(filters.Regex('^📋 Pending Users$'), list_users))
        self.application.add_handler(MessageHandler(filters.Regex('^📋 Enrolled Users$'), list_users))
        self.application.add_handler(MessageHandler(filters.Regex('^📊 Statistics$'), view_statistics))
        self.application.add_handler(MessageHandler(filters.Regex('^🔙 Back to Admin Panel$'), admin_panel))
        self.application.add_handler(MessageHandler(filters.Regex('^🔙 Back to Main Menu$'), admin_panel))
        self.application.add_handler(CallbackQueryHandler(handle_approval_callback, pattern='^(approve_user_|view_user_)'))
        self.application.add_handler(CallbackQueryHandler(broadcast_confirmation_callback, pattern='^(confirm_broadcast|cancel_broadcast)$'))
        self.application.add_handler(CallbackQueryHandler(handle_followup_response, pattern='^employment_followup_'))
        # Callback query handler
        self.application.add_handler(CallbackQueryHandler(handle_callback))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
        # Message handlers - add this if not already there
        self.application.add_handler(MessageHandler(filters.Regex('^🔙 Back to Admin Panel$'), admin_panel))
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again later."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    async def post_init(self, application: Application):
        """Setup bot data after initialization"""
        application.bot_data['admin_ids'] = self.admin_ids
        await self.setup_database()
        logger.info(f"Bot started with admins: {self.admin_ids}")
        
        # Test bot connection
        bot_info = await application.bot.get_me()
        logger.info(f"Bot connected: @{bot_info.username}")
    
    async def shutdown(self):
        """Cleanup on shutdown"""
        await db.close_db()
        logger.info("Database connection closed")
    
    def run(self):
        """Run the bot"""
        # Create application
        self.application = Application.builder().token(self.token).post_init(self.post_init).build()
        
        # Setup handlers
        self.setup_handlers()
        
        # Setup shutdown handler
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Run bot
        logger.info("Starting bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """Main function"""
    try:
        bot = ResourceBot()
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()