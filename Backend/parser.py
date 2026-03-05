"""
parser.py - WhatsApp Database Parser
استخراج الرسائل من قاعدة بيانات واتساب المفككة
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional


def parse_whatsapp_db(
    case_id: str,
    base_cases_dir: str = "Cases",
    db_filename: str = "msgstore_decrypted.db"
) -> dict:
    """
    استخراج الرسائل من قاعدة بيانات واتساب المفككة
    
    Args:
        case_id: رقم القضية
        base_cases_dir: مجلد القضايا الرئيسي
        db_filename: اسم ملف قاعدة البيانات المفككة
    
    Returns:
        dict مع:
        - ok: bool
        - messages: List[dict] (إذا نجح)
        - error: str (إذا فشل)
    """
    
    case_dir = os.path.join(base_cases_dir, case_id)
    decrypted_dir = os.path.join(case_dir, "Decrypted")
    db_path = os.path.join(decrypted_dir, db_filename)
    
    # التحقق من وجود الملف
    if not os.path.exists(db_path):
        return {
            "ok": False,
            "error": f"Database file not found: {db_path}"
        }
    
    try:
        # الاتصال بقاعدة البيانات
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # استخراج الرسائل
        messages = extract_messages(cursor)
        
        # استخراج جهات الاتصال
        contacts = extract_contacts(cursor)
        
        conn.close()
        
        # دمج بيانات جهات الاتصال مع الرسائل
        messages_with_contacts = enrich_messages_with_contacts(messages, contacts)
        
        return {
            "ok": True,
            "case_id": case_id,
            "total_messages": len(messages_with_contacts),
            "messages": messages_with_contacts,
            "contacts": contacts,
            "extracted_at": datetime.now().isoformat()
        }
        
    except sqlite3.Error as e:
        return {
            "ok": False,
            "error": f"SQLite error: {str(e)}"
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Unexpected error: {str(e)}"
        }


def extract_messages(cursor: sqlite3.Cursor) -> List[Dict]:
    """
    استخراج الرسائل من جدول message
    """
    
    # جدول الرسائل في واتساب عادة اسمه 'message'
    # الأعمدة المهمة:
    # - _id: معرف الرسالة
    # - key_remote_jid: رقم المرسل/المستقبل
    # - key_from_me: 1 إذا مُرسل، 0 إذا مُستقبل
    # - data: نص الرسالة
    # - timestamp: وقت الرسالة (milliseconds)
    # - media_wa_type: نوع الملف المرفق
    
    query = """
    SELECT 
        _id,
        key_remote_jid as remote_jid,
        key_from_me as from_me,
        data as message_text,
        timestamp,
        media_wa_type,
        media_mime_type,
        media_caption,
        latitude,
        longitude
    FROM message
    WHERE key_remote_jid IS NOT NULL
    ORDER BY timestamp ASC
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        messages = []
        for row in rows:
            msg = {
                "id": row["_id"],
                "remote_jid": row["remote_jid"],
                "from_me": bool(row["from_me"]),
                "text": row["message_text"] or "",
                "timestamp": row["timestamp"],
                "datetime": timestamp_to_datetime(row["timestamp"]),
                "media_type": get_media_type_name(row["media_wa_type"]),
                "media_mime": row["media_mime_type"],
                "caption": row["media_caption"],
                "latitude": row["latitude"],
                "longitude": row["longitude"]
            }
            messages.append(msg)
        
        return messages
        
    except sqlite3.Error as e:
        print(f"Error extracting messages: {e}")
        return []


def extract_contacts(cursor: sqlite3.Cursor) -> Dict[str, Dict]:
    """
    استخراج جهات الاتصال من جدول wa_contacts
    """
    
    query = """
    SELECT 
        jid,
        display_name,
        given_name,
        status
    FROM wa_contacts
    WHERE jid IS NOT NULL
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        contacts = {}
        for row in rows:
            jid = row["jid"]
            contacts[jid] = {
                "display_name": row["display_name"] or "Unknown",
                "given_name": row["given_name"] or "",
                "status": row["status"] or ""
            }
        
        return contacts
        
    except sqlite3.Error as e:
        print(f"Error extracting contacts: {e}")
        return {}


def enrich_messages_with_contacts(
    messages: List[Dict],
    contacts: Dict[str, Dict]
) -> List[Dict]:
    """
    إضافة بيانات جهات الاتصال للرسائل
    """
    
    for msg in messages:
        jid = msg["remote_jid"]
        
        if jid in contacts:
            msg["contact_name"] = contacts[jid]["display_name"]
            msg["contact_status"] = contacts[jid]["status"]
        else:
            # استخراج الرقم من JID
            # مثال: 966501234567@s.whatsapp.net → 966501234567
            phone = jid.split("@")[0] if "@" in jid else jid
            msg["contact_name"] = format_phone_number(phone)
            msg["contact_status"] = ""
    
    return messages


def timestamp_to_datetime(timestamp: int) -> str:
    """
    تحويل timestamp من milliseconds إلى تاريخ ووقت
    """
    if timestamp:
        try:
            dt = datetime.fromtimestamp(timestamp / 1000.0)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return ""
    return ""


def get_media_type_name(media_type: Optional[int]) -> str:
    """
    تحويل رقم نوع الملف إلى اسم
    """
    media_types = {
        0: "text",
        1: "image",
        2: "audio",
        3: "video",
        4: "contact",
        5: "location",
        9: "document",
        13: "gif",
        15: "audio_recorded",
        16: "sticker"
    }
    
    return media_types.get(media_type, "unknown")


def format_phone_number(phone: str) -> str:
    """
    تنسيق رقم الهاتف للعرض
    """
    # إزالة رمز الدولة إذا كان سعودي
    if phone.startswith("966"):
        phone = "0" + phone[3:]
    
    # إخفاء جزء من الرقم للخصوصية
    if len(phone) >= 10:
        return phone[:3] + "XXXX" + phone[-3:]
    
    return phone


def group_messages_by_chat(messages: List[Dict]) -> Dict[str, List[Dict]]:
    """
    تجميع الرسائل حسب المحادثة (رقم الجوال)
    """
    
    chats = {}
    
    for msg in messages:
        jid = msg["remote_jid"]
        
        if jid not in chats:
            chats[jid] = []
        
        chats[jid].append(msg)
    
    return chats


def get_chat_summary(messages: List[Dict]) -> Dict:
    """
    ملخص المحادثة (عدد الرسائل، أول وآخر رسالة، إلخ)
    """
    
    if not messages:
        return {}
    
    sent_count = sum(1 for m in messages if m["from_me"])
    received_count = len(messages) - sent_count
    
    return {
        "total_messages": len(messages),
        "sent": sent_count,
        "received": received_count,
        "first_message": messages[0]["datetime"],
        "last_message": messages[-1]["datetime"],
        "contact_name": messages[0].get("contact_name", "Unknown")
    }
