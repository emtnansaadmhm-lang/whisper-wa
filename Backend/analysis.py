"""
analysis.py - WhatsApp Data Analysis
تحليل بيانات واتساب واستخراج الكيانات والأنماط
"""

import re
from datetime import datetime
from collections import Counter, defaultdict
from typing import List, Dict, Tuple, Optional
import json


# ========================================
# ENTITY EXTRACTION (استخراج الكيانات)
# ========================================

def extract_phone_numbers(text: str) -> List[str]:
    """
    استخراج أرقام الجوالات من النص
    """
    # أنماط أرقام الجوال السعودية
    patterns = [
        r'\b(05\d{8})\b',  # 05xxxxxxxx
        r'\b(\+?966\s?5\d{8})\b',  # +966 5xxxxxxxx
        r'\b(00966\s?5\d{8})\b',  # 00966 5xxxxxxxx
    ]
    
    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        numbers.extend(matches)
    
    # تنظيف وتوحيد الأرقام
    cleaned = []
    for num in numbers:
        num = re.sub(r'[\s\-\(\)]', '', num)  # إزالة المسافات والرموز
        if num.startswith('+966'):
            num = '0' + num[4:]
        elif num.startswith('00966'):
            num = '0' + num[5:]
        elif num.startswith('966'):
            num = '0' + num[3:]
        cleaned.append(num)
    
    return list(set(cleaned))  # إزالة التكرار


def extract_iban_numbers(text: str) -> List[str]:
    """
    استخراج أرقام IBAN السعودية
    """
    # نمط IBAN السعودي: SA + 22 رقم
    pattern = r'\b(SA\d{22})\b'
    ibans = re.findall(pattern, text, re.IGNORECASE)
    return list(set([iban.upper() for iban in ibans]))


def extract_urls(text: str) -> List[str]:
    """
    استخراج الروابط من النص
    """
    # نمط الروابط
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    urls = re.findall(pattern, text)
    return list(set(urls))


def extract_emails(text: str) -> List[str]:
    """
    استخراج الإيميلات من النص
    """
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(pattern, text)
    return list(set(emails))


def detect_url_shorteners(url: str) -> bool:
    """
    كشف الروابط المختصرة
    """
    shorteners = [
        'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly',
        'is.gd', 'buff.ly', 'adf.ly', 'bl.ink', 'lnkd.in',
        'short.link', 'rb.gy', 'cutt.ly', 's.id'
    ]
    
    return any(shortener in url.lower() for shortener in shorteners)


def extract_locations(messages: List[Dict]) -> List[Dict]:
    """
    استخراج المواقع الجغرافية من الرسائل
    """
    locations = []
    
    for msg in messages:
        if msg.get('latitude') and msg.get('longitude'):
            locations.append({
                'message_id': msg['id'],
                'latitude': msg['latitude'],
                'longitude': msg['longitude'],
                'datetime': msg['datetime'],
                'from_me': msg['from_me']
            })
    
    return locations


# ========================================
# KEYWORD ANALYSIS (تحليل الكلمات المفتاحية)
# ========================================

# كلمات مشبوهة مرتبطة بالاحتيال
SUSPICIOUS_KEYWORDS = {
    'ar': [
        'OTP', 'كود', 'رمز', 'تحويل', 'حول', 'بنك', 'حساب',
        'بطاقة', 'ائتمان', 'رصيد', 'سحب', 'إيداع', 'مبلغ',
        'جائزة', 'ربحت', 'فزت', 'مكافأة', 'هدية', 'مجاني',
        'عاجل', 'فوري', 'سريع', 'الآن', 'حالاً'
    ],
    'en': [
        'OTP', 'code', 'verification', 'transfer', 'bank', 'account',
        'card', 'credit', 'balance', 'withdraw', 'deposit', 'amount',
        'prize', 'won', 'reward', 'gift', 'free',
        'urgent', 'immediately', 'now', 'quick', 'fast'
    ]
}


def analyze_keywords(messages: List[Dict], custom_keywords: List[str] = None) -> Dict:
    """
    تحليل الكلمات المفتاحية في الرسائل
    """
    # دمج الكلمات المشبوهة
    all_keywords = SUSPICIOUS_KEYWORDS['ar'] + SUSPICIOUS_KEYWORDS['en']
    
    if custom_keywords:
        all_keywords.extend(custom_keywords)
    
    keyword_analysis = {}
    
    for keyword in all_keywords:
        keyword_lower = keyword.lower()
        matches = []
        
        for msg in messages:
            text = msg.get('text', '').lower()
            if keyword_lower in text:
                matches.append({
                    'message_id': msg['id'],
                    'text': msg['text'][:200],  # أول 200 حرف
                    'datetime': msg['datetime'],
                    'from_me': msg['from_me'],
                    'contact': msg.get('contact_name', 'Unknown')
                })
        
        if matches:
            keyword_analysis[keyword] = {
                'count': len(matches),
                'messages': matches[:10]  # أول 10 رسائل فقط
            }
    
    # ترتيب حسب الأكثر تكراراً
    sorted_keywords = dict(sorted(
        keyword_analysis.items(),
        key=lambda x: x[1]['count'],
        reverse=True
    ))
    
    return sorted_keywords


# ========================================
# TEMPORAL ANALYSIS (التحليل الزمني)
# ========================================

def analyze_temporal_patterns(messages: List[Dict]) -> Dict:
    """
    تحليل الأنماط الزمنية للرسائل
    """
    if not messages:
        return {}
    
    hourly_dist = defaultdict(int)
    daily_dist = defaultdict(int)
    
    for msg in messages:
        dt_str = msg.get('datetime', '')
        if not dt_str:
            continue
        
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            
            # توزيع الساعات
            hour = dt.hour
            hourly_dist[hour] += 1
            
            # توزيع الأيام
            day = dt.strftime("%Y-%m-%d")
            daily_dist[day] += 1
            
        except:
            continue
    
    # إيجاد أكثر ساعة نشاط
    peak_hour = max(hourly_dist.items(), key=lambda x: x[1])[0] if hourly_dist else 0
    
    # إيجاد أكثر يوم نشاط
    peak_day = max(daily_dist.items(), key=lambda x: x[1])[0] if daily_dist else ""
    
    # حساب مدة التواصل
    first_msg = messages[0]['datetime']
    last_msg = messages[-1]['datetime']
    
    try:
        first_dt = datetime.strptime(first_msg, "%Y-%m-%d %H:%M:%S")
        last_dt = datetime.strptime(last_msg, "%Y-%m-%d %H:%M:%S")
        duration_days = (last_dt - first_dt).days
    except:
        duration_days = 0
    
    return {
        'peak_hour': f"{peak_hour:02d}:00",
        'peak_day': peak_day,
        'duration_days': duration_days,
        'hourly_distribution': dict(hourly_dist),
        'daily_distribution': dict(daily_dist),
        'total_messages': len(messages),
        'first_message': first_msg,
        'last_message': last_msg
    }


# ========================================
# RELATIONSHIP ANALYSIS (تحليل العلاقات)
# ========================================

def analyze_relationships(messages: List[Dict]) -> Dict:
    """
    تحليل العلاقات والتفاعل بين الأطراف
    """
    # تجميع حسب remote_jid
    chats = defaultdict(list)
    
    for msg in messages:
        jid = msg.get('remote_jid', 'unknown')
        chats[jid].append(msg)
    
    relationships = {}
    
    for jid, chat_msgs in chats.items():
        sent = sum(1 for m in chat_msgs if m['from_me'])
        received = len(chat_msgs) - sent
        
        # حساب النسبة
        total = sent + received
        sent_ratio = (sent / total * 100) if total > 0 else 0
        received_ratio = (received / total * 100) if total > 0 else 0
        
        relationships[jid] = {
            'contact_name': chat_msgs[0].get('contact_name', 'Unknown'),
            'total_messages': total,
            'sent': sent,
            'received': received,
            'sent_ratio': round(sent_ratio, 1),
            'received_ratio': round(received_ratio, 1),
            'first_contact': chat_msgs[0]['datetime'],
            'last_contact': chat_msgs[-1]['datetime']
        }
    
    return relationships


# ========================================
# SUSPICIOUS PATTERNS (كشف الأنماط المشبوهة)
# ========================================

def detect_suspicious_patterns(messages: List[Dict]) -> List[Dict]:
    """
    كشف الأنماط المشبوهة في الرسائل
    """
    flags = []
    
    # 1. فحص الروابط المختصرة
    shortened_urls = []
    for msg in messages:
        urls = extract_urls(msg.get('text', ''))
        for url in urls:
            if detect_url_shorteners(url):
                shortened_urls.append({
                    'url': url,
                    'message_id': msg['id'],
                    'datetime': msg['datetime']
                })
    
    if shortened_urls:
        flags.append({
            'type': 'shortened_urls',
            'severity': 'medium',
            'count': len(shortened_urls),
            'description_ar': 'تم رصد روابط مختصرة تحتاج تحقق',
            'description_en': 'Shortened URLs detected that need verification',
            'examples': shortened_urls[:5]
        })
    
    # 2. فحص كلمات التحويل والـ OTP
    transfer_keywords = ['تحويل', 'transfer', 'OTP', 'كود', 'code', 'رمز']
    transfer_msgs = []
    
    for msg in messages:
        text = msg.get('text', '').lower()
        if any(kw.lower() in text for kw in transfer_keywords):
            transfer_msgs.append(msg['id'])
    
    if transfer_msgs:
        flags.append({
            'type': 'transfer_keywords',
            'severity': 'high',
            'count': len(transfer_msgs),
            'description_ar': 'كلمات مرتبطة بالتحويل/التحقق',
            'description_en': 'Transfer/verification keywords detected',
            'message_ids': transfer_msgs[:10]
        })
    
    # 3. فحص أرقام IBAN
    iban_found = []
    for msg in messages:
        ibans = extract_iban_numbers(msg.get('text', ''))
        if ibans:
            iban_found.extend(ibans)
    
    if iban_found:
        flags.append({
            'type': 'iban_numbers',
            'severity': 'high',
            'count': len(set(iban_found)),
            'description_ar': 'تم رصد أرقام IBAN',
            'description_en': 'IBAN numbers detected',
            'ibans': list(set(iban_found))
        })
    
    # 4. فحص أرقام جوال متعددة
    phone_numbers = []
    for msg in messages:
        phones = extract_phone_numbers(msg.get('text', ''))
        phone_numbers.extend(phones)
    
    unique_phones = list(set(phone_numbers))
    if len(unique_phones) >= 3:
        flags.append({
            'type': 'multiple_phone_numbers',
            'severity': 'medium',
            'count': len(unique_phones),
            'description_ar': 'تم رصد عدة أرقام جوال',
            'description_en': 'Multiple phone numbers detected',
            'numbers': unique_phones[:10]
        })
    
    # 5. نشاط في أوقات غير عادية (منتصف الليل)
    late_night_msgs = []
    for msg in messages:
        dt_str = msg.get('datetime', '')
        if not dt_str:
            continue
        try:
            dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            if dt.hour >= 1 and dt.hour <= 4:  # من 1 ص إلى 4 ص
                late_night_msgs.append(msg['id'])
        except:
            continue
    
    if len(late_night_msgs) >= 10:
        flags.append({
            'type': 'late_night_activity',
            'severity': 'low',
            'count': len(late_night_msgs),
            'description_ar': 'نشاط غير عادي في منتصف الليل',
            'description_en': 'Unusual late night activity',
            'percentage': round(len(late_night_msgs) / len(messages) * 100, 1)
        })
    
    return flags


# ========================================
# MEDIA ANALYSIS (تحليل الملفات المرفقة)
# ========================================

def analyze_media(messages: List[Dict]) -> Dict:
    """
    تحليل الملفات المرفقة
    """
    media_types = defaultdict(int)
    
    for msg in messages:
        media_type = msg.get('media_type', 'text')
        media_types[media_type] += 1
    
    return {
        'total_media': sum(media_types.values()) - media_types.get('text', 0),
        'breakdown': dict(media_types),
        'images': media_types.get('image', 0),
        'videos': media_types.get('video', 0),
        'audio': media_types.get('audio', 0),
        'documents': media_types.get('document', 0),
        'locations': media_types.get('location', 0)
    }


# ========================================
# COMPREHENSIVE ANALYSIS (التحليل الشامل)
# ========================================

def analyze_whatsapp_data(messages: List[Dict], case_id: str) -> dict:
    """
    تحليل شامل لبيانات واتساب
    """
    if not messages:
        return {
            "ok": False,
            "error": "No messages to analyze"
        }
    
    # استخراج كل الكيانات
    all_text = " ".join([msg.get('text', '') for msg in messages])
    
    phone_numbers = extract_phone_numbers(all_text)
    ibans = extract_iban_numbers(all_text)
    urls = extract_urls(all_text)
    emails = extract_emails(all_text)
    locations = extract_locations(messages)
    
    # تحليل الكلمات المفتاحية
    keywords = analyze_keywords(messages)
    
    # التحليل الزمني
    temporal = analyze_temporal_patterns(messages)
    
    # تحليل العلاقات
    relationships = analyze_relationships(messages)
    
    # كشف الأنماط المشبوهة
    flags = detect_suspicious_patterns(messages)
    
    # تحليل الملفات
    media = analyze_media(messages)
    
    # الملخص
    summary = {
        'total_messages': len(messages),
        'sent_messages': sum(1 for m in messages if m['from_me']),
        'received_messages': sum(1 for m in messages if not m['from_me']),
        'total_chats': len(relationships),
        'first_message': messages[0]['datetime'],
        'last_message': messages[-1]['datetime']
    }
    
    return {
        "ok": True,
        "case_id": case_id,
        "analyzed_at": datetime.now().isoformat(),
        "summary": summary,
        "entities": {
            "phone_numbers": phone_numbers,
            "ibans": ibans,
            "urls": urls,
            "emails": emails,
            "locations": locations
        },
        "keywords": keywords,
        "temporal": temporal,
        "relationships": relationships,
        "flags": flags,
        "media": media
    }


def save_analysis_report(analysis_data: dict, case_id: str, output_dir: str = "Cases") -> str:
    """
    حفظ تقرير التحليل كملف JSON
    """
    import os
    
    case_dir = os.path.join(output_dir, case_id, "Analysis")
    os.makedirs(case_dir, exist_ok=True)
    
    report_path = os.path.join(case_dir, "analysis_report.json")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)
    
    return report_path
