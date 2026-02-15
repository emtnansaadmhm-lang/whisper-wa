from flask import Flask, render_template, jsonify, request, send_from_directory
import os
from acquisition import pull_whatsapp_evidence
from decrypt import decrypt_whatsapp_db


app = Flask(__name__, template_folder='.', static_folder='.')

@app.route('/')
def index():
    
    return render_template('chat.html')


@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

@app.route('/run_acquisition', methods=['POST'])
def run_acquisition():
    results = pull_whatsapp_evidence("Case_001")
    return jsonify(results)

@app.route("/api/cases/<case_id>/decrypt", methods=["POST"])
def api_decrypt(case_id):
    body = request.get_json(silent=True) or {}
    wadecrypt_path = body.get("wadecrypt_path", "wadecrypt")
    timeout_sec = int(body.get("timeout_sec", 180))

    result = decrypt_whatsapp_db(
        case_id=case_id,
        wadecrypt_path=wadecrypt_path,
        timeout_sec=timeout_sec
    )
    return jsonify(result), (200 if result.get("ok") else 400)


if __name__ == '__main__':

    app.run(debug=True)
