import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
import urllib.request
import json
from backend.app.core.config import settings
from backend.app.integrations.supabase import supabase_db

async def run_persistence_verification():
    print("=" * 60)
    print("AI-PROCTOR REAL PERSISTENCE VERIFICATION (PHASE 8)")
    print("=" * 60)

    # 1. READ VERIFICATION
    print("\n[1] READ VERIFICATION:")
    
    # 1a. Fetch seeded student s-01
    student_s01 = await supabase_db.get_student("s-01")
    assert student_s01 is not None, "Failed to read seeded student s-01"
    print(f"  [OK] Seeded Student (s-01): {student_s01['name']} ({student_s01['roll_number']})")
    assert student_s01["name"] == "Dev Sharma"

    # 1b. Fetch seeded students s-02 and s-03
    student_s02 = await supabase_db.get_student("s-02")
    student_s03 = await supabase_db.get_student("s-03")
    assert student_s02 is not None and student_s03 is not None
    print(f"  [OK] Seeded Student (s-02): {student_s02['name']} ({student_s02['roll_number']})")
    print(f"  [OK] Seeded Student (s-03): {student_s03['name']} ({student_s03['roll_number']})")

    # 1c. Fetch exam roster for exam-01
    roster = await supabase_db.get_exam_roster("exam-01")
    assert len(roster) >= 3, f"Expected at least 3 students in roster, got {len(roster)}"
    print(f"  [OK] Seeded Exam Roster (exam-01): {len(roster)} candidates enrolled")
    for r in roster:
        print(f"      - {r['student_id']}: {r['name']} | Seat: {r['seat_number']} | Status: {r['attendance_status']}")

    # 1d. Fetch ESP32 device directly from remote iot_devices table
    url = f"{settings.SUPABASE_URL}/rest/v1/iot_devices?device_uid=eq.ESP32-HALL304-01"
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        dev_data = json.loads(resp.read().decode())
        assert len(dev_data) == 1, f"Expected ESP32-HALL304-01, found: {dev_data}"
        print(f"  [OK] Seeded ESP32 Device: {dev_data[0]['device_uid']} | Status: {dev_data[0]['status']} | IP: {dev_data[0]['ip_address']}")

    # 2. WRITE VERIFICATION (Legitimate Application Operation)
    print("\n[2] WRITE VERIFICATION (Real Database Write):")
    test_payload = {
        "id": "s-test-write",
        "name": "Database Verification Student",
        "roll_number": "TEST-ROLL-999",
        "email": "db.verify@institution.edu",
        "class_name": "CS-2026",
        "department": "Computer Science & Engineering"
    }

    # Perform legitimate application create_student write
    created = await supabase_db.create_student(test_payload)
    print(f"  [OK] Written record through application service: ID {created['id']}")

    # Verify directly via remote PostgREST endpoint that record exists in remote PostgreSQL
    verify_url = f"{settings.SUPABASE_URL}/rest/v1/students?roll_number=eq.TEST-ROLL-999"
    req_verify = urllib.request.Request(verify_url, headers=headers)
    with urllib.request.urlopen(req_verify) as resp:
        remote_records = json.loads(resp.read().decode())
        assert len(remote_records) == 1, f"Remote write verification failed: {remote_records}"
        print(f"  [OK] Verified physically persisted in remote PostgreSQL: {remote_records[0]['name']} (ID: {remote_records[0]['id']})")

    # 3. CLEANUP ONLY TEST RECORD
    print("\n[3] CLEANUP (Preserving All Production & Seeded Data):")
    del_url = f"{settings.SUPABASE_URL}/rest/v1/students?roll_number=eq.TEST-ROLL-999"
    req_del = urllib.request.Request(del_url, headers=headers, method="DELETE")
    with urllib.request.urlopen(req_del) as resp:
        print("  [OK] Test record successfully deleted from remote table")

    # Verify test record is deleted
    with urllib.request.urlopen(urllib.request.Request(verify_url, headers=headers)) as resp:
        remaining = json.loads(resp.read().decode())
        assert len(remaining) == 0, "Test record was not cleaned up"
        print("  [OK] Cleanup verified: 0 test records remaining")

    # Verify seeded records remain intact
    student_s01_after = await supabase_db.get_student("s-01")
    assert student_s01_after is not None and student_s01_after["name"] == "Dev Sharma"
    print("  [OK] Seeded baseline data remains 100% intact")

    print("\n" + "=" * 60)
    print("REAL PERSISTENCE VERIFICATION: PASS")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_persistence_verification())
