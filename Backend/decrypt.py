
import os
import subprocess
import re
from datetime import datetime


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)
CRYPT_RE = re.compile(r"^msgstore\.db\.crypt(\d+)$", re.IGNORECASE)

def _pick_crypt_file(evidence_dir: str) -> str | None:
    best_ver = -1
    best_name = None

    for name in os.listdir(evidence_dir):
        m = CRYPT_RE.match(name)
        if m:
            ver = int(m.group(1))
            if ver > best_ver:
                best_ver = ver
                best_name = name

    return best_name

def decrypt_whatsapp_db(
    case_id: str,
    base_cases_dir: str = "Cases",
    wadecrypt_path: str = "wadecrypt",
    crypt_filename: str | None = None,
    key_filename: str = "key",
    out_filename: str = "msgstore_decrypted.db",
    timeout_sec: int = 180
) -> dict:
    """
    Step 3: Decryption (Backend)

    Inputs expected (from Acquisition team):
      Cases/<case_id>/Evidence/key
      Cases/<case_id>/Evidence/msgstore.db.crypt14

    Output:
      Cases/<case_id>/Decrypted/msgstore_decrypted.db
    """
    case_dir = os.path.join(base_cases_dir, case_id)
    evidence_dir = os.path.join(case_dir, "Evidence")
    decrypted_dir = os.path.join(case_dir, "Decrypted")

    key_path = os.path.join(evidence_dir, key_filename)
    crypt_path = os.path.join(evidence_dir, crypt_filename)
    out_db_path = os.path.join(decrypted_dir, out_filename)

    if not os.path.exists(key_path):
        return {"ok": False, "step": "decrypt", "error": f"Missing key file: {key_path}"}

    if not os.path.exists(crypt_path):
        return {"ok": False, "step": "decrypt", "error": f"Missing crypt DB: {crypt_path}"}

    _ensure_dir(decrypted_dir)

    cmd = [wadecrypt_path, key_path, crypt_path, out_db_path]

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False
        )

        if p.returncode != 0:
            return {
                "ok": False,
                "step": "decrypt",
                "error": "wadecrypt failed",
                "returncode": p.returncode,
                "stdout": (p.stdout or "").strip(),
                "stderr": (p.stderr or "").strip(),
            }

        if (not os.path.exists(out_db_path)) or os.path.getsize(out_db_path) == 0:
            return {
                "ok": False,
                "step": "decrypt",
                "error": "Decrypted DB not created or empty",
                "stdout": (p.stdout or "").strip(),
                "stderr": (p.stderr or "").strip(),
            }

        return {
            "ok": True,
            "step": "decrypt",
            "case_id": case_id,
            "decrypted_db": out_db_path,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip(),
        }

    except FileNotFoundError:
        return {
            "ok": False,
            "step": "decrypt",
            "error": f"wadecrypt not found. Put it in PATH or pass wadecrypt_path.",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "step": "decrypt", "error": f"Timeout after {timeout_sec}s"}


