# Backend/connected.py
import os
import subprocess
from datetime import datetime
from flask import Blueprint, request, jsonify

# شغل البنات (لا نعدله)
from acquisition import pull_whatsapp_evidence
from decrypt import decrypt_whatsapp_db

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
    # الأفضل يكون adb موجود بـ PATH
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
    """
    Root check:
      1) adb shell su -c id  -> uid=0؟
      2) fallback adb shell id -> uid=0؟
    """
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


@bp_connected.route("/api/device/devices", methods=["GET"])
def api_devices():
    adb_path = request.args.get("adb_path")
    return jsonify(adb_devices(adb_path=adb_path))


@bp_connected.route("/api/device/connect", methods=["POST"])
def api_connect():
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
    now = datetime.now().isoformat(timespec="seconds")

    # 1) devices قبل
    logs.append({"ts": now, "level": "INFO", "msg": "Checking ADB devices..."})
    dev = adb_devices(adb_path=adb_path)
    if not dev["ok"]:
        return jsonify({"ok": False, "step": "devices", "logs": logs, "detail": dev}), 400

    # 2) wifi connect إذا مطلوب
    if method == "wifi":
        if not ip_port:
            return jsonify({"ok": False, "step": "validate", "logs": logs, "error": "ip_port is required for wifi"}), 400

        logs.append({"ts": now, "level": "INFO", "msg": f"ADB connect to {ip_port}..."})
        conn = adb_connect_wifi(ip_port, adb_path=adb_path)
        if not conn["ok"]:
            return jsonify({"ok": False, "step": "adb_connect", "logs": logs, "detail": conn}), 400

        # refresh devices
        dev = adb_devices(adb_path=adb_path)
        if not dev["ok"] or not dev["devices"]:
            return jsonify({"ok": False, "step": "devices_after_connect", "logs": logs, "detail": dev}), 400

    elif method == "usb":
        # لازم جهاز USB يكون ظاهر مسبقاً
        if not dev["devices"]:
            return jsonify({"ok": False, "step": "usb", "logs": logs, "error": "No USB device found. Enable USB Debugging."}), 400

    else:
        return jsonify({"ok": False, "step": "validate", "logs": logs, "error": "method must be wifi or usb"}), 400

    serial = dev["devices"][0] if dev["devices"] else None
    logs.append({"ts": now, "level": "SUCCESS", "msg": f"Device detected: {serial}"})

    # 3) Root check
    logs.append({"ts": now, "level": "INFO", "msg": "Checking root access..."})
    root = adb_root_check(serial=serial, adb_path=adb_path)
    if not root.get("ok"):
        return jsonify({"ok": False, "step": "root_check", "logs": logs, "detail": root}), 400

    if not root.get("rooted"):
        logs.append({"ts": now, "level": "ERROR", "msg": "Device is NOT rooted. Root required to continue."})
        return jsonify({"ok": False, "step": "root_check", "logs": logs, "rooted": False}), 403

    logs.append({"ts": now, "level": "SUCCESS", "msg": "Root access OK."})

    return jsonify({
        "ok": True,
        "step": "connected",
        "case_id": case_id,
        "serial": serial,
        "rooted": True,
        "logs": logs
    }), 200


@bp_connected.route("/api/workflow/run", methods=["POST"])
def api_run_workflow():
    """
    يشغل شغل البنات: acquisition + decrypt
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
    now = datetime.now().isoformat(timespec="seconds")

    logs.append({"ts": now, "level": "INFO", "msg": f"Running acquisition for {case_id}..."})
    acq = pull_whatsapp_evidence(case_id)
    if not (isinstance(acq, dict) and acq.get("ok") is True):
        logs.append({"ts": now, "level": "ERROR", "msg": "Acquisition failed."})
        return jsonify({"ok": False, "step": "acquisition", "logs": logs, "detail": acq}), 400

    logs.append({"ts": now, "level": "SUCCESS", "msg": "Acquisition completed."})

    logs.append({"ts": now, "level": "INFO", "msg": "Decrypting WhatsApp database..."})
    dec = decrypt_whatsapp_db(case_id=case_id, wadecrypt_path=wadecrypt_path, timeout_sec=timeout_sec)
    if not (isinstance(dec, dict) and dec.get("ok") is True):
        logs.append({"ts": now, "level": "ERROR", "msg": "Decryption failed."})
        return jsonify({"ok": False, "step": "decrypt", "logs": logs, "detail": dec}), 400

    logs.append({"ts": now, "level": "SUCCESS", "msg": "Decryption completed."})

    return jsonify({
        "ok": True,
        "step": "done",
        "case_id": case_id,
        "logs": logs,
        "acquisition": acq,
        "decrypt": dec
    }), 200
