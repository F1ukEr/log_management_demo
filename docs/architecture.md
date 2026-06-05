# 🏛️ System Architecture & Data Flow

เอกสารนี้อธิบายถึงสถาปัตยกรรมของระบบ Centralized Log Management (SIEM) รวมถึงเส้นทางการไหลของข้อมูล (Data Flow) และการออกแบบระบบ Multi-tenant

---

## 1. Architecture Diagram

ระบบถูกออกแบบด้วยสถาปัตยกรรมแบบ Microservices ผ่าน Docker Container โดยแบ่งการทำงานออกเป็นส่วนต่างๆ อย่างชัดเจน เพื่อให้ง่ายต่อการดูแลและขยายระบบ (Scalability)

```mermaid
graph TD
    subgraph "1. Log Sources"
        FW[Firewall / Network] -- UDP 5140 --> SYS(Syslog Server)
        APP[Web Apps / Cloud] -- HTTP POST --> API(FastAPI Ingest Endpoint)
    end

    subgraph "2. Backend & Processing (FastAPI)"
        SYS --> NORM[Normalization Engine]
        API --> NORM
        NORM --> GEO[GeoIP Enrichment]
        GEO --> DB_WRITE[Database Writer]
        GEO --> ALERT_ENG[Alert / Rule Engine]
    end

    subgraph "3. Storage (PostgreSQL)"
        DB_WRITE -- Save Log --> PG[(PostgreSQL DB)]
        ALERT_ENG -- Query Last 5 Mins --> PG
        ALERT_ENG -- Trigger Alert --> PG
    end

    subgraph "4. Presentation & Security"
        PG -- Read Data --> API_READ(FastAPI Query Endpoint)
        API_READ -- JSON --> NGINX{Nginx Reverse Proxy\nHTTPS/SSL}
        NGINX --> UI[React Dashboard\nRecharts + RBAC]
    end

    subgraph "5. CI/CD Pipeline"
        GIT[GitHub Push] --> ACTION[GitHub Actions]
        ACTION -- Run Pytest --> SYS
    end


sequenceDiagram
    autonumber
    participant Source as Log Source (Firewall/App)
    participant Ingest as Ingestion (FastAPI)
    participant Process as Processing (Enrich)
    participant Rule as Alert Rule Engine
    participant DB as Database (PostgreSQL)
    participant UI as Web Dashboard (React)

    Source->>Ingest: ส่งข้อมูลดิบ (JSON/Syslog)
    
    rect rgb(240, 248, 255)
        Note over Process: Data Transformation
        Ingest->>Process: สกัดฟิลด์ (Regex/Mapping)
        Process->>Process: แนบพิกัด GeoIP (Enrichment)
    end
    
    Process->>Rule: ส่งต่อ Standardized Log
    
    rect rgb(255, 235, 238)
        Note over Rule: Security Analysis
        Rule->>DB: ดึงข้อมูลย้อนหลัง 5 นาทีมาประเมิน
        Rule->>Rule: ตรวจสอบเงื่อนไข (เช่น Brute Force)
    end
    
    Rule->>DB: บันทึก Log และ Alert (ถ้ามี) ลงตาราง
    UI->>DB: Request ข้อมูล (แนบสิทธิ์ Tenant/Role)
    DB-->>UI: ส่ง Filtered Data (เฉพาะสิทธิ์ที่เข้าถึงได้)
    UI->>UI: แสดงผลตารางและกราฟ (Recharts)

คำอธิบายแต่ละ Phase:
Raw Data (ข้อมูลดิบ): ข้อมูลวิ่งเข้ามาทาง HTTP POST (JSON) หรือทาง UDP 5140 (Syslog)

Normalized & Enriched Data: * Parsing: สกัดข้อมูลด้วย Regex จับคู่ฟิลด์ให้เป็นมาตรฐาน (Schema) ฟิลด์ที่ไม่มีใน Schema จะถูกเก็บใน raw (JSONB)

Enrichment: แปลงค่า src_ip เป็นข้อมูลภูมิศาสตร์ (Country)

Analyzed Data (วิเคราะห์และแจ้งเตือน): Rule Engine ตรวจสอบเงื่อนไขแบบ Time-series หากพบความผิดปกติ (เช่น Login ล้มเหลว 3 ครั้งใน 5 นาที) จะสร้าง Alert ทันที

Visualized Data (แสดงผล): ผู้ใช้เข้าถึงเว็บผ่าน HTTPS ข้อมูลจะถูกกรองตามสิทธิ์ (RBAC) ก่อนส่งไปเรนเดอร์เป็นกราฟและตาราง

3. Tenant Model & RBAC (ระบบแยกข้อมูลและจัดการสิทธิ์)
ระบบนี้รองรับการใช้งานแบบ Multi-tenant (รองรับหลายองค์กรในระบบเดียว) โดยใช้สถาปัตยกรรมแบบ Logical Separation (ใช้ Database และ Schema ร่วมกัน แต่แยกข้อมูลด้วย Logic)

🏢 Tenant Isolation (การแบ่งแยกข้อมูล)
Log ทุกรายการจะถูกประทับตราด้วยฟิลด์ tenant (เช่น demo, demoA, demoB)

การดึงข้อมูลผ่าน API จะถูกบังคับ (Force Filter) ด้วยค่า tenant เสมอในระดับ Backend (SQL Query) ทำให้ผู้ใช้ไม่สามารถเข้าถึงข้อมูลข้ามองค์กรได้เด็ดขาด

🔐 Role-Based Access Control (RBAC)
สิทธิ์การใช้งานถูกแบ่งเป็น 2 ระดับ:

Viewer (ผู้ใช้งานทั่วไป):

ถูกจำกัดให้มองเห็นและเข้าถึงได้เฉพาะ Log/Alert ของ Tenant ตัวเองเท่านั้น

ไม่สามารถแก้ไขหรือลบข้อมูลได้

Admin (ผู้ดูแลระบบระดับสูง):

มีสิทธิ์ระดับ Global Access สามารถสลับดูข้อมูลของ Tenant ใดก็ได้

มีสิทธิ์ใช้งาน Control Panel พิเศษ เช่น การอัปโหลด Batch Log File (JSON) และการสั่งทำ Data Retention (ล้างข้อมูลที่เก่ากว่า 7 วัน)