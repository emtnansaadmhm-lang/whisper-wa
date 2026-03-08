# Backend/export.py
from flask import Blueprint, request, send_file, jsonify
import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

bp_export = Blueprint("bp_export", __name__)

# ================= CSV =================
@bp_export.route("/api/export/csv", methods=["POST"])
def export_csv():

    data = request.json.get("messages", [])

    if not data:
        return jsonify({"error": "No data provided"}), 400

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Message", "Type", "Number", "DateTime"])

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


# ================= PDF =================
@bp_export.route("/api/export/pdf", methods=["POST"])
def export_pdf():

    data = request.json.get("messages", [])

    if not data:
        return jsonify({"error": "No data provided"}), 400

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    y = 750
    pdf.setFont("Helvetica", 10)

    pdf.drawString(50, y, "Whisper-WA Forensic Report")
    y -= 40

    for msg in data:
        line = f"{msg.get('datetime')} | {msg.get('number')} | {msg.get('type')} | {msg.get('message')}"
        pdf.drawString(50, y, line)
        y -= 20

        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = 750

    pdf.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="forensic_report.pdf",
        mimetype="application/pdf"
    )
    
