# Whisper-WA - Digital Forensics Platform
## WhatsApp Digital Forensics Analysis Platform

<div align="center">

![Whisper-WA Logo](Frontend/logo.png)

**Comprehensive WhatsApp Data Analysis System for Forensic Purposes**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-Educational-yellow.svg)]()

</div>

---

##  Key Features

### **Advanced User Interface**
-  Modern design with Glass Morphism effects
-  Full bilingual support (Arabic/English) with RTL
-  Responsive interface works on all devices
-  Multi-level authentication system (Admin/User)

### 🔧 **Technical Capabilities**
-  Automatic WhatsApp data extraction from devices
-  WhatsApp database decryption (crypt12-15)
-  Comprehensive message and attachment analysis
-  Suspicious pattern and entity detection
-  Advanced search engine
-  Professional report generation (PDF/CSV)

###  **Security & Privacy**
-  Password encryption (SHA-256)
-  Session token system
-  User permission management
-  Complete activity logging
-  Request approval system

---

##  Requirements

###  **System Requirements**
- Python 3.8+
- ADB (Android Debug Bridge)
- wadecrypt (for WhatsApp decryption)
- Rooted Android device

### **Required Libraries**
```bash
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.0
PyJWT==2.8.0
Werkzeug==3.0.1
```

---

##  Installation & Setup Guide

### 1️ **Install Dependencies**

```bash
# Install from requirements.txt
pip install -r requirements.txt --break-system-packages

# Or manual installation
pip install Flask Flask-CORS --break-system-packages
```

### 2️ **Initialize Database**

```bash
# Run database file
cd Backend
python database.py
```

This will create:
- Database file `whisper_wa.db`
-  Default admin account

**Admin Credentials:**
-  Email: `admin@whisper-wa.local`
-  Password: `admin123`

### 3️ **Start Server**

```bash
# From Backend directory
python app.py
```

Server will run on: **http://localhost:5000** 

### 4️ **Open Interface**

Open your browser and navigate to:
```
Frontend/index.html
```

Or use Live Server in VS Code

---

##  Project Structure

```
Whisper-WA/
│
├── Backend/                    # Backend
│   ├── app.py                 # Main server (Flask)
│   ├── database.py            # Database management
│   ├── acquisition.py         # Data extraction from device
│   ├── decrypt.py             # Database decryption
│   ├── parser.py              # Message extraction
│   ├── analysis.py            # Comprehensive analysis
│   ├── index.py               # Search engine
│   ├── export.py              # Report export
│   ├── reports.py             # Report management
│   └── requirements.txt       # Dependencies
│
├── Frontend/                   # Frontend
│   ├── index.html             # Home page
│   ├── auth.html              # Login/Request account
│   ├── pending.html           # Approval pending
│   ├── connect.html           # Device connection
│   ├── chat.html              # Report builder
│   ├── analysis.html          # Analysis
│   ├── reports.html           # Reports view
│   ├── admin.html             # Admin dashboard
│   ├── header.html            # Unified header
│   └── logo.png               # Logo
│
└── Cases/                      # Cases folder (auto-created)
    └── Case_001/
        ├── Evidence/          # Extracted evidence
        ├── Decrypted/         # Decrypted database
        └── Analysis/          # Analysis results
```

---

##  Workflow

```
1.  Login
   └─ Admin: admin@whisper-wa.local / admin123
   └─ User: Request account → Admin approval

2.  Connect Device
   └─ USB or Wi-Fi
   └─ Root access check

3.  Data Extraction
   └─ msgstore.db.cryptXX
   └─ key file

4.  Decryption
   └─ Using wadecrypt
   └─ msgstore_decrypted.db

5.  Analysis
   └─ Message extraction
   └─ Pattern detection
   └─ Entity extraction

6.  Report
   └─ Display results
   └─ Export PDF/CSV
```

---

##  API Endpoints

###  **Authentication**
```http
POST /api/auth/login
Body: { "email": "", "password": "" }
```

###  **User Management**
```http
GET  /api/users
POST /api/access-requests
GET  /api/access-requests/pending
POST /api/access-requests/<id>/approve
POST /api/access-requests/<id>/reject
```

###  **Device & Workflow**
```http
POST /api/device/connect
Body: { "method": "wifi|usb", "ip_port": "", "case_id": "" }

POST /api/workflow/run
Body: { "case_id": "", "wadecrypt_path": "", "timeout_sec": 180 }
```

###  **Messages & Analysis**
```http
GET  /api/messages/<case_id>
GET  /api/chats/<case_id>
GET  /api/analysis/<case_id>
POST /api/analysis/run/<case_id>
```

###  **Search**
```http
POST /api/index/build
Body: { "messages": {"1": "text1", "2": "text2"} }

GET  /api/search?q=keyword
GET  /api/links
GET  /api/images
```

###  **Cases & Reports**
```http
POST /api/cases
GET  /api/cases/<user_id>
POST /api/reports
GET  /api/reports/<user_id>
```

---

##  Technology Stack

### Backend:
- **Flask** - Web Framework
- **SQLite** - Database
- **SQLAlchemy** - ORM

### Frontend:
- **HTML5/CSS3** - Structure & Design
- **JavaScript (Vanilla)** - Programming
- **Font Awesome** - Icons
- **Google Fonts (Tajawal)** - Arabic Typography

### Tools:
- **ADB** - Android Debug Bridge
- **wadecrypt** - WhatsApp Decryption Tool

---

##  Database Schema

### **Main Tables:**

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
