import pytest
from syslog import normalize_syslog # นำเข้าฟังก์ชันที่เราเขียนไว้

def test_normalize_syslog_success():
    # จำลอง Log ที่ถูกต้องจาก Firewall
    raw_log = "<134>Aug 20 12:44:56 fw01 vendor=demo product=ngfw action=deny src=10.0.1.10 dst=8.8.8.8 spt=5353 dpt=53 proto=udp msg=DNS blocked"
    
    result = normalize_syslog(raw_log)
    
    # ตรวจสอบว่าฟังก์ชันทำงานถูกต้องและดึงค่าออกมาได้เป๊ะ
    assert result is not None
    assert result["source"] == "syslog"
    assert result["event_type"] == "Firewall: deny"
    assert result["src_ip"] == "10.0.1.10"
    assert result["vendor"] == "fw01"

def test_normalize_syslog_fail():
    # จำลอง Log ขยะที่อ่านไม่รู้เรื่อง
    bad_log = "This is a random text that is not a log"
    
    result = normalize_syslog(bad_log)
    
    # ตรวจสอบว่าระบบจัดการ Error ได้ (ต้องคืนค่า None)
    assert result is None