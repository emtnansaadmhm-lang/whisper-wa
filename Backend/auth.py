"""
Authentication Functions for Whisper-WA
Handles login, JWT tokens, and route protection
"""

from functools import wraps
from flask import request, jsonify
import jwt
from datetime import datetime, timedelta
from models import User, db


# Secret key for JWT (in production, use environment variable)
SECRET_KEY = "whisper-wa-secret-key-2026-change-in-production"
TOKEN_EXPIRATION_HOURS = 24


def generate_token(user):
    """
    Generate JWT token for authenticated user
    
    Args:
        user: User object
    
    Returns:
        JWT token string
    """
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token


def verify_token(token):
    """
    Verify JWT token and return payload
    
    Args:
        token: JWT token string
    
    Returns:
        Payload dictionary if valid, None if invalid
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


def authenticate_user(email, password):
    """
    Authenticate user with email and password
    
    Args:
        email: User email
        password: User password
    
    Returns:
        Tuple: (success: bool, user: User or None, message: str)
    """
    # Find user by email
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return False, None, "Invalid email or password"
    
    # Check if account is active
    if not user.is_active:
        return False, None, "Account has been deactivated. Please contact administrator."
    
    # Verify password
    if not user.check_password(password):
        return False, None, "Invalid email or password"
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    return True, user, "Login successful"


def get_current_user(token):
    """
    Get current user from JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        User object or None
    """
    payload = verify_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get('user_id')
    user = User.query.get(user_id)
    
    return user


# ========================================
# Decorator Functions for Route Protection
# ========================================

def login_required(f):
    """
    Decorator to protect routes - requires valid JWT token
    
    Usage:
        @app.route('/api/protected')
        @login_required
        def protected_route(current_user):
            return jsonify({'message': f'Hello {current_user.name}'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Expected format: "Bearer <token>"
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid token format. Use: Bearer <token>'
                }), 401
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Authentication token is missing'
            }), 401
        
        # Verify token
        current_user = get_current_user(token)
        
        if not current_user:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token'
            }), 401
        
        # Pass current user to the route function
        return f(current_user=current_user, *args, **kwargs)
    
    return decorated_function


def admin_required(f):
    """
    Decorator to protect admin-only routes
    
    Usage:
        @app.route('/api/admin/users')
        @admin_required
        def admin_route(current_user):
            return jsonify({'message': 'Admin access granted'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({
                    'success': False,
                    'message': 'Invalid token format'
                }), 401
        
        if not token:
            return jsonify({
                'success': False,
                'message': 'Authentication required'
            }), 401
        
        # Verify token
        current_user = get_current_user(token)
        
        if not current_user:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired token'
            }), 401
        
        # Check if user is admin
        if current_user.role != 'admin':
            return jsonify({
                'success': False,
                'message': 'Admin privileges required'
            }), 403
        
        # Pass current user to the route function
        return f(current_user=current_user, *args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """
    Decorator for routes that work with or without authentication
    If token is provided and valid, current_user is passed, otherwise None
    
    Usage:
        @app.route('/api/public')
        @optional_auth
        def public_route(current_user=None):
            if current_user:
                return jsonify({'message': f'Hello {current_user.name}'})
            else:
                return jsonify({'message': 'Hello guest'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        current_user = None
        
        # Try to get token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]
                current_user = get_current_user(token)
            except (IndexError, Exception):
                pass  # Continue without authentication
        
        return f(current_user=current_user, *args, **kwargs)
    
    return decorated_function


def validate_password(password):
    """
    Validate password strength
    
    Requirements:
    - At least 8 characters
    - Contains uppercase and lowercase
    - Contains at least one digit
    
    Args:
        password: Password string
    
    Returns:
        Tuple: (valid: bool, message: str)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"


def change_password(user, old_password, new_password):
    """
    Change user password
    
    Args:
        user: User object
        old_password: Current password
        new_password: New password
    
    Returns:
        Tuple: (success: bool, message: str)
    """
    # Verify old password
    if not user.check_password(old_password):
        return False, "Current password is incorrect"
    
    # Validate new password
    valid, message = validate_password(new_password)
    if not valid:
        return False, message
    
    # Set new password
    user.set_password(new_password)
    db.session.commit()
    
    return True, "Password changed successfully"


def reset_password(user, new_password):
    """
    Reset user password (admin function)
    
    Args:
        user: User object
        new_password: New password
    
    Returns:
        Tuple: (success: bool, message: str)
    """
    # Validate new password
    valid, message = validate_password(new_password)
    if not valid:
        return False, message
    
    # Set new password
    user.set_password(new_password)
    db.session.commit()
    
    return True, "Password reset successfully"
