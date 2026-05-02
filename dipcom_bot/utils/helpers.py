def validate_full_name(full_name: str) -> tuple[bool, str]:
    """
    Validate full name format.
    Expected format: First Name Father's Name (at least two words)
    """
    if not full_name or not full_name.strip():
        return False, "Full name cannot be empty."
    
    parts = full_name.strip().split()
    if len(parts) < 2:
        return False, "Please provide your full name with at least first name and father's name (e.g., 'John Doe')."
    
    # Check for reasonable length
    if len(full_name) > 100:
        return False, "Full name is too long (max 100 characters)."
    
    # Check if all parts are alphabetic (allow spaces and apostrophes)
    for part in parts:
        if not part.replace("'", "").replace("-", "").isalpha():
            return False, "Full name should only contain letters, spaces, hyphens, and apostrophes."
    
    return True, "Valid"

def format_user_info(user: dict) -> str:
    """
    Format user information for display
    """
    status_emoji = {
        'pending': '⏳',
        'enrolled': '✅',
        'rejected': '❌'
    }
    
    status = user.get('status', 'unknown')
    emoji = status_emoji.get(status, '❓')
    
    info = f"👤 *Your Information*\n\n"
    info += f"Name: {user.get('full_name', 'N/A')}\n"
    info += f"Status: {emoji} {status.capitalize()}\n"
    if user.get('phone_number'):
        info += f"Phone: {user.get('phone_number')}\n"
    if user.get('username'):
        info += f"Username: @{user.get('username')}\n"
    
    return info