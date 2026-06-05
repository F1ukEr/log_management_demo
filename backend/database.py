import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# โหลดค่าตัวแปรสภาพแวดล้อมจากไฟล์ .env (ถ้ามี)
load_dotenv()

# กำหนด URL สำหรับเชื่อมต่อฐานข้อมูล
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://loguser:password@localhost:5432/logmanagement"
)

# สร้าง Engine สำหรับเชื่อมต่อ
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# สร้าง SessionLocal สำหรับใช้งานในแต่ละ Request
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# สร้าง Base Class สำหรับให้ models.py นำไปสืบทอด
Base = declarative_base()

# Dependency function สำหรับ FastAPI เพื่อเรียกใช้และปิด Database Session อัตโนมัติ
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()