from flask import Flask, render_template, jsonify, request, send_from_directory
import os
from acquisition import pull_whatsapp_evidence


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

if __name__ == '__main__':
    app.run(debug=True)