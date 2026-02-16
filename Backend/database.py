"""
Database Helper Functions for Whisper-WA
"""

from models import db, User, AccountRequest, Case
from datetime import datetime
import os


def init_database(app):
    """
    Initialize database and create all tables
    """
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created successfully")
        
        # Create default admin if not exists
        create_default_admin()
        print("✓ Default admin user initialized")


def create_default_admin():
    """
    Create default admin user (admin@whisper-wa.local / admin123)
    """
    admin_email = "admin@whisper-wa.local"
    
    # Check if admin already exists
    existing_admin = User.query.filter_by(email=admin_email).first()
    
    if not existing_admin:
        admin = User(
            name="System Administrator",
            email=admin_email,
            job_title="System Admin",
            department="IT Security",
            role="admin",
            is_active=True,
            approved_at=datetime.utcnow()
        )
        admin.set_password("admin123")
        
        db.session.add(admin)
        db.session.commit()
        print(f"✓ Default admin created: {admin_email}")
    else:
        print(f"✓ Admin already exists: {admin_email}")


def get_pending_requests_count():
    """
    Get count of pending account requests
    """
    return AccountRequest.query.filter_by(status='pending').count()


def get_active_users_count():
    """
    Get count of active users
    """
    return User.query.filter_by(is_active=True).count()


def get_user_by_email(email):
    """
    Get user by email
    """
    return User.query.filter_by(email=email).first()


def get_user_by_id(user_id):
    """
    Get user by ID
    """
    return User.query.get(user_id)


def get_request_by_id(request_id):
    """
    Get account request by ID
    """
    return AccountRequest.query.get(request_id)


def create_user_from_request(request, approved_by_id, default_password="Whisper@2026"):
    """
    Create a new user from an approved request
    
    Args:
        request: AccountRequest object
        approved_by_id: ID of admin who approved
        default_password: Default password for new user
    
    Returns:
        User object
    """
    # Create new user
    user = User(
        name=request.name,
        email=request.email,
        job_title=request.job_title,
        department=request.department,
        role='user',
        is_active=True,
        approved_at=datetime.utcnow()
    )
    user.set_password(default_password)
    
    # Update request status
    request.status = 'approved'
    request.reviewed_at = datetime.utcnow()
    request.reviewed_by = approved_by_id
    
    # Save to database
    db.session.add(user)
    db.session.commit()
    
    return user


def get_all_requests(status=None):
    """
    Get all account requests, optionally filtered by status
    
    Args:
        status: 'pending', 'approved', or 'rejected' (None for all)
    
    Returns:
        List of AccountRequest objects
    """
    if status:
        return AccountRequest.query.filter_by(status=status).order_by(
            AccountRequest.submitted_at.desc()
        ).all()
    else:
        return AccountRequest.query.order_by(
            AccountRequest.submitted_at.desc()
        ).all()


def get_all_active_users():
    """
    Get all active users
    """
    return User.query.filter_by(is_active=True).order_by(
        User.approved_at.desc()
    ).all()


def deactivate_user(user_id):
    """
    Deactivate a user (revoke access)
    
    Args:
        user_id: ID of user to deactivate
    
    Returns:
        True if successful, False otherwise
    """
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    # Don't allow deactivating admin
    if user.role == 'admin':
        return False
    
    user.is_active = False
    db.session.commit()
    
    return True


def get_admin_stats():
    """
    Get statistics for admin dashboard
    
    Returns:
        Dictionary with stats
    """
    return {
        'pending_requests': AccountRequest.query.filter_by(status='pending').count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'rejected_requests': AccountRequest.query.filter_by(status='rejected').count(),
        'total_requests': AccountRequest.query.count(),
        'total_cases': Case.query.count() if Case.query.first() else 0
    }


def search_users(query):
    """
    Search users by name or email
    
    Args:
        query: Search string
    
    Returns:
        List of matching users
    """
    search_pattern = f"%{query}%"
    return User.query.filter(
        (User.name.like(search_pattern)) | (User.email.like(search_pattern))
    ).all()


def reject_request(request_id, reviewed_by_id):
    """
    Reject an account request
    
    Args:
        request_id: ID of request to reject
        reviewed_by_id: ID of admin who rejected
    
    Returns:
        True if successful, False otherwise
    """
    request = AccountRequest.query.get(request_id)
    
    if not request:
        return False
    
    request.status = 'rejected'
    request.reviewed_at = datetime.utcnow()
    request.reviewed_by = reviewed_by_id
    
    db.session.commit()
    
    return True


def cleanup_old_requests(days=30):
    """
    Delete rejected/approved requests older than specified days
    (For database maintenance)
    
    Args:
        days: Number of days to keep
    """
    from datetime import timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    old_requests = AccountRequest.query.filter(
        AccountRequest.status.in_(['rejected', 'approved']),
        AccountRequest.reviewed_at < cutoff_date
    ).all()
    
    count = len(old_requests)
    
    for request in old_requests:
        db.session.delete(request)
    
    db.session.commit()
    
    return count
