# Centralized Log Management (SIEM Demo)

![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/react-%2320232a.svg?style=for-the-badge&logo=react&logoColor=%2361DAFB)
![PostgreSQL](https://img.shields.io/badge/postgresql-4169e1?style=for-the-badge&logo=postgresql&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)

ระบบบริหารจัดการ Log แบบรวมศูนย์ (Centralized Log Management) ที่ออกแบบมาในรูปแบบ Microservices รองรับการรับ Log จากหลายแหล่ง ทำ Normalization, GeoIP Enrichment และมี Rule Engine สำหรับตรวจจับพฤติกรรมผิดปกติแบบ Real-time พร้อม Web Dashboard สำหรับค้นหาและวิเคราะห์ข้อมูล

---

## Key Features

- **Multi-tenant Architecture** — รองรับหลายองค์กรในระบบเดียว แยกข้อมูลด้วย Logical Separation (ฟิลด์ `tenant` ในทุก Log)
- **Role-Based Access Control (RBAC)** — แบ่งสิทธิ์เป็น 2 ระดับ: `admin` (เข้าถึงได้ทุก Tenant) และ `viewer` (เห็นเฉพาะ Tenant ตัวเอง)
- **Universal Log Ingestion** — รับ Log ผ่าน HTTP POST (JSON) และ UDP 5140 (Syslog) รองรับ source: `m365`, `syslog`, `api`, `crowdstrike`, `aws`
- **Normalization Engine** — แปลง Log ดิบจากทุก source ให้เป็น Schema กลาง เก็บฟิลด์ยิบย่อยไว้ใน JSONB
- **GeoIP Enrichment** — แปลง `src_ip` เป็นชื่อประเทศอัตโนมัติ (จำลอง) และเก็บไว้ใน `raw.enriched_country`
- **Alert / Rule Engine** — ตรวจจับอัตโนมัติ 2 กฎ:
  - **Brute Force Login** — Login ล้มเหลว 5 ครั้งขึ้นไปจาก IP เดียวกัน ภายใน 5 นาที
  - **Log Flooding** — Source หรือ Event Type เดียวกันเข้ามามากกว่า 10 ครั้งภายใน 1 นาที
- **Webhook Notification** — ส่งแจ้งเตือนไปยัง Webhook URL เมื่อ Alert ถูก Trigger
- **React Dashboard** — มี Login, กราฟแท่ง (Top Event Types), กราฟเส้น (Timeline), ตาราง Log พร้อม Search และ Date Range Filter
- **HTTPS / SSL** — รองรับการเชื่อมต่อผ่าน Nginx Reverse Proxy พร้อม SSL/TLS
- **CI/CD** — GitHub Actions รัน Pytest อัตโนมัติทุกครั้งที่ Push ขึ้น `main`

---

## Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React.js, Recharts, Axios |
| Backend | Python 3.10, FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL 15 (JSONB สำหรับ Raw Data) |
| Infrastructure | Docker, Docker Compose, Nginx |
| Testing | Pytest |
| CI/CD | GitHub Actions |

---

## Architecture Overview

```
Log Sources
  ├── HTTP POST (JSON)  →  FastAPI /api/ingest
  └── UDP 5140 (Syslog) →  Syslog Server

FastAPI Backend
  ├── Normalization Engine  (แปลงเป็น Schema กลาง)
  ├── GeoIP Enrichment      (แปลง IP → Country)
  ├── Alert / Rule Engine   (Brute Force, Log Flooding)
  └── Database Writer       →  PostgreSQL

Presentation
  └── React Dashboard  ←  Nginx (HTTPS)  ←  FastAPI Query API
```

ดูรายละเอียดสถาปัตยกรรมเพิ่มเติมได้ที่ [docs/architecture.md](docs/architecture.md)

---

## Quick Start

### ข้อกำหนดเบื้องต้น

- Docker และ Docker Compose

### 1. สร้าง SSL Certificate (สำหรับทดสอบ)

```bash
mkdir -p certs
docker run --rm -v ${PWD}/certs:/certs alpine/openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout /certs/server.key \
  -out /certs/server.crt \
  -subj "/C=TH/ST=Bangkok/L=Bangkok/O=Demo/CN=localhost"
```

### 2. รันระบบ

```bash
docker compose up -d --build
```

### 3. เข้าใช้งาน

| URL | คำอธิบาย |
|---|---|
| `https://localhost:3443` | Web Dashboard (HTTPS) |
| `http://localhost:3000` | Web Dashboard (HTTP) |
| `http://localhost:8000/docs` | FastAPI Swagger UI |

> เบราว์เซอร์อาจแจ้งเตือนใบรับรองไม่ปลอดภัย ให้กด **Advanced** แล้วเลือก **Proceed to localhost**

---

## Demo Accounts

| Username | Password | Role | สิทธิ์ |
|---|---|---|---|
| `admin` | `password123` | Admin | เข้าถึงทุก Tenant, ใช้ File Upload และ Data Retention ได้ |
| `viewer` | `password123` | Viewer | เห็นเฉพาะข้อมูล Tenant `demo` |

---

## API Endpoints

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| `POST` | `/api/ingest` | รับ Log ดิบ (JSON) |
| `POST` | `/api/ingest/file_sample` | โหลด Sample Log จากไฟล์ |
| `DELETE` | `/api/ingest/clear` | ลบ Log และ Alert ทั้งหมด |
| `GET` | `/api/logs` | ดึงข้อมูล Log (รองรับ `?tenant=` และ `?limit=`) |
| `GET` | `/api/alerts` | ดึงข้อมูล Alert |
| `POST` | `/api/login` | เข้าสู่ระบบ |

### ตัวอย่าง Log ที่รองรับ

**M365 Log**
```json
{
  "source": "m365",
  "tenant": "demoB",
  "@timestamp": "2024-03-01T10:00:00Z",
  "workload": "AzureAD",
  "event_type": "LogonFailed",
  "user": "alice@example.com",
  "ip": "203.1.2.3",
  "status": "Failed"
}
```

**Syslog (Firewall)**
```json
{
  "source": "syslog",
  "tenant": "demoA",
  "@timestamp": "2024-03-01T10:00:00Z",
  "event_type": "firewall_alert",
  "src_ip": "10.0.0.1",
  "payload": {
    "src_port": 1234,
    "dst_ip": "192.168.1.1",
    "protocol": "TCP"
  }
}
```

---

## Project Structure

```
log_management_demo/
├── backend/
│   ├── main.py           # FastAPI app, API endpoints, Rule Engine
│   ├── models.py         # SQLAlchemy models (LogEntry, Alert)
│   ├── database.py       # DB connection
│   ├── syslog.py         # Syslog UDP listener
│   ├── test_syslog.py    # Pytest unit tests
│   ├── sample_logs.json  # ตัวอย่าง Log สำหรับทดสอบ
│   └── requirements.txt
├── frontend/
│   └── src/
│       └── App.jsx       # React Dashboard (Login, Charts, Table)
├── docs/
│   ├── architecture.md   # สถาปัตยกรรมและ Data Flow
│   ├── setup_appliance.md
│   └── setup_saas.md
├── certs/                # SSL Certificate (ไม่ถูก commit)
├── docker-compose.yml
├── nginx-custom.conf
└── .github/workflows/ci-cd.yml
```

---

## Running Tests

```bash
cd backend
pytest test_syslog.py
```

GitHub Actions จะรัน Test อัตโนมัติทุกครั้งที่ Push หรือ Pull Request ไปยังสาขา `main`

---

## Documentation

- [System Architecture & Data Flow](docs/architecture.md)
- [On-Premise Appliance Setup](docs/setup_appliance.md)
- [SaaS / Cloud Deployment](docs/setup_saas.md)
