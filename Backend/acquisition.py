import os
import subprocess
import hashlib


def calculate_sha256(file_path: str) -> str:
    """
    حساب SHA-256 للملف
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


def _run(cmd):
    """
    تشغيل أمر system وإرجاع stdout/stderr
    """
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip(), result.stderr.strip()


def pull_whatsapp_evidence(case_id: str = "Case_001") -> dict:
    """
    سحب أدلة واتساب من الجهاز:
    - msgstore.db.crypt14
    - key

    يتطلب:
    - adb
    - root
    """

    save_path = os.path.join("Cases", case_id, "Evidence")
    os.makedirs(save_path, exist_ok=True)

    # الملفات المطلوبة من الجهاز
    android_db = "/sdcard/WhatsApp/Databases/msgstore.db.crypt14"
    android_key = "/data/data/com.whatsapp/files/key"

    files_to_pull = [
        {"name": "msgstore.db.crypt14", "path": android_db},
        {"name": "key", "path": android_key}
    ]

    results = []
    success_count = 0

    for file_info in files_to_pull:
        file_name = file_info["name"]
        source_path = file_info["path"]
        temp_sdcard_path = f"/sdcard/{file_name}"
        local_file_path = os.path.join(save_path, file_name)

        try:
            # 1) نسخ الملف من المسار الأصلي إلى sdcard باستخدام root
            stdout1, stderr1 = _run([
                "adb", "shell", "su", "-c",
                f"cp {source_path} {temp_sdcard_path}"
            ])

            # 2) سحب الملف من sdcard إلى الجهاز المحلي
            stdout2, stderr2 = _run([
                "adb", "pull", temp_sdcard_path, local_file_path
            ])

            # 3) حذف النسخة المؤقتة من sdcard
            stdout3, stderr3 = _run([
                "adb", "shell", "rm", temp_sdcard_path
            ])

            # 4) التحقق من وجود الملف محليًا
            if not os.path.exists(local_file_path):
                raise FileNotFoundError(f"Local file not found after pull: {local_file_path}")

            file_hash = calculate_sha256(local_file_path)
            file_size = os.path.getsize(local_file_path)

            results.append({
                "file": file_name,
                "status": "Success",
                "hash": file_hash,
                "size_bytes": file_size,
                "size_kb": round(file_size / 1024, 2),
                "path": local_file_path,
                "source_path": source_path
            })

            success_count += 1

        except subprocess.CalledProcessError as e:
            results.append({
                "file": file_name,
                "status": "Failed",
                "source_path": source_path,
                "error": "ADB command failed",
                "returncode": e.returncode,
                "stdout": (e.stdout or "").strip(),
                "stderr": (e.stderr or "").strip()
            })

        except Exception as e:
            results.append({
                "file": file_name,
                "status": "Failed",
                "source_path": source_path,
                "error": str(e)
            })

    return {
        "ok": success_count == len(files_to_pull),
        "case_id": case_id,
        "save_path": save_path,
        "total_files": len(files_to_pull),
        "success_count": success_count,
        "failed_count": len(files_to_pull) - success_count,
        "results": results
    }
