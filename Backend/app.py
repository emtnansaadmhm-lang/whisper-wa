# Backend/connected.py
import subprocess
from datetime import datetime
from flask import Blueprint, request, jsonify

# ✅ نستدعي شغل البنات مثل ما هو
from acquisition import pull_whatsapp_evidence

# إذا عندكم decrypt.py موجود (بنفس مشروعك)
try:
    from decrypt import decrypt_whatsapp_db
except Exception:
    decrypt_whatsapp_db = None

bp_connected = Blueprint("bp_connected", __name__)

DEFAULT_CASE_ID = "Case_001"


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


@bp_connected.route("/api/device/connect", methods=["POST"])
def api_device_connect():
    """
    POST body:
    {
      "method": "wifi" | "usb",
      "ip_port": "192.168.56.101:5555",   # required if wifi
      "adb_path": "adb",                  # optional
      "case_id": "Case_001"               # optional
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


@bp_connected.route("/api/workflow/run", methods=["POST"])
def api_workflow_run():
    """
    يشغل: acquisition (+ decrypt إذا موجود)
    POST body:
    {
      "case_id": "Case_001",
      "wadecrypt_path": "wadecrypt",
      "timeout_sec": 180
    }
    """
    body = request.get_json(silent=True) or {}
    case_id = body.get("case_id") or DEFAULT_CASE_ID
    wadecrypt_path = body.get("wadecrypt_path", "wadecrypt")
    timeout_sec = int(body.get("timeout_sec", 180))

    logs = []
    ts = datetime.now().isoformat(timespec="seconds")

    logs.append({"ts": ts, "level": "INFO", "msg": f"Running acquisition for {case_id}..."})
    acq = pull_whatsapp_evidence(case_id)

    # لو شغل البنات يرجع list عادي أو dict — نخليه يمشي
    logs.append({"ts": ts, "level": "SUCCESS", "msg": "Acquisition finished."})

    result = {"ok": True, "step": "acquisition_done", "case_id": case_id, "logs": logs, "acquisition": acq}

    # decrypt optional
    if decrypt_whatsapp_db is not None:
        logs.append({"ts": ts, "level": "INFO", "msg": "Decrypting WhatsApp database..."})
        dec = decrypt_whatsapp_db(case_id=case_id, wadecrypt_path=wadecrypt_path, timeout_sec=timeout_sec)
        if isinstance(dec, dict) and dec.get("ok") is False:
            logs.append({"ts": ts, "level": "ERROR", "msg": "Decryption failed."})
            return jsonify({"ok": False, "step": "decrypt", "logs": logs, "detail": dec}), 400

        logs.append({"ts": ts, "level": "SUCCESS", "msg": "Decryption finished."})
        result["step"] = "done"
        result["decrypt"] = dec

    return jsonify(result), 200
