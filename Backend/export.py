# Backend/export.py
from flask import Blueprint, request, send_file, jsonify
import csv
import io

bp_export = Blueprint("bp_export", __name__)

@bp_export.route("/api/export/csv", methods=["POST"])
def export_csv():

    data = request.json.get("messages", [])

    if not data:
        return jsonify({"error": "No data provided"}), 400

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(["Message", "Type", "Number", "DateTime"])

    # Rows
    for msg in data:
        writer.writerow([
            msg.get("message"),
            msg.get("type"),
            msg.get("number"),
            msg.get("datetime")
        ])

    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name="forensic_report.csv"
    )
