import os
import subprocess
from datetime import datetime

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def decrypt_case_db(
    case_id: str,
    base_cases_dir: str = "Cases",
    wadecrypt_path: str = "wadecrypt",
    timeout_sec: int = 180
) -> dict:
    """
    Inputs:
      Cases/<case_id>/Evidence/key
      Cases/<case_id>/Evidence/msgstore.db.crypt14

    Output:
      Cases/<case_id>/Decrypted/msgstore_decrypted.db
    """
    base_dir = os.path.join(base_cases_dir, case_id)
    evidence_dir = os.path.join(base_dir, "Evidence")
    decrypted_dir = os.path.join(base_dir, "Decrypted")

    key_path = os.path.join(evidence_dir, "key")
    crypt_path = os.path.join(evidence_dir, "msgstore.db.crypt14")
    out_db_path = os.path.join(decrypted_dir, "msgstore_decrypted.db")

    if not os.path.exists(key_path):
        return {"ok": False, "step": "decrypt", "error": f"Missing key: {key_path}"}

    if not os.path.exists(crypt_path):
        return {"ok": False, "step": "decrypt", "error": f"Missing crypt db: {crypt_path}"}

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
                "stderr": (p.stderr or "").strip()
            }

        if (not os.path.exists(out_db_path)) or os.path.getsize(out_db_path) == 0:
            return {
                "ok": False,
                "step": "decrypt",
                "error": "Decrypted DB not created or empty",
                "stdout": (p.stdout or "").strip(),
                "stderr": (p.stderr or "").strip()
            }

        return {
            "ok": True,
            "step": "decrypt",
            "case_id": case_id,
            "decrypted_db": out_db_path,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "stdout": (p.stdout or "").strip(),
            "stderr": (p.stderr or "").strip()
        }

    except FileNotFoundError:
        return {"ok": False, "step": "decrypt", "error": f"wadecrypt not found: {wadecrypt_path}"}

    except subprocess.TimeoutExpired:
        return {"ok": False, "step": "decrypt", "error": f"Timeout after {timeout_sec}s"}

