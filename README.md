#  Whisper-WA - Digital Forensics Platform
## منصة التحليل الجنائي الرقمي لواتساب

<div align="center">

![Whisper-WA Logo](Frontend/logo.png)

**نظام شامل لتحليل بيانات واتساب للأغراض الجنائية**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Educational-yellow.svg)]()

[English](#english) | [العربية](#arabic)

</div>

---

## 🌟 المميزات الرئيسية

### ✨ **واجهة مستخدم متقدمة**
- 🎨 تصميم عصري بتأثيرات Glass Morphism
- 🌐 دعم كامل للغتين (عربي/إنجليزي) مع RTL
- 📱 واجهة متجاوبة تعمل على جميع الأجهزة
- 🔐 نظام مصادقة متعدد المستويات (Admin/User)

### 🔧 **إمكانيات تقنية**
- 📲 استخراج تلقائي لبيانات واتساب من الأجهزة
- 🔓 فك تشفير قواعد بيانات واتساب (crypt12-15)
- 🔍 تحليل شامل للرسائل والملفات المرفقة
- 📊 كشف الأنماط المشبوهة والكيانات
- 🔎 محرك بحث متقدم
- 📄 توليد تقارير احترافية (PDF/CSV)

### 🛡️ **الأمان والخصوصية**
- 🔐 تشفير كلمات المرور (SHA-256)
- 🎫 نظام Session Tokens
- 👥 إدارة صلاحيات المستخدمين
- 📝 تسجيل كامل لجميع الأنشطة
- ✅ نظام موافقة على الطلبات

---

## 📋 متطلبات التشغيل

### 🖥️ **المتطلبات الأساسية**
- Python 3.8+
- ADB (Android Debug Bridge)
- wadecrypt (لفك تشفير واتساب)
- جهاز Android بصلاحيات Root

### 📦 **المكتبات المطلوبة**
```bash
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.0
PyJWT==2.8.0
Werkzeug==3.0.1
```

---

## 🚀 دليل التثبيت والتشغيل

### 1️⃣ **تثبيت المكتبات**

```bash
# تثبيت المكتبات من requirements.txt
pip install -r requirements.txt --break-system-packages

# أو تثبيت يدوي
pip install Flask Flask-CORS --break-system-packages
```

### 2️⃣ **تهيئة قاعدة البيانات**

```bash
# تشغيل ملف قاعدة البيانات
cd Backend
python database.py
```

هذا سينشئ:
- ✅ قاعدة بيانات `whisper_wa.db`
- ✅ حساب المسؤول الافتراضي

**بيانات المسؤول:**
- 📧 البريد: `admin@whisper-wa.local`
- 🔑 كلمة المرور: `admin123`

### 3️⃣ **تشغيل السيرفر**

```bash
# من مجلد Backend
python app.py
```

السيرفر سيشتغل على: **http://localhost:5000** 🌐

### 4️⃣ **فتح الواجهة**

افتح المتصفح وروح على:
```
Frontend/index.html
```

أو استخدم Live Server في VS Code

---

## 📁 هيكل المشروع

```
Whisper-WA/
│
├── Backend/                    # الباك اند
│   ├── app.py                 # السيرفر الرئيسي (Flask)
│   ├── database.py            # إدارة قاعدة البيانات
│   ├── acquisition.py         # سحب البيانات من الجهاز
│   ├── decrypt.py             # فك تشفير قاعدة البيانات
│   ├── parser.py              # استخراج الرسائل
│   ├── analysis.py            # التحليل الشامل
│   ├── index.py               # محرك البحث
│   ├── export.py              # تصدير التقارير
│   ├── reports.py             # إدارة التقارير
│   └── requirements.txt       # المكتبات المطلوبة
│
├── Frontend/                   # الفرونت اند
│   ├── index.html             # الصفحة الرئيسية
│   ├── auth.html              # تسجيل الدخول/طلب حساب
│   ├── pending.html           # انتظار الموافقة
│   ├── connect.html           # ربط الجهاز
│   ├── chat.html              # بناء التقرير
│   ├── analysis.html          # التحليل
│   ├── reports.html           # عرض التقارير
│   ├── admin.html             # لوحة الأدمن
│   ├── header.html            # الهيدر الموحد
│   └── logo.png               # اللوغو
│
└── Cases/                      # مجلد القضايا (يُنشأ تلقائياً)
    └── Case_001/
        ├── Evidence/          # الأدلة المسحوبة
        ├── Decrypted/         # قاعدة البيانات المفككة
        └── Analysis/          # نتائج التحليل
```

---

## 🔄 سير العمل (Workflow)

```
1. 🔐 تسجيل الدخول
   └─ Admin: admin@whisper-wa.local / admin123
   └─ User: طلب حساب → موافقة الأدمن

2. 📱 ربط الجهاز
   └─ USB أو Wi-Fi
   └─ فحص صلاحيات Root

3. 📥 سحب البيانات
   └─ msgstore.db.cryptXX
   └─ key file

4. 🔓 فك التشفير
   └─ استخدام wadecrypt
   └─ msgstore_decrypted.db

5. 🔍 التحليل
   └─ استخراج الرسائل
   └─ كشف الأنماط
   └─ استخراج الكيانات

6. 📊 التقرير
   └─ عرض النتائج
   └─ تصدير PDF/CSV
```

---

## 🎯 الـ API Endpoints

### 🔐 **Authentication**
```http
POST /api/auth/login
Body: { "email": "", "password": "" }
```

### 👥 **User Management**
```http
GET  /api/users
POST /api/access-requests
GET  /api/access-requests/pending
POST /api/access-requests/<id>/approve
POST /api/access-requests/<id>/reject
```

### 📱 **Device & Workflow**
```http
POST /api/device/connect
Body: { "method": "wifi|usb", "ip_port": "", "case_id": "" }

POST /api/workflow/run
Body: { "case_id": "", "wadecrypt_path": "", "timeout_sec": 180 }
```

### 💬 **Messages & Analysis**
```http
GET  /api/messages/<case_id>
GET  /api/chats/<case_id>
GET  /api/analysis/<case_id>
POST /api/analysis/run/<case_id>
```

### 🔎 **Search**
```http
POST /api/index/build
Body: { "messages": {"1": "text1", "2": "text2"} }

GET  /api/search?q=keyword
GET  /api/links
GET  /api/images
```

### 📊 **Cases & Reports**
```http
POST /api/cases
GET  /api/cases/<user_id>
POST /api/reports
GET  /api/reports/<user_id>
```

---

## 🛠️ الأدوات المستخدمة

### Backend:
- **Flask** - Web Framework
- **SQLite** - قاعدة البيانات
- **SQLAlchemy** - ORM

### Frontend:
- **HTML5/CSS3** - الهيكل والتصميم
- **JavaScript (Vanilla)** - البرمجة
- **Font Awesome** - الأيقونات
- **Google Fonts (Tajawal)** - الخط العربي

### Tools:
- **ADB** - Android Debug Bridge
- **wadecrypt** - WhatsApp Decryption Tool

---

## 📊 قاعدة البيانات

### 📦 **الجداول الرئيسية:**

#### **1. users**
```sql
- id (PK)
- name
- email (UNIQUE)
- password_hash
- job_title
- department
- role (admin/user)
- status (active/inactive)
- created_at
- last_login
```

#### **2. access_requests**
```sql
- id (PK)
- name
- email
- job_title
- department
- reason
- status (pending/approved/rejected)
- submitted_at
- reviewed_at
- reviewed_by (FK → users)
```

#### **3. cases**
```sql
- id (PK)
- case_id (UNIQUE)
- case_number
- investigator_id (FK → users)
- device_info
- acquisition_date
- status
- notes
```

#### **4. reports**
```sql
- id (PK)
- case_id (FK → cases)
- report_title
- report_type
- total_messages
- total_chats
- generated_by (FK → users)
- generated_at
- file_path
```

#### **5. activity_logs**
```sql
- id (PK)
- user_id (FK → users)
- action
- entity_type
- entity_id
- details
- ip_address
- timestamp
```

---

</div>
