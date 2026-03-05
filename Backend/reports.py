# Backend/reports.py
import json
import os
from datetime import datetime
from flask import Blueprint, request, jsonify

bp_reports = Blueprint("bp_reports", __name__)
REPORTS_FILE = "reports_db.json"

def load_reports():
    if not os.path.exists(REPORTS_FILE):
        return []
    with open(REPORTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_reports(data):
    with open(REPORTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# GET — جيب التقارير
@bp_reports.route("/api/reports", methods=["GET"])
def get_reports():
    reports = load_reports()
    investigator = request.args.get("investigator")
    role = request.args.get("role", "user")
    if role != "admin" and investigator:
        reports = [r for r in reports if r.get("investigator") == investigator]
    return jsonify({"ok": True, "reports": reports})

# POST — احفظ تقرير جديد
@bp_reports.route("/api/reports", methods=["POST"])
def create_report():
    body = request.get_json(silent=True) or {}
    report = {
        "id": int(datetime.now().timestamp() * 1000),
        "investigator": body.get("investigator", "Unknown"),
        "date": body.get("date") or datetime.now().strftime("%Y-%m-%d"),
        "time": body.get("time") or datetime.now().strftime("%H:%M"),
        "caseNumber": body.get("caseNumber", "---"),
        "deviceInfo": body.get("deviceInfo", "---"),
        "status": body.get("status", "completed"),
    }
    reports = load_reports()
    reports.append(report)
    save_reports(reports)
    return jsonify({"ok": True, "report": report}), 201

# DELETE — احذف تقرير
@bp_reports.route("/api/reports/<int:report_id>", methods=["DELETE"])
def delete_report(report_id):
    reports = load_reports()
    updated = [r for r in reports if r.get("id") != report_id]
    if len(updated) == len(reports):
        return jsonify({"ok": False, "error": "Not found"}), 404
    save_reports(updated)
    return jsonify({"ok": True})

# PATCH — عدّل الحالة
@bp_reports.route("/api/reports/<int:report_id>/status", methods=["PATCH"])
def update_status(report_id):
    body = request.get_json(silent=True) or {}
    new_status = body.get("status")
    if new_status not in ("completed", "pending", "archived"):
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    reports = load_reports()
    for r in reports:
        if r.get("id") == report_id:
            r["status"] = new_status
            save_reports(reports)
            return jsonify({"ok": True, "report": r})
    return jsonify({"ok": False, "error": "Not found"}), 404
