# ☁️ Installation Guide: SaaS / Cloud Deployment

เอกสารนี้อธิบายขั้นตอนการติดตั้งระบบ SIEM ในรูปแบบ Software-as-a-Service (SaaS) บน Cloud Provider เพื่อให้บริการแบบ Multi-tenant โดยแยกข้อมูลของลูกค้าแต่ละรายอย่างปลอดภัย

## 📋 Prerequisites (สิ่งที่ต้องเตรียม)
* **Cloud Server:** เช่น AWS EC2, DigitalOcean Droplet, Google Compute Engine
* **Network:** Public IP Address แบบ Static
* **Domain Name:** เช่น `siem.yourcompany.com`
* **Software:** ติดตั้ง Docker และ Docker Compose v2 ขึ้นไป

---

## 🚀 Step-by-Step Installation

### Step 1: DNS & Firewall Setup
1. นำ Domain Name ไปชี้ A Record มาที่ Public IP ของ Cloud Server
2. ตั้งค่า Cloud Security Group (หรือ UFW) ให้เปิดรับพอร์ต:
   * `TCP 80` และ `TCP 443` (สำหรับหน้าเว็บและ API)
   * *หมายเหตุ: ปิดพอร์ต 5432 (Database) ไม่ให้เข้าถึงจากภายนอกโดยเด็ดขาด*

### Step 2: Clone Repository
ดาวน์โหลดซอร์สโค้ดลงใน Cloud Server

```bash
git clone [https://github.com/your-username/log-management-siem.git](https://github.com/your-username/log-management-siem.git)
cd log-management-siem

###Step 3: ตั้งค่า SSL Certificate ด้วย Let's Encrypt (Production)
สำหรับการใช้งานจริงบนอินเทอร์เน็ต ต้องใช้ SSL ที่มีความน่าเชื่อถือ:

แก้ไขไฟล์ nginx-custom.conf เปลี่ยน server_name เป็นโดเมนจริงของคุณ

ใช้ Certbot ออกใบรับรองฟรี:
sudo apt install certbot
sudo certbot certonly --standalone -d siem.yourcompany.com
คัดลอกไฟล์ fullchain.pem และ privkey.pem ไปไว้ในโฟลเดอร์ ./certs/ และอัปเดตพาธใน Nginx ให้ตรงกัน

###Step 4: Environment Variables (Security)
สร้างไฟล์ .env เพื่อเปลี่ยนรหัสผ่านเริ่มต้นทั้งหมดให้ปลอดภัยสำหรับการขึ้น Cloud:

ข้อมูลโค้ด
POSTGRES_USER=saas_admin
POSTGRES_PASSWORD=Strong_Cloud_Password_123!
POSTGRES_DB=saas_logmanagement
JWT_SECRET=Your_Super_Secret_Key_For_Production
ข้อควรระวัง: ต้องอัปเดตไฟล์ docker-compose.yml ให้ดึงค่าผ่าน .env แทนการ Hardcode รหัสผ่านในไฟล์โดยตรง

###Step 5: Start the SaaS Platform
สั่งรันระบบขึ้นคลาวด์

docker compose up -d --build

##🏢 Tenant Onboarding (การรับลูกค้าใหม่)
เมื่อลูกค้ารายใหม่ (Tenant) ต้องการส่ง Log เข้ามายังระบบ SaaS ของเรา:
สร้าง Tenant ID: กำหนดรหัสให้ลูกค้า เช่น tenant="company_x"

สร้าง Viewer Account: สร้างบัญชีผู้ใช้ในหน้า Login ให้ลูกค้า โดยกำหนด Role เป็น Viewer และผูกกับ Tenant ของลูกค้า

การส่ง Log (API Ingestion):
ให้ลูกค้ายิง HTTP POST Request มาที่ https://siem.yourcompany.com/api/ingest พร้อมแนบ JSON Payload ที่ระบุ Tenant ของตนเอง:

JSON
{
    "tenant": "company_x",
    "source": "api",
    "event_type": "app_login",
    "src_ip": "1.2.3.4"
}
ข้อมูลจะถูกบันทึกและกรองด้วยระบบ RBAC ทำให้ลูกค้าแต่ละบริษัทจะมองเห็นเฉพาะข้อมูลของตนเองเมื่อเข้าใช้งาน Dashboard