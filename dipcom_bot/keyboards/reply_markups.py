from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

def get_main_keyboard(is_admin: bool = False, is_enrolled: bool = False):
    """Get main menu keyboard - 2 buttons per row"""
    keyboard = []
    
    row1 = []
    if is_enrolled:
        row1.append(KeyboardButton("📚 View Modules"))
    row1.append(KeyboardButton("ℹ️ My Status"))
    if row1:
        keyboard.append(row1)
    
    if is_admin:
        keyboard.append([KeyboardButton("👥 View Users"), KeyboardButton("📊 Admin Panel")])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_panel_keyboard():
    """Get admin panel keyboard - 2 buttons per row, NO back to main menu"""
    keyboard = [
        [KeyboardButton("➕ Add Module"), KeyboardButton("🗑 Delete Module")],
        [KeyboardButton("📤 Upload Resource"), KeyboardButton("📋 List All Modules")],
        [KeyboardButton("👥 Manage Users"), KeyboardButton("📢 Broadcast Message")],
        [KeyboardButton("📊 View Statistics")]  # Removed "Back to Main Menu" from here
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_user_management_keyboard():
    """Get user management keyboard - 2 buttons per row"""
    keyboard = [
        [KeyboardButton("✅ Enroll User"), KeyboardButton("❌ Remove Enrollment")],
        [KeyboardButton("📋 List Pending Users"), KeyboardButton("📋 List Enrolled Users")],
        [KeyboardButton("🔙 Back to Admin Panel")]  # This one stays - goes back to admin panel
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_module_selection_keyboard(modules):
    """Get module selection inline keyboard - 2 modules per row"""
    keyboard = []
    row = []
    for i, module in enumerate(modules, 1):
        row.append(InlineKeyboardButton(module['module_name'], callback_data=f"module_{module['id']}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_resource_keyboard(resources):
    """Get resource selection inline keyboard - 1 per row (for better readability)"""
    keyboard = []
    for resource in resources:
        display_name = resource['file_name'][:30] + "..." if len(resource['file_name']) > 30 else resource['file_name']
        keyboard.append([InlineKeyboardButton(f"📄 {display_name}", callback_data=f"download_{resource['id']}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Modules", callback_data="back_to_modules")])
    return InlineKeyboardMarkup(keyboard)

def get_back_button():
    """Get simple back button"""
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(keyboard)