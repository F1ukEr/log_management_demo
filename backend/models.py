from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from database import Base

class LogEntry(Base):
    __tablename__ = "logs"

    # Primary Key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Metadata & Source Information
    timestamp = Column("timestamp", DateTime(timezone=True), default=func.now(), index=True) # @timestamp ]
    tenant = Column(String, index=True, nullable=False) #Multi-tenant
    source = Column(String, index=True) 
    product = Column(String) 
    vendor = Column(String)

    # 2. รายละเอียดเหตุการณ์ (Event Details)
    event_type = Column(String, index=True)
    event_subtype = Column(String) 
    severity = Column(Integer)
    action = Column(String) # allow, deny, login, ฯลฯ

    # 3. ข้อมูลเครือข่าย (Network Information)
    src_ip = Column(String, index=True) 
    src_port = Column(Integer) 
    dst_ip = Column(String, index=True)
    dst_port = Column(Integer)
    protocol = Column(String)

    # 4. ข้อมูลผู้ใช้และระบบ (User, System & Application)
    username = Column(String, index=True)
    host = Column(String) 
    process = Column(String) 
    url = Column(Text) 
    http_method = Column(String)
    status_code = Column(Integer) 

    # 5. ข้อมูลความปลอดภัยและคลาวด์ (Security & Cloud)
    rule_name = Column(String) 
    rule_id = Column(String) 
    cloud_account_id = Column(String)
    cloud_region = Column(String)
    cloud_service = Column(String)

    # 6. ข้อมูลอื่นๆ (Others)
    # เก็บข้อความดิบหรือ JSON ดิบ โดยใช้ JSONB เพื่อให้ PostgreSQL สามารถ Query ค้นหาข้างในได้ประสิทธิภาพสูง
    raw = Column(JSONB)  
    tags = Column(ARRAY(String))

    # Indexes สำหรับการค้นหาที่เร็วขึ้น 
    __table_args__ = (
        Index("idx_logs_timestamp", "timestamp"),
        Index("idx_logs_tenant", "tenant"),
        Index("idx_logs_source", "source"),
        Index("idx_logs_event_type", "event_type"),
        Index("idx_logs_username", "username"),
        Index("idx_logs_src_ip", "src_ip"),
        Index("idx_logs_dst_ip", "dst_ip"),
    )

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=func.now(), index=True)
    rule_name = Column(String) 
    message = Column(String)
    log_id = Column(Integer)
    