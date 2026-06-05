# 🛠️ Installation Guide: On-Premise Appliance

ขั้นตอนการติดตั้ง Centralized Log Management SIEM บนเซิร์ฟเวอร์ภายในองค์กร (On-Premise / Virtual Machine) 

## 📋 Prerequisites (สิ่งที่ต้องเตรียม)
1. เครื่อง Server หรือ VM (แนะนำ Ubuntu 22.04 LTS หรือ CentOS)
2. RAM ขั้นต่ำ 4GB, CPU 2 Cores
3. ติดตั้ง Docker และ Docker Compose v2 ขึ้นไป
4. เปิดพอร์ต Firewall ภายในองค์กร: `TCP 443` (หน้าเว็บ), `UDP 5140` (รับ Syslog)

---

## 🚀 Step-by-Step Installation

### Step 1: Clone Repository
ดาวน์โหลดซอร์สโค้ดของระบบลงในเครื่อง Server

```bash
git clone [https://github.com/your-username/log-management-siem.git](https://github.com/your-username/log-management-siem.git)
cd log-management-siem
Step 2: สร้าง Self-Signed SSL Certificate
เนื่องจากเป็นการใช้งานภายในองค์กร (Local IP) เราจะสร้างใบรับรอง SSL ชั่วคราวเพื่อให้ระบบรองรับ HTTPS

Bash
mkdir -p certs
docker run --rm -v ${PWD}/certs:/certs alpine/openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /certs/server.key -out /certs/server.crt -subj "/C=TH/ST=Bangkok/L=Bangkok/O=InternalAppliance/CN=localhost"
Step 3: ตรวจสอบและแก้ไข Configuration
เปิดไฟล์ docker-compose.yml เพื่อให้แน่ใจว่าพอร์ตที่จำเป็นถูกเปิดใช้งาน:

Frontend: 3443:443 สำหรับหน้า Dashboard

Backend: 5140:5140/udp สำหรับรับ Syslog

Step 4: Start the Appliance
สั่งรันระบบทั้งหมดในโหมด Background

Bash
docker compose up -d --build
ระบบจะทำการสร้าง Database, Backend API, และ Frontend UI อัตโนมัติ

Step 5: การตั้งค่าอุปกรณ์ต้นทาง (Log Sources)
เข้าไปตั้งค่าที่ Firewall หรือ Network Devices ขององค์กร (เช่น Fortinet, Cisco, pfSense) ให้ส่ง Syslog มาที่:

Destination IP: [IP ของเครื่อง Server นี้]

Port: 5140

Protocol: UDP