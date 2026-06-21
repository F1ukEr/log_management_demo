from fastapi import FastAPI, Request, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from dateutil import parser
from datetime import datetime, timedelta
from pydantic import BaseModel
import json
import requests

# อิมพอร์ตไฟล์ที่เราสร้างไว้
import models
from database import engine, get_db

# สั่งให้ SQLAlchemy สร้างตารางในฐานข้อมูลอัตโนมัติตอนเริ่มรันแอป
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Log Management API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class LoginRequest(BaseModel):
    username: str
    password: str

# ---------------------------------------------------------
# ส่วนที่ 1: ฟังก์ชัน Normalization แปลงข้อมูลเข้า Schema กลาง
# ---------------------------------------------------------
def parse_ts(raw: dict) -> datetime:
    return parser.parse(raw.get("@timestamp", datetime.utcnow().isoformat() + "Z"))

def normalize_log(source: str, raw_data: dict) -> dict:
    if source == "m365":
        return {
            "timestamp": parse_ts(raw_data),
            "tenant": raw_data.get("tenant", "unknown"),
            "source": raw_data.get("source", "m365"),
            "vendor": "Microsoft",
            "product": raw_data.get("workload", "unknown"),
            "event_type": raw_data.get("event_type", "unknown"),
            "action": "login" if raw_data.get("status") == "Success" else "unknown",
            "src_ip": raw_data.get("ip", ""),
            "username": raw_data.get("user", ""), # ใช้ฟิลด์ username ให้ตรงกับ models.py
            "raw": raw_data # เก็บ dict ดิบไว้ SQLAlchemy จะแปลงเป็น JSONB ให้เอง
        }

    if source == "syslog":
        raw_payload = raw_data.get("payload", {})
        raw_data.update(raw_payload) # ดึงข้อมูลจาก payload ขึ้นมาไว้บนระดับเดียวกับ log หลักเพื่อให้ง่ายต่อการเข้าถึง
        return {
            "timestamp": parse_ts(raw_data),
            "tenant": raw_data.get("tenant", "demoA"),
            "source": "syslog",
            "event_type": raw_data.get("event_type", "firewall_alert"),
            "username": raw_data.get("user", "-"), # ใส่ - ไว้ก่อนถ้า Syslog ไม่มีชื่อ User
            "src_ip": raw_data.get("src_ip", ""),
            "raw": raw_payload # 👈 ฟิลด์ยิบย่อยอย่าง src_port, dst_ip, protocol จะถูกเซฟในนี้อย่างปลอดภัย
        }

    # api, crowdstrike, aws
    return {
        "timestamp": parse_ts(raw_data),
        "tenant": raw_data.get("tenant", "demo"),
        "source": "api",
        "event_type": raw_data.get("event_type"),
        "username": raw_data.get("user"),
        "src_ip": raw_data.get("ip"),
        "raw": raw_data
    }

def enrich_geoip(ip_address: str) -> str:
    # เป็นฟังก์ชันจำลองการแปลง IP เป็นชื่อประเทศ
    if not ip_address: return "Unknown"
    if ip_address.startswith("10.") or ip_address.startswith("192.168."): return "Internal Network"
    if ip_address.startswith("203."): return "Thailand"
    return "United States"
# ---------------------------------------------------------
# ส่วนที่ 2: Ingestion API Endpoint (บันทึกลง DB)
# ---------------------------------------------------------
@app.post("/api/ingest")
async def ingest_log(request: Request, db: Session = Depends(get_db)):

    raw_data = await request.json()
    source = raw_data.get("source")

    if source not in ("m365", "syslog", "api", "crowdstrike", "aws"):
        raise HTTPException(status_code=400, detail="Unsupported log source")

    standardized_log = normalize_log(source, raw_data)

    try:
        standardized_log["raw"]["enriched_country"] = enrich_geoip(standardized_log["src_ip"])
        db_log = models.LogEntry(**standardized_log)

        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        # กฎข้อที่ 1: Brute Force (Login Failed 3 ครั้งใน 5 นาที)
        if db_log.event_type in ["app_login_failed","LogonFailed"]:
            five_mins_ago = db_log.timestamp - timedelta(minutes=5)
            # ค้นหา Log ที่เคยล้มเหลวจาก IP นี้ ในช่วง 5 นาทีที่ผ่านมา
            failed_count = db.query(models.LogEntry).filter(
                models.LogEntry.src_ip == db_log.src_ip,
                models.LogEntry.event_type.in_(["app_login_failed", "LogonFailed"]),
                models.LogEntry.timestamp >= five_mins_ago
            ).count()

            # ถ้านับได้ 5 ครั้งขึ้นไป (รวมครั้งนี้) ให้แจ้งเตือน!
            if failed_count >= 5:
                msg = f"พบการพยายาม Login ล้มเหลวมากกว่า 5 ครั้งจาก IP: {db_log.src_ip}"
                alert = models.Alert(rule_name="Brute Force Login", message=msg, log_id=db_log.id)
                db.add(alert)
                db.commit()
                webhook_alert("Brute Force Login", msg)
        # กฎข้อที่ 2:Source หรือ Event เข้ามามากกว่า 10 ครั้งใน 1 นาที
        one_min_ago = db_log.timestamp - timedelta(minutes=1)
        source_count = db.query(models.LogEntry).filter(
            models.LogEntry.source == db_log.source,
            models.LogEntry.timestamp >= one_min_ago
        ).count()
        event_count = db.query(models.LogEntry).filter(
            models.LogEntry.event_type == db_log.event_type,
            models.LogEntry.timestamp >= one_min_ago
        ).count()
        if source_count >= 10 or event_count >= 10:
            trigger_reason = f"Source '{db_log.source}'" if source_count >= 10 else f"Event '{db_log.event_type}'"
            msg = f"⚠️ ปริมาณข้อมูลผิดปกติ: ตรวจพบ {trigger_reason} เข้ามาถึง 10 ครั้งภายในเวลา 1 นาที"
            
            alert = models.Alert(rule_name="Log Flooding Detected", message=msg, log_id=db_log.id)
            db.add(alert)
            db.commit()
            webhook_alert("Log Flooding Detected", msg)

        return {"status":"success","id":db_log.id}
    except Exception as e:
        db.rollback() # ถอยการทำงานกลับหากเกิด Error ป้องกัน DB ค้าง
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest/file_sample")
async def ingest_file_sample(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        sample_logs = json.loads(await file.read())

        for raw_log in sample_logs:
            source = raw_log.get("source")
            if source == "m365":
                standardized_log = normalize_log("m365", raw_log)
            else:
                continue # ข้ามถ้าไม่ใช่ m365

            standardized_log["raw"]["enriched_country"] = enrich_geoip(standardized_log["src_ip"])
            db_log = models.LogEntry(**standardized_log)
            db.add(db_log)
        
        db.commit()
        return {"status":"success","message":"Sample logs ingested"}
    except Exception as e:
        db.rollback() # ถอยการทำงานกลับหากเกิด Error ป้องกัน DB ค้าง
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/ingest/clear")
async def clear_logs(db: Session = Depends(get_db)):
    try:
        db.query(models.Alert).delete()
        db.query(models.LogEntry).delete()
        db.commit()
        return {"status":"success","message":"All logs and alerts cleared"}
    except Exception as e:
        db.rollback() # ถอยการทำงานกลับหากเกิด Error ป้องกัน DB ค้าง
        raise HTTPException(status_code=500, detail=str(e))
# ---------------------------------------------------------
# ส่วนที่ 3: API Endpoint สำหรับดึงข้อมูล Logs และ Alerts
@app.get("/api/logs")
def get_logs(limit: int = 50, tenant: str = None, user_role: str = None, db: Session = Depends(get_db)):
    try:
        query = db.query(models.LogEntry)
        
        if user_role == "viewer":
                tenant = "demo" # กำหนด tenant เป็น demo สำหรับ viewer เพื่อจำกัดการเข้าถึงข้อมูล
                query = query.filter(models.LogEntry.tenant == tenant)
        else: 
            if tenant:
                query = query.filter(models.LogEntry.tenant == tenant)
        logs = query.order_by(models.LogEntry.timestamp.desc()).limit(limit).all()
        return {
            "status": "success",
            "total": len(logs),
            "data": logs
        }
    except Exception as e:
        db.rollback() # ถอยการทำงานกลับหากเกิด Error ป้องกัน DB ค้าง
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts")
def get_alerts(limit: int = 50, tenant: str = None, db: Session = Depends(get_db)):
    try:
        alerts = db.query(models.Alert).order_by(models.Alert.timestamp.desc()).limit(limit).all()
        return {
            "status": "success",
            "total": len(alerts),
            "data": alerts
        }
    except Exception as e:
        db.rollback() # ถอยการทำงานกลับหากเกิด Error ป้องกัน DB ค้าง
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
def login(request: LoginRequest):
    # จำลองฐานข้อมูล User แบบง่ายๆ
    users_db = {
        "admin": {"password": "password123", "role": "admin", "tenant": "all"},
        "viewer": {"password": "password123", "role": "viewer", "tenant": "demo"} # ดูได้แค่ demo
    }
    
    user = users_db.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
        
    return {
        "status": "success",
        "token": f"fake-jwt-token-{request.username}", # จำลอง Token
        "role": user["role"],
        "tenant": user["tenant"]
    }

# ---------------------------------------------------------
#ระบบแจ้งเตือน Webhook
def webhook_alert(rule_name: str, message: str):
    webhook_url = "https://webhook.site/973beac3-74f7-4bcc-968f-14696345f1ad" # เปลี่ยนเป็น URL ของ Webhook ที่ต้องการส่งแจ้งเตือน
    payload = {
        "text": f"ALERT: {rule_name}\n{message}"
    }
    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code != 200:
            print(f"Failed to send alert: {response.status_code} {response.text}")
        print(f"Alert sent: {message}")
    except Exception as e:
        print(f"Error sending alert: {str(e)}")