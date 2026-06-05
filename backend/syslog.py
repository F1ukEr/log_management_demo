import socket
import re
import requests
from datetime import datetime

FASTAPI_INGEST_URL = "http://127.0.0.1:8000/api/ingest"

def normalize_syslog(raw_log: str) -> dict:
    # กวาดหาข้อมูล ไม่สนว่าจะหน้าตาแปลกแค่ไหน
    match = re.search(r'(?P<timestamp>[A-Za-z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+(?P<host>\S+)\s+(?P<message>.*)', raw_log)
    
    if not match:
        print(f"Regex not match! ข้อมูลที่รับมาคือ: {raw_log}")
        return None
    
    data = match.groupdict()

    # ดึง IP และ Action ออกมาจากข้อความ message
    src_ip_match = re.search(r'src=(\d+\.\d+\.\d+\.\d+)', data["message"])
    src_ip = src_ip_match.group(1) if src_ip_match else "unknown"
    
    action_match = re.search(r'action=(\w+)', data["message"])
    action = action_match.group(1) if action_match else "unknown"

    normalized = {
        "tenant": "demoA",
        "source": "syslog",
        "event_type": f"Firewall: {action}",
        "src_ip": src_ip,
        "vendor": data["host"],
        "@timestamp": datetime.utcnow().isoformat() + "Z",
        "message": data["message"]
    }

    return normalized

def start_syslog_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5140))
    print("🚀 Syslog UDP server listening on UDP port 5140...")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            message = data.decode("utf-8").strip()
            print(f"📥 Received from {addr}: {message}")

            normalized = normalize_syslog(message)

            if normalized:
                response = requests.post(FASTAPI_INGEST_URL, json=normalized)
                print(f"✅ Sent to API (Status: {response.status_code})")
            else:
                print("❌ Failed to parse syslog message")
                
        except Exception as e:
            print("🚨 Error:", e)

if __name__ == "__main__":
    start_syslog_server()