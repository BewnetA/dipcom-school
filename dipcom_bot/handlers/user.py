from telegram import Update, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from keyboards.reply_markups import *
from utils.decorators import error_handler
from utils.helpers import validate_full_name
import logging
import os
from dotenv import load_dotenv
import datetime
import sqlite3
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Conversation states
REGISTER_PHONE = 1
REGISTER_NAME = 2

# Get admin IDs directly from .env file
def get_admin_ids():
    """Parse admin IDs from .env file"""
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip()]
    return admin_ids


def is_admin_user(user_id: int) -> bool:
    """Return True when the given Telegram user ID is configured as an admin"""
    return user_id in get_admin_ids()


def get_backend_db():
    """Get connection to backend SQLite database"""
    # handlers/user.py -> handlers -> dipcom_bot -> dipcom-backend
    backend_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(backend_root, 'db.sqlite3')
    return sqlite3.connect(db_path)

def get_student_by_phone(phone):
    """Get student from backend by phone"""
    try:
        conn = get_backend_db()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students_student WHERE phone = ?", (phone,))
        result = cursor.fetchone()
        conn.close()
        return dict(result) if result else None
    except Exception as e:
        logger.error(f"Error querying student by phone: {e}")
        return None

def update_student_meta(student_id, user_id, username):
    """Update student meta with telegram info"""
    try:
        conn = get_backend_db()
        cursor = conn.cursor()
        # First get current meta
        cursor.execute("SELECT meta FROM students_student WHERE id = ?", (student_id,))
        current_meta = cursor.fetchone()
        if current_meta and current_meta[0]:
            meta = current_meta[0]
            if isinstance(meta, str):
                meta = json.loads(meta)
        else:
            meta = {}
        
        meta['telegram_user_id'] = user_id
        meta['telegram_username'] = username
        
        meta_json = json.dumps(meta)
        cursor.execute("UPDATE students_student SET meta = ? WHERE id = ?", (meta_json, student_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating student meta: {e}")
        return False

def update_backend_student_status_by_phone(phone, status):
    """Update a backend student status using phone number"""
    if not phone:
        return False
    try:
        conn = get_backend_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE students_student SET status = ? WHERE phone = ?",
            (status, phone)
        )
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        return updated > 0
    except Exception as e:
        logger.error(f"Error updating backend student status by phone: {e}")
        return False

def insert_student(name, father_name, phone, user_id, username, status: str = 'pending'):
    """Insert new student to backend"""
    try:
        import uuid
        from datetime import datetime
        student_id = f"s-{uuid.uuid4().hex[:8]}"
        conn = get_backend_db()
        cursor = conn.cursor()
        meta = json.dumps({'telegram_user_id': user_id, 'telegram_username': username})
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute(
            """INSERT INTO students_student 
               (id, name, father_name, phone, telegram_user_id, telegram_username, meta, status, 
                payment_status, tuition_fee, amount_paid, graduated, employment_status, registration_type,
                registration_date, created_at, updated_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (student_id, name, father_name, phone, user_id, username, meta, status,
             'not_paid', 12000, 0, 0, 'no', 'online', today, now, now)
        )
        conn.commit()
        conn.close()
        return student_id
    except Exception as e:
        logger.error(f"Error inserting student: {e}")
        return None

@error_handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    try:
        user_id = update.effective_user.id
        
        # Get admin IDs directly from .env
        admin_ids = get_admin_ids()
        is_admin = user_id in admin_ids
        
        logger.info(f"Admin IDs from .env: {admin_ids}")
        logger.info(f"Current user ID: {user_id}, Is admin: {is_admin}")
        
        # Get user from database
        user = await db.get_user(user_id)
        
        if user:
            # User exists - if admin and not enrolled, fix it immediately
            if is_admin and user.get('status') != 'enrolled':
                logger.info(f"Fixing admin status for user {user_id} - was {user.get('status')}, changing to enrolled")
                await db.update_user_status(user_id, 'enrolled')
                user = await db.get_user(user_id)
            
            is_enrolled = user.get('status') == 'enrolled' if user else False
            
            welcome_msg = f"Welcome back, {user.get('full_name', 'User')}! 👋\n\n"
            
            if is_admin:
                welcome_msg += "👑 You are an ADMIN with full access.\n"
                if is_enrolled:
                    welcome_msg += "✅ Your admin account is active and enrolled.\n\n"
                    welcome_msg += "Use the buttons below to manage the bot:"
                else:
                    welcome_msg += "⚠️ Your admin account is being activated. Please wait or contact support."
            else:
                if is_enrolled:
                    welcome_msg += "✅ You are enrolled and can access all modules."
                else:
                    welcome_msg += "⏳ Your registration is pending approval from an admin."
            
            # Show appropriate keyboard
            if is_admin and is_enrolled:
                await update.message.reply_text(
                    welcome_msg,
                    parse_mode='Markdown',
                    reply_markup=get_admin_panel_keyboard()
                )
            else:
                await update.message.reply_text(
                    welcome_msg,
                    reply_markup=get_main_keyboard(is_admin, is_enrolled)
                )
        else:
            # New user - start registration with phone
            keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
            await update.message.reply_text(
                "📝 *Welcome to Resource Sharing Bot*\n\n"
                "To get started, please share your phone number.\n\n"
                "This is required for registration and verification.\n\n"
                "Tap the button below to share your phone number:",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return REGISTER_PHONE
    except Exception as e:
        logger.error(f"Error in start function: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")
        return
@error_handler
async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle phone number registration"""
    try:
        phone_number = None
        
        if update.message.contact:
            phone_number = update.message.contact.phone_number
        elif update.message.text:
            # Validate phone number format
            import re
            if re.match(r'^\+?[\d\s\-\(\)]{10,}$', update.message.text.strip()):
                phone_number = update.message.text.strip()
            else:
                keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
                await update.message.reply_text(
                    "❌ Invalid phone number format.\n\n"
                    "Please share your phone number using the button or enter a valid number (e.g., +1234567890):",
                    reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
                )
                return REGISTER_PHONE
        else:
            keyboard = [[KeyboardButton("📱 Share Phone Number", request_contact=True)]]
            await update.message.reply_text(
                "❌ Please share your phone number to continue registration.\n\n"
                "Tap the button below:",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            )
            return REGISTER_PHONE
        
        user_id = update.effective_user.id
        username = update.effective_user.username
        is_admin = is_admin_user(user_id)
        
        # Query backend for student by phone
        student = get_student_by_phone(phone_number)
        
        if student:
            # Student exists, update with telegram info
            success = update_student_meta(student['id'], user_id, username)
            if success:
                logger.info(f"Updated student {student['id']} with telegram info for user {user_id}")
            else:
                logger.error(f"Failed to update student {student['id']} for user {user_id}")
            
            # Check student status for bot access
            student_status = student.get('status', 'pending')
            if is_admin:
                bot_status = 'enrolled'
                if student_status not in ['approved', 'enrolled']:
                    update_backend_student_status_by_phone(phone_number, 'approved')
            else:
                bot_status = 'enrolled' if student_status in ['approved', 'enrolled'] else 'pending'
            
            # Register in bot DB
            success = await db.register_user(
                user_id,
                student['name'],  # Use name from backend
                '',  # No father name in backend
                phone_number,
                username,
                status=bot_status
            )
            
            if success:
                if bot_status == 'enrolled':
                    await update.message.reply_text(
                        f"✅ *Registration Successful!*\n\n"
                        f"Welcome back, {student['name']}!\n\n"
                        f"✅ Your account is active and you can access all modules.",
                        parse_mode='Markdown',
                        reply_markup=get_main_keyboard(False, True)
                    )
                else:
                    await update.message.reply_text(
                        f"✅ *Registration Received!*\n\n"
                        f"Welcome, {student['name']}!\n\n"
                        f"⏳ Your account is pending approval. You will be notified once approved.",
                        parse_mode='Markdown',
                        reply_markup=ReplyKeyboardRemove()
                    )
            else:
                await update.message.reply_text("❌ Registration failed. Please try again.")
        else:
            # Student not found, ask for full name
            context.user_data['phone'] = phone_number
            context.user_data['user_id'] = user_id
            context.user_data['username'] = username
            
            await update.message.reply_text(
                "📝 *Phone number verified*\n\n"
                "You are not registered in our system yet.\n\n"
                "Please provide your *Full Name* (e.g., 'John Doe'):",
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardRemove()
            )
            return REGISTER_NAME
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in register_phone: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
        return REGISTER_PHONE

@error_handler
async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle name registration for new students"""
    try:
        full_name = update.message.text.strip()
        
        is_valid, message = validate_full_name(full_name)
        if not is_valid:
            await update.message.reply_text(f"❌ {message}\n\nPlease send your full name again:")
            return REGISTER_NAME
        
        phone = context.user_data.get('phone')
        user_id = context.user_data.get('user_id')
        username = context.user_data.get('username')
        
        # Parse name and father name for backend student record
        parts = full_name.split()
        name = parts[0]
        father_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
        
        # Insert new student to backend
        status = 'approved' if is_admin_user(user_id) else 'pending'
        student_id = insert_student(name, father_name, phone, user_id, username, status=status)
        
        if student_id:
            # Register in bot DB
            bot_status = 'enrolled' if is_admin_user(user_id) else 'pending'
            success = await db.register_user(
                user_id,
                full_name,
                father_name,
                phone,
                username,
                status=bot_status
            )
            
            if success:
                if is_admin_user(user_id):
                    await update.message.reply_text(
                        "✅ *Registration Successful!*\n\n"
                        f"Welcome, {full_name}!\n\n"
                        "👑 Your admin account is active and you can access all admin features.",
                        parse_mode='Markdown',
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    await update.message.reply_text(
                        "✅ *Registration Successful!*\n\n"
                        f"Welcome, {full_name}!\n\n"
                        "⏳ Your account is pending approval from an administrator.\n\n"
                        "You will receive a notification once approved.",
                        parse_mode='Markdown',
                        reply_markup=ReplyKeyboardRemove()
                    )
                
                # Notify admins
                admin_ids = get_admin_ids()
                for admin_id in admin_ids:
                    try:
                        await context.bot.send_message(
                            admin_id,
                            f"🆕 *NEW STUDENT REGISTRATION*\n\n"
                            f"👤 Name: {full_name}\n"
                            f"📞 Phone: {phone}\n"
                            f"🆔 User ID: {user_id}\n"
                            f"📱 Username: @{username or 'N/A'}\n\n"
                            f"⚠️ Status: PENDING APPROVAL",
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify admin {admin_id}: {e}")
            else:
                await update.message.reply_text("❌ Registration failed. Please try again.")
        else:
            await update.message.reply_text("❌ Failed to create student record. Please try again.")
        
        context.user_data.clear()
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in register_name: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")
        return REGISTER_NAME

@error_handler
async def view_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View available modules"""
    try:
        user_id = update.effective_user.id
        user = await db.get_user(user_id)
        
        # Check admin status from .env
        admin_ids = get_admin_ids()
        is_admin = user_id in admin_ids
        
        # Allow access if enrolled OR if admin
        if not user or (user['status'] != 'enrolled' and not is_admin):
            await update.message.reply_text(
                "❌ Access Denied!\n\n"
                "You are not enrolled in this bot.\n\n"
                "If you are an admin, please use /start to refresh your status.",
                reply_markup=get_main_keyboard(is_admin, False)
            )
            return
        
        modules = await db.get_modules()
        if not modules:
            await update.message.reply_text("📚 No modules available yet.")
            return
        
        await update.message.reply_text(
            "📚 *Available Modules*\n\nSelect a module to view resources:",
            reply_markup=get_module_selection_keyboard(modules),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in view_modules: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

@error_handler
async def my_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check user status"""
    try:
        user_id = update.effective_user.id
        user = await db.get_user(user_id)
        
        # Check admin status from .env
        admin_ids = get_admin_ids()
        is_admin = user_id in admin_ids
        
        if user:
            from utils.helpers import format_user_info
            status_text = format_user_info(user)
            if is_admin:
                status_text += "\n\n👑 *You have ADMIN privileges*"
                if user['status'] != 'enrolled':
                    status_text += "\n⚠️ *Status Issue:* Your admin account needs to be enrolled. Please contact support."
            await update.message.reply_text(
                status_text,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ You are not registered. Use /start to register."
            )
    except Exception as e:
        logger.error(f"Error in my_status: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again later.")

@error_handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user = await db.get_user(user_id)
        admin_ids = get_admin_ids()
        is_admin = user_id in admin_ids
        
        if query.data.startswith("module_"):
            # Handle module selection
            if not user or (user['status'] != 'enrolled' and not is_admin):
                await query.edit_message_text("❌ Access denied. You are not enrolled.")
                return
            
            module_id = int(query.data.split("_")[1])
            module = await db.get_module(module_id)
            resources = await db.get_module_resources(module_id)
            
            if not resources:
                await query.edit_message_text(
                    f"📁 *{module['module_name']}*\n\nNo resources available in this module yet.",
                    parse_mode='Markdown',
                    reply_markup=get_back_button()
                )
            else:
                await query.edit_message_text(
                    f"📁 *{module['module_name']}*\n\nSelect a resource to download:",
                    parse_mode='Markdown',
                    reply_markup=get_resource_keyboard(resources)
                )
        
        elif query.data.startswith("download_"):
            # Handle resource download
            if not user or (user['status'] != 'enrolled' and not is_admin):
                await query.edit_message_text("❌ Access denied. You are not enrolled.")
                return
            
            resource_id = int(query.data.split("_")[1])
            
            # FIXED: Use db.get_resource instead of accessing pool directly
            resource = await db.get_resource(resource_id)
            
            if resource:
                try:
                    if resource['file_type'] == 'document':
                        await context.bot.send_document(
                            chat_id=user_id,
                            document=resource['file_id'],
                            caption=f"📄 {resource['file_name']}"
                        )
                    elif resource['file_type'] == 'video':
                        await context.bot.send_video(
                            chat_id=user_id,
                            video=resource['file_id'],
                            caption=f"🎥 {resource['file_name']}"
                        )
                    elif resource['file_type'] == 'photo':
                        await context.bot.send_photo(
                            chat_id=user_id,
                            photo=resource['file_id'],
                            caption=f"🖼️ {resource['file_name']}"
                        )
                    
                    await db.log_action(user_id, "download", f"Downloaded resource {resource_id}")
                    await query.answer("✅ Download started!")
                except Exception as e:
                    logger.error(f"Download error: {e}")
                    await query.answer("❌ Download failed", show_alert=True)
            else:
                await query.answer("❌ Resource not found", show_alert=True)
        
        elif query.data == "back_to_modules":
            modules = await db.get_modules()
            if modules:
                await query.edit_message_text(
                    "📚 *Available Modules*\n\nSelect a module:",
                    parse_mode='Markdown',
                    reply_markup=get_module_selection_keyboard(modules)
                )
            else:
                await query.edit_message_text("No modules available.")
        
        elif query.data == "back_to_main":
            is_admin_user = user_id in admin_ids
            is_enrolled = user['status'] == 'enrolled' if user else False
            await query.message.reply_text(
                "Main Menu:",
                reply_markup=get_main_keyboard(is_admin_user, is_enrolled)
            )
            await query.message.delete()
    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")
        await query.answer("❌ An error occurred", show_alert=True)
@error_handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    await update.message.reply_text(
        "❌ Operation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END