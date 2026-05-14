from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from keyboards.reply_markups import *
from utils.decorators import admin_required, error_handler
import logging

logger = logging.getLogger(__name__)

# Conversation states
ADD_MODULE_NAME = 1
ADD_MODULE_FILE = 2
DELETE_MODULE = 3
UPLOAD_RESOURCE_SELECT = 4
UPLOAD_FILE = 5
BROADCAST_MESSAGE = 6
ENROLL_USER = 7
REMOVE_ENROLLMENT = 8
FOLLOWUP_CONFIRM = 9
SET_FOLLOWUP_QUESTION = 10

@admin_required
@error_handler
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel"""
    await update.message.reply_text(
        "🔧 *Admin Panel*\n\nChoose an option:",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode='Markdown'
    )

@admin_required
@error_handler
async def send_followup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the follow-up survey send flow"""
    survey = await db.ensure_followup_survey()
    graduated_students = await db.get_graduated_students()

    if not graduated_students:
        await update.message.reply_text(
            "⚠️ No graduated students found with Telegram contact information.\n\n"
            "Make sure graduated students have their Telegram ID attached to their student profile before sending the follow-up.",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END

    question = survey.get('question', "Have you found a job after graduation? Please answer Yes or No.")
    count = len(graduated_students)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Send to Graduated Students", callback_data="confirm_followup_send")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_followup_send")]
    ])

    await update.message.reply_text(
        f"📣 *Follow-Up Survey*\n\n"
        f"*Question:* {question}\n\n"
        f"This will be sent to *{count}* graduated student(s) who have a Telegram account attached.\n\n"
        "Do you want to send this follow-up now?",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    return FOLLOWUP_CONFIRM

@admin_required
@error_handler
async def handle_followup_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the follow-up question after admin confirmation"""
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_followup_send':
        await query.edit_message_text(
            "❌ Follow-up send cancelled."
        )
        return ConversationHandler.END

    survey = await db.ensure_followup_survey()
    graduated_students = await db.get_graduated_students()
    question = survey.get('question', "Have you found a job after graduation? Please answer Yes or No.")
    survey_id = survey.get('id', 'job_followup')

    if not graduated_students:
        await query.edit_message_text(
            "⚠️ No graduated students found to send the follow-up."
        )
        return ConversationHandler.END

    yes_button = InlineKeyboardButton("✅ Yes", callback_data=f"employment_followup_yes_{survey_id}")
    no_button = InlineKeyboardButton("❌ No", callback_data=f"employment_followup_no_{survey_id}")
    inline_keyboard = InlineKeyboardMarkup([[yes_button, no_button]])

    sent_count = 0
    failed_count = 0
    for student in graduated_students:
        telegram_id = student.get('telegram_user_id')
        try:
            await context.bot.send_message(
                telegram_id,
                f"📣 *Follow-Up Question*\n\n{question}",
                parse_mode='Markdown',
                reply_markup=inline_keyboard
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send follow-up to student {student['id']}: {e}")
            failed_count += 1

    await db.update_followup_survey_last_sent(survey_id)
    try:
        await query.edit_message_text(
            f"✅ Follow-up completed. Sent to *{sent_count}* graduated student(s) and failed for *{failed_count}* student(s).",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to edit followup completion message: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"✅ Follow-up completed. Sent to *{sent_count}* graduated student(s) and failed for *{failed_count}* student(s).",
            parse_mode='Markdown',
            reply_markup=get_admin_panel_keyboard()
        )

    await db.log_action(update.effective_user.id, "send_followup", f"Sent follow-up to {sent_count} graduated students")
    return ConversationHandler.END

@admin_required
@error_handler
async def set_followup_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask admin to provide a new follow-up question"""
    survey = await db.ensure_followup_survey()
    current_question = survey.get('question', "Have you found a job after graduation? Please answer Yes or No.")

    await update.message.reply_text(
        "✏️ *Update Follow-Up Question*\n\n"
        f"Current question: {current_question}\n\n"
        "Send the new follow-up question that will be sent to graduated students.",
        parse_mode='Markdown'
    )
    return SET_FOLLOWUP_QUESTION

@admin_required
@error_handler
async def set_followup_question_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save the new follow-up question text"""
    question_text = update.message.text.strip()
    if len(question_text) < 10:
        await update.message.reply_text(
            "❌ The question is too short. Please send a clear yes/no question with at least 10 characters."
        )
        return SET_FOLLOWUP_QUESTION

    survey = await db.update_followup_survey_question(question_text)
    if not survey:
        await update.message.reply_text(
            "❌ Failed to update the follow-up question. Please try again."
        )
        return SET_FOLLOWUP_QUESTION

    await update.message.reply_text(
        "✅ Follow-up question updated successfully.\n\n"
        f"New question: {question_text}",
        reply_markup=get_admin_panel_keyboard(),
        parse_mode='Markdown'
    )
    await db.log_action(update.effective_user.id, "update_followup_question", f"Set follow-up question: {question_text}")
    return ConversationHandler.END

@admin_required
@error_handler
async def handle_approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user approval from inline buttons"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("approve_user_"):
        user_id = int(query.data.split("_")[2])
        
        # Enroll the user
        success = await db.update_user_status(user_id, 'enrolled')
        
        if success:
            user = await db.get_user(user_id)
            if user and user.get('phone_number'):
                from handlers.user import update_backend_student_status_by_phone
                update_backend_student_status_by_phone(user['phone_number'], 'approved')
            
            # Delete the old message
            await query.message.delete()
            
            # Send confirmation to admin
            await query.message.reply_text(
                f"✅ *USER APPROVED SUCCESSFULLY*\n\n"
                f"👤 User: *{user['full_name']}*\n"
                f"🆔 ID: `{user_id}`\n\n"
                f"User has been enrolled and can now access all modules.",
                parse_mode='Markdown',
                reply_markup=get_admin_panel_keyboard()
            )
            
            # Notify the user
            try:
                await context.bot.send_message(
                    user_id,
                    "✅ *Congratulations!*\n\n"
                    "Your account has been **APPROVED** and you are now enrolled!\n\n"
                    "You now have access to all modules and resources.\n\n"
                    "Use /start to begin accessing the content.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
            
            await db.log_action(update.effective_user.id, "approve_user", f"Approved user {user_id}")
        else:
            await query.edit_message_text(
                f"❌ Failed to approve user. Please try again using /admin menu.",
                parse_mode='Markdown'
            )
    
    elif query.data.startswith("view_user_"):
        user_id = int(query.data.split("_")[2])
        user = await db.get_user(user_id)
        
        if user:
            from utils.helpers import format_user_info
            user_info = format_user_info(user)
            
            # Add approve button again
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Approve User", callback_data=f"approve_user_{user_id}")
                ]
            ])
            
            await query.edit_message_text(
                user_info,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        else:
            await query.answer("User not found!", show_alert=True)

            
@admin_required
@error_handler
async def add_module_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a module - Step 1: Get module name"""
    await update.message.reply_text(
        "📝 *Add New Module*\n\n"
        "Please send the **name** of the module:\n"
        "(Example: 'Python Basics' or 'Mathematics')\n\n"
        "Type /cancel to cancel.",
        parse_mode='Markdown'
    )
    return ADD_MODULE_NAME

@admin_required
@error_handler
async def add_module_name_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive module name - Step 1 complete, move to Step 2: Get file"""
    module_name = update.message.text.strip()
    
    # Store module name temporarily
    context.user_data['temp_module'] = {
        'name': module_name
    }
    
    await update.message.reply_text(
        f"✅ Module name saved: *{module_name}*\n\n"
        f"📤 Now please **upload the file** for this module.\n\n"
        f"You can send:\n"
        f"• 📄 Document (PDF, DOC, etc.)\n"
        f"• 🎥 Video\n"
        f"• 🖼️ Photo\n\n"
        f"Type /cancel to cancel the entire process.",
        parse_mode='Markdown'
    )
    return ADD_MODULE_FILE

@admin_required
@error_handler
async def add_module_file_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive file and complete module creation - Step 2"""
    module_data = context.user_data.get('temp_module', {})
    module_name = module_data.get('name')
    
    if not module_name:
        await update.message.reply_text(
            "❌ Session expired. Please start over with /admin and select 'Add Module'.",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    # Check what type of file was sent
    if update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
        file_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_name = f"video_{update.message.video.file_unique_id}.mp4"
        file_type = "video"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_name = f"photo_{update.message.photo[-1].file_unique_id}.jpg"
        file_type = "photo"
    else:
        await update.message.reply_text(
            "❌ Please send a valid file (document, video, or photo).\n\n"
            "Try again or type /cancel to cancel.",
            reply_markup=get_admin_panel_keyboard()
        )
        return ADD_MODULE_FILE
    
    # Check if module already exists
    existing_module = await db.get_module_by_name(module_name)
    if existing_module:
        await update.message.reply_text(
            f"❌ Module '{module_name}' already exists!\n\n"
            f"Please use a different module name.",
            reply_markup=get_admin_panel_keyboard()
        )
        context.user_data.pop('temp_module', None)
        return ConversationHandler.END
    
    # Add the module to database
    success = await db.add_module(module_name, update.effective_user.id)
    
    if not success:
        await update.message.reply_text(
            "❌ Failed to create module. Please try again.",
            reply_markup=get_admin_panel_keyboard()
        )
        context.user_data.pop('temp_module', None)
        return ConversationHandler.END
    
    # Get the newly created module
    module = await db.get_module_by_name(module_name)
    
    # Add the resource to the module
    resource_success = await db.add_resource(
        module['id'], 
        file_id, 
        file_name, 
        file_type, 
        update.effective_user.id
    )
    
    if resource_success:
        await update.message.reply_text(
            f"✅ *Module Created Successfully!*\n\n"
            f"📚 Module: *{module_name}*\n"
            f"📎 File: *{file_name}*\n\n"
            f"The module has been created and the file has been uploaded.\n\n"
            f"You can add more files to this module later using the 'Upload Resource' option.",
            parse_mode='Markdown',
            reply_markup=get_admin_panel_keyboard()
        )
        await db.log_action(
            update.effective_user.id, 
            "add_module_with_file", 
            f"Added module '{module_name}' with file '{file_name}'"
        )
    else:
        # Module was created but file upload failed - delete the module to keep consistency
        await db.delete_module(module['id'])
        await update.message.reply_text(
            f"❌ *Module Creation Failed*\n\n"
            f"The module '{module_name}' was created but the file upload failed.\n"
            f"The module has been removed to maintain consistency.\n\n"
            f"Please try again.",
            parse_mode='Markdown',
            reply_markup=get_admin_panel_keyboard()
        )
    
    # Clean up temp data
    context.user_data.pop('temp_module', None)
    return ConversationHandler.END

@admin_required
@error_handler
async def add_module_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel add module process"""
    context.user_data.pop('temp_module', None)
    await update.message.reply_text(
        "❌ Module creation cancelled.",
        reply_markup=get_admin_panel_keyboard()
    )
    return ConversationHandler.END

@admin_required
@error_handler
async def delete_module_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start deleting a module"""
    modules = await db.get_modules()
    
    if not modules:
        await update.message.reply_text("❌ No modules available to delete.", reply_markup=get_admin_panel_keyboard())
        return ConversationHandler.END
    
    keyboard = []
    row = []
    for i, module in enumerate(modules, 1):
        row.append(InlineKeyboardButton(module['module_name'], callback_data=f"delmod_{module['id']}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="back_to_admin_panel")])
    
    await update.message.reply_text(
        "🗑 *Delete Module*\n\nSelect a module to delete:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return DELETE_MODULE

@admin_required
@error_handler
async def delete_module_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle module deletion callback"""
    query = update.callback_query
    await query.answer()
    
    # Handle back button
    if query.data == "back_to_admin_panel":
        # Send new message instead of editing
        await query.message.delete()
        await query.message.reply_text(
            "🔧 Admin Panel",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    # Handle module deletion
    if query.data.startswith("delmod_"):
        module_id = int(query.data.split("_")[1])
        
        module = await db.get_module(module_id)
        if module:
            success = await db.delete_module(module_id)
            
            if success:
                # Delete the old message and send new one
                await query.message.delete()
                await query.message.reply_text(
                    f"✅ Module '{module['module_name']}' has been deleted successfully!\n\nReturning to Admin Panel...",
                    reply_markup=get_admin_panel_keyboard()
                )
                await db.log_action(update.effective_user.id, "delete_module", f"Deleted module: {module['module_name']}")
            else:
                # Keep the inline keyboard but show error
                await query.edit_message_text(
                    "❌ Failed to delete module. Please try again.\n\nSelect a module to delete:",
                    reply_markup=query.message.reply_markup
                )
        else:
            await query.edit_message_text(
                "❌ Module not found.\n\nSelect a module to delete:",
                reply_markup=query.message.reply_markup
            )
        
        return ConversationHandler.END
    
    return ConversationHandler.END
@admin_required
@error_handler
async def upload_resource_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start uploading a resource to existing module"""
    modules = await db.get_modules()
    
    if not modules:
        await update.message.reply_text("❌ No modules available. Please add a module first.", reply_markup=get_admin_panel_keyboard())
        return ConversationHandler.END
    
    context.user_data['temp'] = {}
    keyboard = []
    row = []
    for i, module in enumerate(modules, 1):
        row.append(InlineKeyboardButton(module['module_name'], callback_data=f"upmod_{module['id']}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="back_to_admin_upload")])
    
    await update.message.reply_text(
        "📤 *Upload Resource*\n\nSelect the module to upload to:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return UPLOAD_RESOURCE_SELECT

@admin_required
@error_handler
async def handle_upload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle upload module selection callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("upmod_"):
        module_id = int(query.data.split("_")[1])
        context.user_data['temp']['module_id'] = module_id
        
        module = await db.get_module(module_id)
        
        await query.edit_message_text(
            f"📤 *Upload Resource to {module['module_name']}*\n\n"
            f"Please send the file you want to upload:\n\n"
            f"You can send:\n"
            f"• 📄 Document (PDF, DOC, etc.)\n"
            f"• 🎥 Video\n"
            f"• 🖼️ Photo\n\n"
            f"Type /cancel to cancel.",
            parse_mode='Markdown'
        )
        return UPLOAD_FILE
    
    elif query.data == "back_to_admin_upload":
        await query.edit_message_text(
            "🔧 Returning to Admin Panel..."
        )
        return ConversationHandler.END
    
    return UPLOAD_RESOURCE_SELECT

@admin_required
@error_handler
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and save file to existing module"""
    module_id = context.user_data['temp'].get('module_id')
    
    if not module_id:
        await update.message.reply_text(
            "❌ Session expired. Please start over.",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    if update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name
        file_type = "document"
    elif update.message.video:
        file_id = update.message.video.file_id
        file_name = f"video_{update.message.video.file_unique_id}.mp4"
        file_type = "video"
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_name = f"photo_{update.message.photo[-1].file_unique_id}.jpg"
        file_type = "photo"
    else:
        await update.message.reply_text(
            "❌ Please send a valid file (document, video, or photo).\n\nTry again:",
            reply_markup=get_admin_panel_keyboard()
        )
        return UPLOAD_FILE
    
    success = await db.add_resource(module_id, file_id, file_name, file_type, update.effective_user.id)
    
    if success:
        module = await db.get_module(module_id)
        await update.message.reply_text(
            f"✅ Resource '{file_name}' has been uploaded to module '{module['module_name']}'!",
            reply_markup=get_admin_panel_keyboard()
        )
        await db.log_action(update.effective_user.id, "upload_resource", f"Uploaded {file_name} to module {module_id}")
    else:
        await update.message.reply_text(
            "❌ Failed to upload resource. Please try again.",
            reply_markup=get_admin_panel_keyboard()
        )
    
    context.user_data.pop('temp', None)
    return ConversationHandler.END

@admin_required
@error_handler
async def list_modules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all modules"""
    modules = await db.get_modules()
    
    if not modules:
        await update.message.reply_text("❌ No modules available.", reply_markup=get_admin_panel_keyboard())
        return
    
    message = "📚 *Available Modules*\n━━━━━━━━━━━━━━━\n\n"
    for i, module in enumerate(modules, 1):
        resources = await db.get_module_resources(module['id'])
        message += f"{i}. *{module['module_name']}*\n"
        message += f"   📎 {len(resources)} resource(s)\n"
        message += f"   🆔 ID: `{module['id']}`\n\n"
    
    message += "\n💡 Use 'Upload Resource' to add files to existing modules."
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=get_admin_panel_keyboard())

@admin_required
@error_handler
async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user management menu"""
    await update.message.reply_text(
        "👥 *User Management*\n\nSelect an option:",
        reply_markup=get_user_management_keyboard(),
        parse_mode='Markdown'
    )

@admin_required
@error_handler
async def enroll_user_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start enrolling a user"""
    pending_users = await db.get_all_users(status='pending')
    
    if not pending_users:
        await update.message.reply_text("❌ No pending users to enroll.", reply_markup=get_user_management_keyboard())
        return ConversationHandler.END
    
    MAX_BUTTONS = 20
    keyboard = []
    displayed_users = pending_users[:MAX_BUTTONS]
    for user in displayed_users:
        keyboard.append([InlineKeyboardButton(f"{user['full_name']} (ID: {user['user_id']})", 
                                             callback_data=f"enroll_{user['user_id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="back_to_user_management")])
    
    extra_text = ""
    if len(pending_users) > MAX_BUTTONS:
        extra_text = (
            f"\n\n⚠️ There are {len(pending_users)} pending users, showing the first {MAX_BUTTONS}. "
            "Use pending enrollment again after reviewing these users."
        )
    
    await update.message.reply_text(
        f"✅ *Enroll User*\n\nSelect a user to enroll:{extra_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return ENROLL_USER

@admin_required
@error_handler
async def remove_enrollment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start removing enrollment from a user"""
    enrolled_users = await db.get_all_users(status='enrolled')
    
    if not enrolled_users:
        await update.message.reply_text("❌ No enrolled users to remove.", reply_markup=get_user_management_keyboard())
        return ConversationHandler.END
    
    keyboard = []
    for user in enrolled_users:
        keyboard.append([InlineKeyboardButton(f"{user['full_name']} (ID: {user['user_id']})", 
                                             callback_data=f"remove_{user['user_id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="back_to_user_management")])
    
    await update.message.reply_text(
        "❌ *Remove Enrollment*\n\nSelect a user to remove enrollment:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return REMOVE_ENROLLMENT

@admin_required
@error_handler
async def handle_remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle enrollment removal callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_user_management":
        await query.edit_message_text(
            "👥 User Management"
        )
        return ConversationHandler.END
    
    if query.data.startswith("remove_"):
        user_id = int(query.data.split("_")[1])
        
        # Change status back to pending
        success = await db.update_user_status(user_id, 'pending')
        
        if success:
            user = await db.get_user(user_id)
            if user and user.get('phone_number'):
                from handlers.user import update_backend_student_status_by_phone
                update_backend_student_status_by_phone(user['phone_number'], 'pending')
            
            # Delete the old message
            await query.message.delete()
            
            # Send confirmation to admin
            await query.message.reply_text(
                f"❌ User '{user['full_name']}' has been removed from enrollment!\n\nReturning to User Management...",
                reply_markup=get_user_management_keyboard()
            )
            
            await db.log_action(update.effective_user.id, "remove_enrollment", f"Removed enrollment for user {user_id}")
            
            # Notify the user
            try:
                await context.bot.send_message(
                    user_id,
                    "❌ *Enrollment Removed*\n\n"
                    "Your enrollment has been removed by an admin. You no longer have access to modules and resources.\n\n"
                    "Please contact an administrator for further information.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            await query.edit_message_text(
                "❌ Failed to remove enrollment. Please try again."
            )
    
    return ConversationHandler.END


@admin_required
@error_handler
async def handle_enroll_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle enrollment callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_user_management":
        await query.edit_message_text(
            "👥 User Management"
        )
        return ConversationHandler.END
    
    if query.data.startswith("enroll_"):
        user_id = int(query.data.split("_")[1])
        
        success = await db.update_user_status(user_id, 'enrolled')
        
        if success:
            user = await db.get_user(user_id)
            if user and user.get('phone_number'):
                from handlers.user import update_backend_student_status_by_phone
                update_backend_student_status_by_phone(user['phone_number'], 'approved')
            
            # Delete the old message instead of editing it
            await query.message.delete()
            
            # Send a new message without inline keyboard
            await query.message.reply_text(
                f"✅ User '{user['full_name']}' has been enrolled successfully!\n\nReturning to User Management...",
                reply_markup=get_user_management_keyboard()
            )
            
            await db.log_action(update.effective_user.id, "enroll_user", f"Enrolled user {user_id}")
            
            # Notify the user
            try:
                await context.bot.send_message(
                    user_id,
                    "✅ *Congratulations!*\n\n"
                    "Your account has been **APPROVED** and you are now enrolled!\n\n"
                    "You now have access to all modules and resources.\n\n"
                    "Use /start to begin accessing the content.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        else:
            await query.edit_message_text(
                "❌ Failed to enroll user. Please try again.",
                reply_markup=get_user_management_keyboard()
            )
    
    return ConversationHandler.END

@admin_required
@error_handler
async def enroll_user_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Restart the enroll user flow if the admin clicks the button again while still in state."""
    return await enroll_user_start(update, context)

@admin_required
@error_handler
async def enroll_user_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel enroll user operation and return to user management."""
    await update.message.reply_text(
        "❌ Enrollment process cancelled. Use the user management menu to start again.",
        reply_markup=get_user_management_keyboard()
    )
    return ConversationHandler.END

@admin_required
@error_handler
async def remove_enrollment_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel remove enrollment operation and return to user management."""
    await update.message.reply_text(
        "❌ Remove enrollment process cancelled. Use the user management menu to start again.",
        reply_markup=get_user_management_keyboard()
    )
    return ConversationHandler.END

@admin_required
@error_handler
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List users by status"""
    if "Pending" in update.message.text:
        status = 'pending'
        title = "Pending Users"
    else:
        status = 'enrolled'
        title = "Enrolled Users"
    
    users = await db.get_all_users(status=status)
    
    if not users:
        await update.message.reply_text(f"❌ No {title.lower()} found.", reply_markup=get_user_management_keyboard())
        return
    
    message = f"👥 *{title}*\n━━━━━━━━━━━━━━━\n\n"
    for i, user in enumerate(users[:20], 1):
        message += f"{i}. *{user['full_name']}*\n"
        message += f"   🆔 ID: `{user['user_id']}`\n"
        # Format the datetime properly
        registered_date = user['registered_at']
        if isinstance(registered_date, str):
            display_date = registered_date[:10]
        else:
            # It's a datetime object, format it
            display_date = registered_date.strftime('%Y-%m-%d')
        message += f"   📅 Registered: {display_date}\n\n"
    
    if len(users) > 20:
        message += f"\n*Showing 20 of {len(users)} users*"
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=get_user_management_keyboard())

@admin_required
@error_handler
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast message"""
    # Store broadcast state in user_data
    context.user_data['broadcast_active'] = True
    
    await update.message.reply_text(
        "📢 *BROADCAST MESSAGE*\n\n"
        "Send the message you want to broadcast to all enrolled users.\n\n"
        "📝 You can send:\n"
        "• Text messages\n"
        "• Photos (with or without caption)\n"
        "• Videos (with or without caption)\n"
        "• Documents (with or without caption)\n\n"
        "⚠️ To CANCEL broadcast, type:\n"
        "/cancel_broadcast\n\n"
        "Type /cancel_broadcast at any time to cancel.",
        parse_mode=None  # Changed from 'Markdown' to None
    )
    return BROADCAST_MESSAGE

@admin_required
@error_handler
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to all enrolled users"""
    
    # Check if broadcast is active
    if not context.user_data.get('broadcast_active', False):
        # Broadcast has been completed or cancelled, end the conversation
        return ConversationHandler.END
    
    # Check if user wants to cancel
    if update.message.text and update.message.text == '/cancel_broadcast':
        context.user_data['broadcast_active'] = False
        await update.message.reply_text(
            "❌ Broadcast cancelled successfully!",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    # If the admin sends another command during broadcast, cancel it and exit
    if update.message.text and update.message.text.startswith('/') and update.message.text != '/cancel_broadcast':
        context.user_data['broadcast_active'] = False
        context.user_data.pop('broadcast_content', None)
        await update.message.reply_text(
            "⚠️ Broadcast interrupted. The broadcast sequence has been cancelled.\n\n"
            "Please use the admin menu again or send the command you intended to use.",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    # If the admin presses a keyboard button while in broadcast flow, cancel the broadcast state
    button_texts = [
        "➕ Add Module", "🗑 Delete Module", "📤 Upload", 
        "📋 Modules", "👥 Users", "📢 Broadcast", "📣 Follow-Up", "✏️ Set Question",
        "📊 Statistics", "🔙 Back to Admin Panel", "👥 View Users",
        "📊 Admin Panel", "✅ Enroll User", "❌ Remove Enrollment",
        "📋 Pending Users", "📋 Enrolled Users", "🔙 Back to User Management",
        "📚 View Modules", "ℹ️ My Status",
        # Keep legacy labels for compatibility
        "📤 Upload Resource", "📋 List All Modules", "👥 Manage Users", "📢 Broadcast Message",
        "📋 List Pending Users", "📋 List Enrolled Users", "📊 View Statistics"
    ]
    
    if update.message.text and update.message.text in button_texts:
        context.user_data['broadcast_active'] = False
        context.user_data.pop('broadcast_content', None)
        await update.message.reply_text(
            "⚠️ Broadcast interrupted. The broadcast sequence has been cancelled.\n\n"
            "Please select your next action from the admin panel again.",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    # Get all enrolled users
    users = await db.get_all_users(status='enrolled')
    
    if not users:
        await update.message.reply_text(
            "❌ No enrolled users to broadcast to.",
            reply_markup=get_admin_panel_keyboard()
        )
        context.user_data['broadcast_active'] = False
        return ConversationHandler.END
    
    # Confirm before broadcasting
    confirm_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, Send", callback_data="confirm_broadcast"),
            InlineKeyboardButton("❌ No, Cancel", callback_data="cancel_broadcast")
        ]
    ])
    
    # Store the broadcast content in context
    context.user_data['broadcast_content'] = {
        'type': 'text' if update.message.text else 'media',
        'data': update.message
    }
    
    await update.message.reply_text(
        f"⚠️ *Broadcast Confirmation*\n\n"
        f"You are about to send this message to *{len(users)}* enrolled users.\n\n"
        f"Are you sure you want to proceed?",
        parse_mode='Markdown',
        reply_markup=confirm_keyboard
    )
    return BROADCAST_MESSAGE

@admin_required
@error_handler
async def broadcast_confirmation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast confirmation"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_broadcast":
        broadcast_content = context.user_data.get('broadcast_content', {})
        users = await db.get_all_users(status='enrolled')
        
        if not users:
            await query.edit_message_text(
                "❌ No enrolled users to broadcast to.",
                reply_markup=get_admin_panel_keyboard()
            )
            context.user_data['broadcast_active'] = False
            context.user_data.pop('broadcast_content', None)
            return ConversationHandler.END
        
        success_count = 0
        fail_count = 0
        
        try:
            # Send progress message
            progress_msg = await query.edit_message_text(
                f"📢 Broadcasting in progress...\n0/{len(users)} users",
                reply_markup=None
            )
            
            for i, user in enumerate(users):
                try:
                    msg_data = broadcast_content.get('data')
                    
                    if broadcast_content.get('type') == 'text':
                        await context.bot.send_message(
                            chat_id=user['user_id'],
                            text=msg_data.text
                        )
                    elif msg_data.photo:
                        await context.bot.send_photo(
                            chat_id=user['user_id'],
                            photo=msg_data.photo[-1].file_id,
                            caption=msg_data.caption
                        )
                    elif msg_data.video:
                        await context.bot.send_video(
                            chat_id=user['user_id'],
                            video=msg_data.video.file_id,
                            caption=msg_data.caption
                        )
                    elif msg_data.document:
                        await context.bot.send_document(
                            chat_id=user['user_id'],
                            document=msg_data.document.file_id,
                            caption=msg_data.caption
                        )
                    
                    success_count += 1
                    
                    # Update progress every 10 users
                    if (i + 1) % 10 == 0:
                        await progress_msg.edit_text(
                            f"📢 Broadcasting in progress...\n{i + 1}/{len(users)} users sent"
                        )
                        
                except Exception as e:
                    logger.error(f"Failed to send to user {user['user_id']}: {e}")
                    fail_count += 1
            
            # Clean up
            context.user_data['broadcast_active'] = False
            context.user_data.pop('broadcast_content', None)
            
            try:
                await progress_msg.edit_text(
                    f"📢 *Broadcast Complete*\n\n"
                    f"✅ Sent to: {success_count} users\n"
                    f"❌ Failed: {fail_count} users\n\n"
                    f"Success Rate: {(success_count/len(users)*100):.1f}%",
                    parse_mode='Markdown',
                    reply_markup=get_admin_panel_keyboard()
                )
            except Exception as e:
                logger.error(f"Failed to edit broadcast completion message: {e}")
                # If editing fails, send a new message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"📢 *Broadcast Complete*\n\n"
                         f"✅ Sent to: {success_count} users\n"
                         f"❌ Failed: {fail_count} users\n\n"
                         f"Success Rate: {(success_count/len(users)*100):.1f}%",
                    parse_mode='Markdown',
                    reply_markup=get_admin_panel_keyboard()
                )
            
            await db.log_action(update.effective_user.id, "broadcast", f"Broadcast to {success_count} users")
            return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error during broadcast: {e}")
            # Clean up on error
            context.user_data['broadcast_active'] = False
            context.user_data.pop('broadcast_content', None)
            try:
                await query.edit_message_text(
                    "❌ An error occurred during broadcast. Please try again.",
                    reply_markup=get_admin_panel_keyboard()
                )
            except Exception as edit_error:
                logger.error(f"Failed to edit message after broadcast error: {edit_error}")
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text="❌ An error occurred during broadcast. Please try again.",
                    reply_markup=get_admin_panel_keyboard()
                )
            return ConversationHandler.END
    
    elif query.data == "cancel_broadcast":
        context.user_data['broadcast_active'] = False
        context.user_data.pop('broadcast_content', None)
        await query.edit_message_text(
            "❌ Broadcast cancelled successfully!",
            reply_markup=get_admin_panel_keyboard()
        )
        return ConversationHandler.END
    
    return ConversationHandler.END

@admin_required
@error_handler
async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast from command"""
    context.user_data['broadcast_active'] = False
    context.user_data.pop('broadcast_content', None)
    await update.message.reply_text(
        "❌ Broadcast cancelled successfully!",
        reply_markup=get_admin_panel_keyboard()
    )
    return ConversationHandler.END

@admin_required
@error_handler
async def view_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View bot statistics"""
    users = await db.get_all_users()
    total_users = len(users)
    enrolled_users = len([u for u in users if u.get('status') == 'enrolled'])
    pending_users = len([u for u in users if u.get('status') == 'pending'])
    modules = await db.get_modules()
    
    total_resources = 0
    for module in modules:
        resources = await db.get_module_resources(module['id'])
        total_resources += len(resources)
    
    enrollment_rate = (enrolled_users / total_users * 100) if total_users > 0 else 0
    
    stats = f"""
📊 *Bot Statistics*
━━━━━━━━━━━━━━━

👥 *Users*
├ Total Users: {total_users}
├ Enrolled: {enrolled_users}
└ Pending: {pending_users}

📚 *Content*
├ Modules: {len(modules)}
└ Resources: {total_resources}

🎯 *Engagement*
└ Enrollment Rate: {enrollment_rate:.1f}%
"""
    
    await update.message.reply_text(stats, parse_mode='Markdown', reply_markup=get_admin_panel_keyboard())