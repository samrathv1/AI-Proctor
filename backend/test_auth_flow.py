import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
import urllib.request
import json
from backend.app.core.config import settings
from backend.app.integrations.supabase import supabase_db

async def run_auth_verification():
    print("=" * 60)
    print("AI-PROCTOR AUTHENTICATION & IDENTITY VERIFICATION (PHASE 9)")
    print("=" * 60)

    # 1. Candidate Registration
    reg_data = {
        "name": "Tanvi Deshmukh",
        "roll_number": "CS-2026-095",
        "email": "tanvi.deshmukh@institution.edu",
        "class_name": "CS-2026",
        "department": "Computer Science & Engineering"
    }
    created = await supabase_db.create_student(reg_data)
    assert created["roll_number"] == "CS-2026-095"
    print(f"  [OK] Registration: Created student {created['name']} (ID: {created['id']})")

    # 2. Verify in Remote Supabase Database
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
    }
    url = f"{settings.SUPABASE_URL}/rest/v1/students?roll_number=eq.CS-2026-095"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        db_records = json.loads(resp.read().decode())
        assert len(db_records) == 1
        print(f"  [OK] Supabase Persistence: Record found in remote DB table: {db_records[0]['email']}")

    # 3. Candidate Login by Roll Number
    found_by_roll = await supabase_db.get_student_by_identifier("CS-2026-095")
    assert found_by_roll is not None and found_by_roll["id"] == created["id"]
    print("  [OK] Login by Roll Number: Authenticated successfully")

    # 4. Candidate Login by Institutional Email
    found_by_email = await supabase_db.get_student_by_identifier("tanvi.deshmukh@institution.edu")
    assert found_by_email is not None and found_by_email["id"] == created["id"]
    print("  [OK] Login by Institutional Email: Authenticated successfully")

    # 5. Face Enrollment Status Check (Initial = PENDING, Zero Biometric Leakage)
    status = await supabase_db.get_face_profile_status(created["id"])
    assert status["enrollment_status"] == "PENDING"
    assert status["has_embedding"] is False
    assert "face_embedding" not in status and "embedding" not in status
    print("  [OK] Biometric Status: PENDING (zero embeddings exposed)")

    # 6. Cleanup Verification Candidate
    del_url = f"{settings.SUPABASE_URL}/rest/v1/students?roll_number=eq.CS-2026-095"
    req_del = urllib.request.Request(del_url, headers=headers, method="DELETE")
    with urllib.request.urlopen(req_del) as resp:
        print("  [OK] Cleanup: Test candidate cleanly removed from Supabase")

    print("\n" + "=" * 60)
    print("AUTHENTICATION & IDENTITY VERIFICATION: PASS")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_auth_verification())
