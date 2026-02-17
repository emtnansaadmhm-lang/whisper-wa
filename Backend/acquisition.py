import os
import subprocess
import hashlib
from datetime import datetime

# دالة حساب الهاش SHA-256 لتوثيق سلامة الدليل
def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# دالة سحب الأدلة (الخطوة رقم 2 في اللستة)
def pull_whatsapp_evidence(case_id="Case_001"):
    # إنشاء مسارات الحفظ
    save_path = f"Cases/{case_id}/Evidence"
    os.makedirs(save_path, exist_ok=True)
    
    # مسارات الملفات في الأندرويد (تحتاج روت)
    android_db = "/sdcard/WhatsApp/Databases/msgstore.db.crypt14"
    android_key = "/data/data/com.whatsapp/files/key"
    
    results = []

    # مصفوفة للملفات اللي نبي نسحبها
    files_to_pull = [
        {"name": "msgstore.db", "path": android_db},
        {"name": "key", "path": android_key}
    ]

    for file in files_to_pull:
        local_file_path = os.path.join(save_path, file["name"])
        
        try:
            # 1. نسخ الملف لمكان مؤقت في الجوال ثم سحبه
            subprocess.run(
                ['adb', 'shell', 'su', '-c', f'cp {file["path"]} /sdcard/{file["name"]}'],
                check=True
            )
            subprocess.run(
                ['adb', 'pull', f'/sdcard/{file["name"]}', local_file_path],
                check=True
            )
            
            # مسح الملف المؤقت من الجوال
            subprocess.run(
                ['adb', 'shell', 'rm', f'/sdcard/{file["name"]}'],
                check=True
            )

            # 2. حساب الهاش وتوثيق معلومات الملف
            file_hash = calculate_sha256(local_file_path)
            file_size = os.path.getsize(local_file_path)
            
            results.append({
                "file": file["name"],
                "status": "Success",
                "hash": file_hash,
                "size": f"{file_size / 1024:.2f} KB",
                "path": local_file_path
            })
            
        except Exception as e:
            results.append({
                "file": file["name"],
                "status": "Failed",
                "error": str(e)
            })
            
    return results
