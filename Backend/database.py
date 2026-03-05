"""
database.py - System Database Management
إدارة قاعدة بيانات النظام (المستخدمين، القضايا، التقارير)
"""

import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict
import hashlib
import secrets


DB_PATH = "whisper_wa.db"


def get_connection():
    """
    إنشاء اتصال بقاعدة البيانات
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    إنشاء جداول قاعدة البيانات
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # جدول المستخدمين
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        job_title TEXT,
        department TEXT,
        role TEXT DEFAULT 'user',
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """)
    
    # جدول طلبات الوصول
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS access_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        job_title TEXT NOT NULL,
        department TEXT,
        reason TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reviewed_at TIMESTAMP,
        reviewed_by INTEGER,
        FOREIGN KEY (reviewed_by) REFERENCES users(id)
    )
    """)
    
    # جدول القضايا
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT UNIQUE NOT NULL,
        case_number TEXT NOT NULL,
        investigator_id INTEGER NOT NULL,
        device_info TEXT,
        device_model TEXT,
        device_os TEXT,
        acquisition_date TIMESTAMP,
        status TEXT DEFAULT 'in_progress',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (investigator_id) REFERENCES users(id)
    )
    """)
    
    # جدول التقارير
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_id TEXT NOT NULL,
        report_title TEXT,
        report_type TEXT,
        total_messages INTEGER DEFAULT 0,
        total_chats INTEGER DEFAULT 0,
        generated_by INTEGER NOT NULL,
        generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        file_path TEXT,
        status TEXT DEFAULT 'completed',
        FOREIGN KEY (case_id) REFERENCES cases(case_id),
        FOREIGN KEY (generated_by) REFERENCES users(id)
    )
    """)
    
    # جدول سجلات النشاط
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT,
        entity_id TEXT,
        details TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    # جدول الجلسات
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        session_token TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Database initialized successfully!")


def create_admin_user():
    """
    إنشاء حساب المسؤول الافتراضي
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # التحقق من وجود الأدمن
    cursor.execute("SELECT id FROM users WHERE email = ?", ("admin@whisper-wa.local",))
    if cursor.fetchone():
        print("ℹ️ Admin user already exists")
        conn.close()
        return
    
    # إنشاء الأدمن
    password_hash = hash_password("admin123")
    
    cursor.execute("""
    INSERT INTO users (name, email, password_hash, job_title, department, role, status)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        "System Administrator",
        "admin@whisper-wa.local",
        password_hash,
        "System Admin",
        "IT Security",
        "admin",
        "active"
    ))
    
    conn.commit()
    conn.close()
    
    print("✅ Admin user created: admin@whisper-wa.local / admin123")


# ========================================
# USER MANAGEMENT
# ========================================

def hash_password(password: str) -> str:
    """
    تشفير كلمة المرور باستخدام SHA-256
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """
    التحقق من كلمة المرور
    """
    return hash_password(password) == password_hash


def create_user(name: str, email: str, password: str, job_title: str, 
                department: str = None, role: str = "user") -> dict:
    """
    إنشاء مستخدم جديد
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = hash_password(password)
        
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, job_title, department, role)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (name, email, password_hash, job_title, department, role))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        log_activity(user_id, "user_created", "user", str(user_id), 
                    f"User {name} created")
        
        return {"ok": True, "user_id": user_id, "message": "User created successfully"}
        
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "Email already exists"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def authenticate_user(email: str, password: str) -> dict:
    """
    تسجيل دخول المستخدم
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, name, email, password_hash, role, status
    FROM users WHERE email = ?
    """, (email,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return {"ok": False, "error": "Invalid credentials"}
    
    if user["status"] != "active":
        conn.close()
        return {"ok": False, "error": "Account is not active"}
    
    if not verify_password(password, user["password_hash"]):
        conn.close()
        return {"ok": False, "error": "Invalid credentials"}
    
    # تحديث آخر تسجيل دخول
    cursor.execute("""
    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
    """, (user["id"],))
    
    # إنشاء session token
    session_token = secrets.token_urlsafe(32)
    
    cursor.execute("""
    INSERT INTO sessions (user_id, session_token, expires_at)
    VALUES (?, ?, datetime('now', '+24 hours'))
    """, (user["id"], session_token))
    
    conn.commit()
    
    log_activity(user["id"], "login", "user", str(user["id"]), "User logged in")
    
    conn.close()
    
    return {
        "ok": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        },
        "session_token": session_token
    }


def get_user_by_id(user_id: int) -> Optional[dict]:
    """
    جلب بيانات مستخدم حسب ID
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, name, email, job_title, department, role, status, created_at, last_login
    FROM users WHERE id = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return dict(user)
    return None


def get_all_users() -> List[dict]:
    """
    جلب جميع المستخدمين
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, name, email, job_title, department, role, status, created_at, last_login
    FROM users
    ORDER BY created_at DESC
    """)
    
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return users


# ========================================
# ACCESS REQUESTS MANAGEMENT
# ========================================

def create_access_request(name: str, email: str, job_title: str, 
                          department: str, reason: str) -> dict:
    """
    إنشاء طلب وصول جديد
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO access_requests (name, email, job_title, department, reason)
        VALUES (?, ?, ?, ?, ?)
        """, (name, email, job_title, department, reason))
        
        request_id = cursor.lastrowid
        conn.commit()
        
        return {"ok": True, "request_id": request_id, "message": "Request submitted"}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def get_pending_requests() -> List[dict]:
    """
    جلب جميع الطلبات المعلقة
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM access_requests
    WHERE status = 'pending'
    ORDER BY submitted_at DESC
    """)
    
    requests = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return requests


def approve_request(request_id: int, admin_id: int, default_password: str = "demo123") -> dict:
    """
    الموافقة على طلب وصول
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # جلب بيانات الطلب
    cursor.execute("SELECT * FROM access_requests WHERE id = ?", (request_id,))
    request = cursor.fetchone()
    
    if not request:
        conn.close()
        return {"ok": False, "error": "Request not found"}
    
    if request["status"] != "pending":
        conn.close()
        return {"ok": False, "error": "Request already processed"}
    
    try:
        # إنشاء المستخدم
        result = create_user(
            name=request["name"],
            email=request["email"],
            password=default_password,
            job_title=request["job_title"],
            department=request["department"]
        )
        
        if not result["ok"]:
            conn.close()
            return result
        
        # تحديث حالة الطلب
        cursor.execute("""
        UPDATE access_requests
        SET status = 'approved', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
        WHERE id = ?
        """, (admin_id, request_id))
        
        conn.commit()
        
        log_activity(admin_id, "request_approved", "access_request", str(request_id),
                    f"Approved request for {request['email']}")
        
        return {"ok": True, "message": "Request approved, user created"}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def reject_request(request_id: int, admin_id: int) -> dict:
    """
    رفض طلب وصول
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE access_requests
    SET status = 'rejected', reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
    WHERE id = ? AND status = 'pending'
    """, (admin_id, request_id))
    
    if cursor.rowcount == 0:
        conn.close()
        return {"ok": False, "error": "Request not found or already processed"}
    
    conn.commit()
    
    log_activity(admin_id, "request_rejected", "access_request", str(request_id),
                f"Rejected access request")
    
    conn.close()
    
    return {"ok": True, "message": "Request rejected"}


# ========================================
# CASES MANAGEMENT
# ========================================

def create_case(case_id: str, case_number: str, investigator_id: int,
                device_info: str = None, device_model: str = None,
                device_os: str = None) -> dict:
    """
    إنشاء قضية جديدة
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO cases (case_id, case_number, investigator_id, device_info, 
                          device_model, device_os, acquisition_date)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (case_id, case_number, investigator_id, device_info, device_model, device_os))
        
        conn.commit()
        
        log_activity(investigator_id, "case_created", "case", case_id,
                    f"Created case {case_number}")
        
        return {"ok": True, "case_id": case_id}
        
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "Case ID already exists"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def get_case(case_id: str) -> Optional[dict]:
    """
    جلب بيانات قضية
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM cases WHERE case_id = ?", (case_id,))
    case = cursor.fetchone()
    
    conn.close()
    
    if case:
        return dict(case)
    return None


def get_user_cases(user_id: int) -> List[dict]:
    """
    جلب جميع قضايا المستخدم
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM cases
    WHERE investigator_id = ?
    ORDER BY created_at DESC
    """, (user_id,))
    
    cases = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return cases


# ========================================
# REPORTS MANAGEMENT
# ========================================

def create_report(case_id: str, user_id: int, report_title: str = None,
                 report_type: str = "forensic", total_messages: int = 0,
                 total_chats: int = 0, file_path: str = None) -> dict:
    """
    إنشاء تقرير جديد
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        INSERT INTO reports (case_id, report_title, report_type, total_messages,
                           total_chats, generated_by, file_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (case_id, report_title, report_type, total_messages, total_chats, user_id, file_path))
        
        report_id = cursor.lastrowid
        conn.commit()
        
        log_activity(user_id, "report_created", "report", str(report_id),
                    f"Created report for case {case_id}")
        
        return {"ok": True, "report_id": report_id}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def get_user_reports(user_id: int) -> List[dict]:
    """
    جلب جميع تقارير المستخدم
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT r.*, c.case_number, c.device_info
    FROM reports r
    JOIN cases c ON r.case_id = c.case_id
    WHERE r.generated_by = ?
    ORDER BY r.generated_at DESC
    """, (user_id,))
    
    reports = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return reports


# ========================================
# ACTIVITY LOGS
# ========================================

def log_activity(user_id: int, action: str, entity_type: str = None,
                entity_id: str = None, details: str = None,
                ip_address: str = None):
    """
    تسجيل نشاط المستخدم
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details, ip_address)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, action, entity_type, entity_id, details, ip_address))
    
    conn.commit()
    conn.close()


def get_user_activity(user_id: int, limit: int = 50) -> List[dict]:
    """
    جلب سجل نشاط المستخدم
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT * FROM activity_logs
    WHERE user_id = ?
    ORDER BY timestamp DESC
    LIMIT ?
    """, (user_id, limit))
    
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return logs


# ========================================
# INITIALIZATION
# ========================================

if __name__ == "__main__":
    print("🚀 Initializing Whisper-WA Database...")
    init_database()
    create_admin_user()
    print("✅ Done!")
