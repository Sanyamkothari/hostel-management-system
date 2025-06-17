"""
User utilities for the Hostel Management System.
"""
from flask import g

def get_user_attribute(attribute_name, default=None):
    """
    Safely get a user attribute from g.user dictionary.
    
    Args:
        attribute_name (str): The name of the attribute to get
        default: The default value to return if the attribute doesn't exist
        
    Returns:
        The value of the attribute or the default value if not found
    """
    if hasattr(g, 'user') and g.user and isinstance(g.user, dict):
        return g.user.get(attribute_name, default)
    return default
