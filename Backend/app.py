"""
Whisper-WA Backend Server
Flask application with complete API for admin dashboard and forensic analysis
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime
import os

# Import models and helper functions
from models import db, User, AccountRequest, Case
from database import (
    init_database, 
    get_all_requests, 
    get_all_active_users,
    create_user_from_request,
    deactivate_user,
    get_admin_stats,
    reject_request,
    get_request_by_id,
    get_user_by_id,
    get_user_by_email
)
from auth import (
    authenticate_user,
    generate_token,
    login_required,
    admin_required,
    get_current_user
)

# Import existing acquisition function
from acquisition import pull_whatsapp_evidence


# ========================================
# Flask App Configuration
# ========================================
app = Flask(__name__, template_folder='../Frontend', static_folder='../Frontend')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///whisper_wa.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'whisper-wa-secret-2026-change-in-production'

# Initialize database
db.init_app(app)

# Enable CORS for frontend
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})


# ========================================
# Initialize Database on First Run
# ========================================
with app.app_context():
    init_database(app)


# ========================================
# Frontend Routes (HTML Pages)
# ========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('../Frontend', filename)


# ========================================
# Authentication APIs
# ========================================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    User login endpoint
    
    Request Body:
        {
            "email": "user@example.com",
            "password": "password123"
        }
    
    Response:
        {
            "success": true,
            "message": "Login successful",
            "token": "jwt_token_here",
            "user": {...}
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        email = data['email']
        password = data['password']
        
        # Authenticate user
        success, user, message = authenticate_user(email, password)
        
        if not success:
            return jsonify({
                'success': False,
                'message': message
            }), 401
        
        # Generate JWT token
        token = generate_token(user)
        
        return jsonify({
            'success': True,
            'message': message,
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Login error: {str(e)}'
        }), 500


@app.route('/api/auth/verify', methods=['GET'])
@login_required
def verify_token(current_user):
    """
    Verify if token is still valid
    
    Headers:
        Authorization: Bearer <token>
    
    Response:
        {
            "success": true,
            "user": {...}
        }
    """
    return jsonify({
        'success': True,
        'user': current_user.to_dict()
    }), 200


@app.route('/api/auth/register-request', methods=['POST'])
def register_request():
    """
    Submit account request
    
    Request Body:
        {
            "name": "John Doe",
            "email": "john@example.com",
            "job_title": "Forensic Analyst",
            "department": "Digital Forensics",
            "reason": "Need access for Case #123"
        }
    
    Response:
        {
            "success": true,
            "message": "Request submitted successfully",
            "request_id": 1
        }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'job_title', 'reason']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'success': False,
                    'message': f'Field "{field}" is required'
                }), 400
        
        # Check if email already exists
        existing_user = get_user_by_email(data['email'])
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'An account with this email already exists'
            }), 400
        
        # Check if request already submitted
        existing_request = AccountRequest.query.filter_by(
            email=data['email'], 
            status='pending'
        ).first()
        
        if existing_request:
            return jsonify({
                'success': False,
                'message': 'A request with this email is already pending'
            }), 400
        
        # Create new request
        new_request = AccountRequest(
            name=data['name'],
            email=data['email'],
            job_title=data['job_title'],
            department=data.get('department', ''),
            reason=data['reason'],
            status='pending'
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Request submitted successfully. You will be notified once reviewed.',
            'request_id': new_request.id
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error submitting request: {str(e)}'
        }), 500


# ========================================
# Admin APIs - Dashboard Stats
# ========================================

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def admin_stats(current_user):
    """
    Get admin dashboard statistics
    
    Response:
        {
            "success": true,
            "stats": {
                "pending_requests": 5,
                "active_users": 12,
                "rejected_requests": 3,
                "total_requests": 20
            }
        }
    """
    try:
        stats = get_admin_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching stats: {str(e)}'
        }), 500


# ========================================
# Admin APIs - Account Requests
# ========================================

@app.route('/api/admin/requests', methods=['GET'])
@admin_required
def get_requests(current_user):
    """
    Get all account requests (with optional status filter)
    
    Query Parameters:
        ?status=pending (optional: pending, approved, rejected)
    
    Response:
        {
            "success": true,
            "requests": [...]
        }
    """
    try:
        status = request.args.get('status', None)
        
        requests = get_all_requests(status)
        
        return jsonify({
            'success': True,
            'requests': [r.to_dict() for r in requests],
            'count': len(requests)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching requests: {str(e)}'
        }), 500


@app.route('/api/admin/requests/pending', methods=['GET'])
@admin_required
def get_pending_requests(current_user):
    """
    Get only pending account requests
    
    Response:
        {
            "success": true,
            "requests": [...]
        }
    """
    try:
        requests = get_all_requests(status='pending')
        
        return jsonify({
            'success': True,
            'requests': [r.to_dict() for r in requests],
            'count': len(requests)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching pending requests: {str(e)}'
        }), 500


@app.route('/api/admin/approve/<int:request_id>', methods=['POST'])
@admin_required
def approve_request(current_user, request_id):
    """
    Approve an account request
    
    Request Body (optional):
        {
            "default_password": "CustomPassword123"
        }
    
    Response:
        {
            "success": true,
            "message": "Request approved successfully",
            "user": {...}
        }
    """
    try:
        # Get the request
        account_request = get_request_by_id(request_id)
        
        if not account_request:
            return jsonify({
                'success': False,
                'message': 'Request not found'
            }), 404
        
        if account_request.status != 'pending':
            return jsonify({
                'success': False,
                'message': f'Request already {account_request.status}'
            }), 400
        
        # Get custom password if provided
        data = request.get_json() or {}
        default_password = data.get('default_password', 'Whisper@2026')
        
        # Create user from request
        new_user = create_user_from_request(
            account_request, 
            current_user.id, 
            default_password
        )
        
        return jsonify({
            'success': True,
            'message': f'Request approved. User {new_user.name} has been activated.',
            'user': new_user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error approving request: {str(e)}'
        }), 500


@app.route('/api/admin/reject/<int:request_id>', methods=['POST'])
@admin_required
def reject_account_request(current_user, request_id):
    """
    Reject an account request
    
    Response:
        {
            "success": true,
            "message": "Request rejected successfully"
        }
    """
    try:
        success = reject_request(request_id, current_user.id)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'Request not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Request rejected successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error rejecting request: {str(e)}'
        }), 500


# ========================================
# Admin APIs - User Management
# ========================================

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users(current_user):
    """
    Get all active users
    
    Response:
        {
            "success": true,
            "users": [...]
        }
    """
    try:
        users = get_all_active_users()
        
        return jsonify({
            'success': True,
            'users': [u.to_dict() for u in users],
            'count': len(users)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error fetching users: {str(e)}'
        }), 500


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def revoke_user(current_user, user_id):
    """
    Revoke user access (deactivate)
    
    Response:
        {
            "success": true,
            "message": "User access revoked"
        }
    """
    try:
        # Prevent self-deactivation
        if user_id == current_user.id:
            return jsonify({
                'success': False,
                'message': 'You cannot deactivate your own account'
            }), 400
        
        success = deactivate_user(user_id)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'User not found or cannot be deactivated'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'User access revoked successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error revoking access: {str(e)}'
        }), 500


# ========================================
# Forensic Analysis APIs (Existing)
# ========================================

@app.route('/api/acquisition/run', methods=['POST'])
@login_required
def run_acquisition(current_user):
    """
    Run WhatsApp data acquisition
    (Protected - requires login)
    """
    try:
        data = request.get_json() or {}
        case_id = data.get('case_id', 'Case_001')
        
        results = pull_whatsapp_evidence(case_id)
        
        return jsonify({
            'success': True,
            'results': results
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Acquisition error: {str(e)}'
        }), 500


# ========================================
# Health Check
# ========================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Simple health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'service': 'Whisper-WA Backend',
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


# ========================================
# Error Handlers
# ========================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'message': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({
        'success': False,
        'message': 'Internal server error'
    }), 500


# ========================================
# Run Server
# ========================================

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Whisper-WA Backend Server Starting...")
    print("=" * 50)
    print(f"📊 Database: whisper_wa.db")
    print(f"🔐 Default Admin: admin@whisper-wa.local / admin123")
    print(f"🌐 Server: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
