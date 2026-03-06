"""
app.py - Main Flask Application
Backend API للنظام الكامل
"""

from flask import Flask, request, jsonify, Blueprint
from flask_cors import CORS
from datetime import datetime
import subprocess

# استيراد الوحدات
from acquisition import pull_whatsapp_evidence
from parser import parse_whatsapp_db, group_messages_by_chat, get_chat_summary
from analysis import analyze_whatsapp_data, save_analysis_report
from index import build_index, search_word
import database as db

try:
    from decrypt import decrypt_whatsapp_db
except Exception:
    decrypt_whatsapp_db = None

# إنشاء التطبيق
app = Flask(__name__)
CORS(app)

# Blueprints (إذا موجودة)
try:
    from reports import bp_reports
    app.register_blueprint(bp_reports)
except:
    pass

try:
    from export import bp_export
    app.register_blueprint(bp_export)
except:
    pass

# متغيرات عامة
DEFAULT_CASE_ID = "Case_001"
MESSAGES = {}
INDEX = {}

# ========================================
# HELPER FUNCTIONS
# ========================================

def _run(cmd, timeout=30):
    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False
    )
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def _adb(adb_path=None):
    return adb_path or "adb"


def adb_devices(adb_path=None):
    adb = _adb(adb_path)
    code, out, err = _run([adb, "devices"], timeout=20)
    if code != 0:
        return {"ok": False, "error": "adb devices failed", "stdout": out, "stderr": err, "devices": []}

    devices = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])

    return {"ok": True, "devices": devices, "stdout": out, "stderr": err}


def adb_connect_wifi(ip_port, adb_path=None):
    adb = _adb(adb_path)
    code, out, err = _run([adb, "connect", ip_port], timeout=25)
    text = (out + " " + err).lower()
    ok = (code == 0) and ("connected" in text or "already connected" in text)
    return {"ok": ok, "returncode": code, "stdout": out, "stderr": err}


def adb_root_check(serial=None, adb_path=None):
    adb = _adb(adb_path)
    base = [adb]
    if serial:
        base += ["-s", serial]

    # Try su
    code, out, err = _run(base + ["shell", "su", "-c", "id"], timeout=20)
    if code == 0 and "uid=0" in out:
        return {"ok": True, "rooted": True, "method": "su", "stdout": out, "stderr": err}

    # Fallback id
    code2, out2, err2 = _run(base + ["shell", "id"], timeout=20)
    if code2 == 0 and "uid=0" in out2:
        return {"ok": True, "rooted": True, "method": "id", "stdout": out2, "stderr": err2}

    return {"ok": True, "rooted": False, "method": "su/id", "stdout": out or out2, "stderr": err or err2}


# ========================================
# HEALTH CHECK
# ========================================

@app.route("/", methods=["GET"])
def health_check():
    """
    فحص صحة الخادم
    """
    return jsonify({
        "status": "ok",
        "service": "Whisper-WA Backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    })


# ========================================
# AUTHENTICATION
# ========================================

@app.route("/api/auth/login", methods=["POST"])
def login():
    """
    تسجيل دخول المستخدم
    POST body: { "email": "user@example.com", "password": "password123" }
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    
    if not email or not password:
        return jsonify({"ok": False, "error": "Email and password required"}), 400
    
    result = db.authenticate_user(email, password)
    
    if result["ok"]:
        return jsonify(result), 200
    else:
        return jsonify(result), 401


# ========================================
# USER & ACCESS REQUESTS MANAGEMENT
# ========================================

@app.route("/api/users", methods=["GET"])
def get_users():
    """
    جلب جميع المستخدمين
    """
    users = db.get_all_users()
    return jsonify({"ok": True, "users": users}), 200


@app.route("/api/access-requests", methods=["POST"])
def create_access_request():
    """
    إنشاء طلب وصول جديد
    POST body: { "name": "", "email": "", "job_title": "", "department": "", "reason": "" }
    """
    data = request.get_json() or {}
    
    result = db.create_access_request(
        name=data.get("name"),
        email=data.get("email"),
        job_title=data.get("job_title"),
        department=data.get("department", ""),
        reason=data.get("reason")
    )
    
    if result["ok"]:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@app.route("/api/access-requests/pending", methods=["GET"])
def get_pending_requests():
    """
    جلب الطلبات المعلقة
    """
    requests = db.get_pending_requests()
    return jsonify({"ok": True, "requests": requests}), 200


@app.route("/api/access-requests/<int:request_id>/approve", methods=["POST"])
def approve_access_request(request_id):
    """
    الموافقة على طلب
    """
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)  # يفترض يجي من الـ session
    
    result = db.approve_request(request_id, admin_id)
    
    if result["ok"]:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


@app.route("/api/access-requests/<int:request_id>/reject", methods=["POST"])
def reject_access_request(request_id):
    """
    رفض طلب
    """
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)
    
    result = db.reject_request(request_id, admin_id)
    
    if result["ok"]:
        return jsonify(result), 200
    else:
        return jsonify(result), 400


# ========================================
# DEVICE CONNECTION & WORKFLOW
# ========================================

@app.route("/api/device/connect", methods=["POST"])
def api_device_connect():
    """
    POST body:
    {
      "method": "wifi" | "usb",
      "ip_port": "192.168.56.101:5555",
      "adb_path": "adb",
      "case_id": "Case_001"
    }
    """
    body = request.get_json(silent=True) or {}
    method = (body.get("method") or "").lower()
    ip_port = (body.get("ip_port") or "").strip()
    adb_path = body.get("adb_path") or None
    case_id = body.get("case_id") or DEFAULT_CASE_ID

    logs = []
    ts = datetime.now().isoformat(timespec="seconds")

    logs.append({"ts": ts, "level": "INFO", "msg": "Checking ADB devices..."})
    dev = adb_devices(adb_path=adb_path)
    if not dev["ok"]:
        return jsonify({"ok": False, "step": "devices", "logs": logs, "detail": dev}), 400

    if method == "wifi":
        if not ip_port:
            return jsonify({"ok": False, "step": "validate", "logs": logs, "error": "ip_port is required"}), 400

        logs.append({"ts": ts, "level": "INFO", "msg": f"ADB connect to {ip_port}..."})
        conn = adb_connect_wifi(ip_port, adb_path=adb_path)
        if not conn["ok"]:
            logs.append({"ts": ts, "level": "ERROR", "msg": "ADB connect failed."})
            return jsonify({"ok": False, "step": "adb_connect", "logs": logs, "detail": conn}), 400

        dev = adb_devices(adb_path=adb_path)
        if not dev["ok"] or not dev["devices"]:
            return jsonify({"ok": False, "step": "devices_after_connect", "logs": logs, "detail": dev}), 400

    elif method == "usb":
        if not dev["devices"]:
            return jsonify({
                "ok": False,
                "step": "usb",
                "logs": logs,
                "error": "No USB device found. Enable USB Debugging."
            }), 400

    else:
        return jsonify({"ok": False, "step": "validate", "logs": logs, "error": "method must be wifi or usb"}), 400

    serial = dev["devices"][0]
    logs.append({"ts": ts, "level": "SUCCESS", "msg": f"Device detected: {serial}"})

    logs.append({"ts": ts, "level": "INFO", "msg": "Checking root access..."})
    root = adb_root_check(serial=serial, adb_path=adb_path)
    if not root.get("ok"):
        return jsonify({"ok": False, "step": "root_check", "logs": logs, "detail": root}), 400

    if not root.get("rooted"):
        logs.append({"ts": ts, "level": "ERROR", "msg": "Device is NOT rooted. Root required to continue."})
        return jsonify({"ok": False, "step": "root_check", "logs": logs, "rooted": False}), 403

    logs.append({"ts": ts, "level": "SUCCESS", "msg": "Root access OK."})

    return jsonify({
        "ok": True,
        "step": "connected",
        "case_id": case_id,
        "serial": serial,
        "rooted": True,
        "logs": logs
    }), 200


@app.route("/api/workflow/run", methods=["POST"])
def api_workflow_run():
    """
    يشغل: acquisition → decrypt → parse → analyze
    POST body:
    {
      "case_id": "Case_001",
      "wadecrypt_path": "wadecrypt",
      "timeout_sec": 180,
      "user_id": 1
    }
    """
    body = request.get_json(silent=True) or {}
    case_id = body.get("case_id") or DEFAULT_CASE_ID
    wadecrypt_path = body.get("wadecrypt_path", "wadecrypt")
    timeout_sec = int(body.get("timeout_sec", 180))
    user_id = body.get("user_id", 1)

    logs = []
    ts = datetime.now().isoformat(timespec="seconds")

    # 1. Acquisition
    logs.append({"ts": ts, "level": "INFO", "msg": f"Running acquisition for {case_id}..."})
    acq = pull_whatsapp_evidence(case_id)
    logs.append({"ts": ts, "level": "SUCCESS", "msg": "Acquisition finished."})

    result = {"ok": True, "step": "acquisition_done", "case_id": case_id, "logs": logs, "acquisition": acq}

    # 2. Decrypt
    if decrypt_whatsapp_db is not None:
        logs.append({"ts": ts, "level": "INFO", "msg": "Decrypting WhatsApp database..."})
        dec = decrypt_whatsapp_db(case_id=case_id, wadecrypt_path=wadecrypt_path, timeout_sec=timeout_sec)
        
        if isinstance(dec, dict) and dec.get("ok") is False:
            logs.append({"ts": ts, "level": "ERROR", "msg": "Decryption failed."})
            return jsonify({"ok": False, "step": "decrypt", "logs": logs, "detail": dec}), 400

        logs.append({"ts": ts, "level": "SUCCESS", "msg": "Decryption finished."})
        result["decrypt"] = dec

    # 3. Parse
    logs.append({"ts": ts, "level": "INFO", "msg": "Parsing WhatsApp database..."})
    parsed = parse_whatsapp_db(case_id)
    
    if not parsed.get("ok"):
        logs.append({"ts": ts, "level": "ERROR", "msg": "Parsing failed."})
        return jsonify({"ok": False, "step": "parse", "logs": logs, "detail": parsed}), 400
    
    logs.append({"ts": ts, "level": "SUCCESS", "msg": f"Parsed {parsed['total_messages']} messages."})
    result["parsed"] = {
        "total_messages": parsed["total_messages"],
        "extracted_at": parsed["extracted_at"]
    }

    # 4. Analysis
    logs.append({"ts": ts, "level": "INFO", "msg": "Running analysis..."})
    analysis = analyze_whatsapp_data(parsed["messages"], case_id)
    
    if not analysis.get("ok"):
        logs.append({"ts": ts, "level": "ERROR", "msg": "Analysis failed."})
        return jsonify({"ok": False, "step": "analysis", "logs": logs}), 400
    
    # حفظ تقرير التحليل
    report_path = save_analysis_report(analysis, case_id)
    logs.append({"ts": ts, "level": "SUCCESS", "msg": f"Analysis saved to {report_path}"})
    
    result["analysis_report"] = report_path
    result["step"] = "completed"

    # 5. Build Index
    logs.append({"ts": ts, "level": "INFO", "msg": "Building search index..."})
    messages_dict = {msg["id"]: msg["text"] for msg in parsed["messages"]}
    index_data = build_index(messages_dict)
    logs.append({"ts": ts, "level": "SUCCESS", "msg": f"Indexed {len(index_data['word_index'])} words."})

    return jsonify(result), 200


# ========================================
# MESSAGES & CHATS
# ========================================

@app.route("/api/messages/<case_id>", methods=["GET"])
def get_messages(case_id):
    """
    جلب جميع الرسائل لقضية معينة
    """
    parsed = parse_whatsapp_db(case_id)
    
    if not parsed.get("ok"):
        return jsonify({"ok": False, "error": "Failed to parse database"}), 400
    
    return jsonify({
        "ok": True,
        "case_id": case_id,
        "total_messages": parsed["total_messages"],
        "messages": parsed["messages"]
    }), 200


@app.route("/api/chats/<case_id>", methods=["GET"])
def get_chats(case_id):
    """
    جلب المحادثات مجمّعة حسب الرقم
    """
    parsed = parse_whatsapp_db(case_id)
    
    if not parsed.get("ok"):
        return jsonify({"ok": False, "error": "Failed to parse database"}), 400
    
    chats = group_messages_by_chat(parsed["messages"])
    
    # إضافة ملخص لكل محادثة
    chats_summary = {}
    for jid, messages in chats.items():
        summary = get_chat_summary(messages)
        chats_summary[jid] = {
            "summary": summary,
            "messages": messages
        }
    
    return jsonify({
        "ok": True,
        "case_id": case_id,
        "total_chats": len(chats_summary),
        "chats": chats_summary
    }), 200


# ========================================
# ANALYSIS
# ========================================

@app.route("/api/analysis/<case_id>", methods=["GET"])
def get_analysis(case_id):
    """
    جلب نتائج التحليل
    """
    import json
    import os
    
    report_path = os.path.join("Cases", case_id, "Analysis", "analysis_report.json")
    
    if not os.path.exists(report_path):
        return jsonify({"ok": False, "error": "Analysis report not found"}), 404
    
    with open(report_path, 'r', encoding='utf-8') as f:
        analysis = json.load(f)
    
    return jsonify(analysis), 200


@app.route("/api/analysis/run/<case_id>", methods=["POST"])
def run_analysis(case_id):
    """
    تشغيل التحليل لقضية معينة
    """
    parsed = parse_whatsapp_db(case_id)
    
    if not parsed.get("ok"):
        return jsonify({"ok": False, "error": "Failed to parse database"}), 400
    
    analysis = analyze_whatsapp_data(parsed["messages"], case_id)
    
    if not analysis.get("ok"):
        return jsonify({"ok": False, "error": "Analysis failed"}), 400
    
    report_path = save_analysis_report(analysis, case_id)
    
    return jsonify({
        "ok": True,
        "case_id": case_id,
        "report_path": report_path,
        "summary": analysis["summary"]
    }), 200


# ========================================
# SEARCH & INDEX
# ========================================

@app.route("/api/index/build", methods=["POST"])
def build_index_api():
    """
    بناء الفهرس للبحث
    POST body: { "messages": {"1": "text1", "2": "text2"} }
    """
    global MESSAGES, INDEX
    
    data = request.json or {}
    MESSAGES = {int(k): v for k, v in data.get("messages", {}).items()}
    INDEX = build_index(MESSAGES)

    return jsonify({
        "status": "success",
        "total_words": len(INDEX["word_index"]),
        "total_links": len(INDEX["links"]),
        "total_images": len(INDEX["images"]),
        "most_common_word": INDEX.get("most_common", [])
    }), 200


@app.route("/api/search", methods=["GET"])
def search():
    """
    البحث في الفهرس
    GET /api/search?q=keyword
    """
    q = request.args.get("q", "").strip()
    
    if not q:
        return jsonify({"ok": False, "error": "Query parameter 'q' required"}), 400
    
    ids = search_word(INDEX, q)
    results = {i: MESSAGES.get(i, "") for i in ids}
    
    return jsonify({
        "ok": True,
        "query": q,
        "total_results": len(results),
        "results": results
    }), 200


@app.route("/api/links", methods=["GET"])
def get_links():
    """
    جلب جميع الروابط
    """
    return jsonify({
        "ok": True,
        "total_links": len(INDEX.get("links", [])),
        "links": INDEX.get("links", [])
    }), 200


@app.route("/api/images", methods=["GET"])
def get_images():
    """
    جلب جميع الصور
    """
    return jsonify({
        "ok": True,
        "total_images": len(INDEX.get("images", [])),
        "images": INDEX.get("images", [])
    }), 200


# ========================================
# CASES MANAGEMENT
# ========================================

@app.route("/api/cases", methods=["POST"])
def create_case():
    """
    إنشاء قضية جديدة
    """
    data = request.get_json() or {}
    
    result = db.create_case(
        case_id=data.get("case_id"),
        case_number=data.get("case_number"),
        investigator_id=data.get("investigator_id", 1),
        device_info=data.get("device_info"),
        device_model=data.get("device_model"),
        device_os=data.get("device_os")
    )
    
    if result["ok"]:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@app.route("/api/cases/<int:user_id>", methods=["GET"])
def get_user_cases(user_id):
    """
    جلب قضايا المستخدم
    """
    cases = db.get_user_cases(user_id)
    return jsonify({"ok": True, "cases": cases}), 200


# ========================================
# REPORTS MANAGEMENT
# ========================================

@app.route("/api/reports", methods=["POST"])
def create_report():
    """
    إنشاء تقرير جديد
    """
    data = request.get_json() or {}
    
    result = db.create_report(
        case_id=data.get("case_id"),
        user_id=data.get("user_id", 1),
        report_title=data.get("report_title"),
        report_type=data.get("report_type", "forensic"),
        total_messages=data.get("total_messages", 0),
        total_chats=data.get("total_chats", 0),
        file_path=data.get("file_path")
    )
    
    if result["ok"]:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@app.route("/api/reports/<int:user_id>", methods=["GET"])
def get_user_reports(user_id):
    """
    جلب تقارير المستخدم
    """
    reports = db.get_user_reports(user_id)
    return jsonify({"ok": True, "reports": reports}), 200


# ========================================
# DATABASE INITIALIZATION
# ========================================

@app.route("/api/init-db", methods=["POST"])
def init_database():
    """
    تهيئة قاعدة البيانات
    """
    try:
        db.init_database()
        db.create_admin_user()
        return jsonify({"ok": True, "message": "Database initialized successfully"}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ========================================
# RUN APPLICATION
# ========================================

if __name__ == "__main__":
    print("🚀 Starting Whisper-WA Backend...")
    print("📊 Initializing database...")
    
    try:
        db.init_database()
        db.create_admin_user()
        print("✅ Database ready!")
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")
    
    print("🌐 Starting Flask server...")
    app.run(debug=True, host="0.0.0.0", port=5000)
