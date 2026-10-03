import sys
import os
sys.path.insert(0, os.path.abspath("."))

import asyncio
import cv2
import numpy as np
import base64
import urllib.request
import json
from backend.app.core.config import settings
from backend.app.integrations.supabase import supabase_db
from backend.app.services.face_engine import face_engine
from backend.app.models.requests import FaceEnrollmentRequest
from backend.app.services.enrollment_service import enrollment_service

def generate_test_face():
    img = np.ones((400, 400, 3), dtype=np.uint8) * 220
    # Head contour
    cv2.ellipse(img, (200, 200), (90, 120), 0, 0, 360, (180, 200, 230), -1)
    # Eyes & Pupils
    cv2.circle(img, (200 - 35, 200 - 25), 14, (50, 50, 50), -1)
    cv2.circle(img, (200 + 35, 200 - 25), 14, (50, 50, 50), -1)
    cv2.circle(img, (200 - 35, 200 - 25), 6, (255, 255, 255), -1)
    cv2.circle(img, (200 + 35, 200 - 25), 6, (255, 255, 255), -1)
    # Eyebrows
    cv2.line(img, (200 - 55, 200 - 45), (200 - 15, 200 - 45), (40, 40, 40), 4)
    cv2.line(img, (200 + 15, 200 - 45), (200 + 55, 200 - 45), (40, 40, 40), 4)
    # Nose
    cv2.line(img, (200, 200 - 20), (200 - 5, 200 + 15), (100, 100, 100), 3)
    cv2.line(img, (200 - 5, 200 + 15), (200 + 10, 200 + 15), (100, 100, 100), 3)
    # Mouth
    cv2.ellipse(img, (200, 200 + 55), (35, 15), 0, 0, 180, (40, 40, 180), 4)
    
    _, buffer = cv2.imencode(".jpg", img)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("utf-8")

async def test_face_enrollment():
    print("=" * 60)
    print("AI-PROCTOR FACE ENROLLMENT PERSISTENCE (PHASE 10)")
    print("=" * 60)

    # Use seeded student s-01 (Dev Sharma)
    student_id = "s-01"
    b64_face = generate_test_face()

    req = FaceEnrollmentRequest(
        student_id=student_id,
        image_base64=b64_face,
        notes="Phase 10 Supabase test enrollment"
    )

    # 1. Execute Face Enrollment Pipeline
    res = await enrollment_service.enroll_face(req)
    print(f"  [OK] Face Enrollment Response: status={res.status}, quality={res.quality_score:.1f}, model={res.model_version}")

    # Explicit check: Zero raw embeddings in response model
    res_dict = res.model_dump()
    assert "face_embedding" not in res_dict
    assert "embedding" not in res_dict
    assert "embedding_bytes" not in res_dict
    print("  [OK] Biometric Privacy: Verified ZERO raw embeddings in API response")

    # 2. Verify in Remote Supabase Database
    headers = {
        "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}"
    }
    url = f"{settings.SUPABASE_URL}/rest/v1/student_face_profiles?student_id=eq.{student_id}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers)) as resp:
        records = json.loads(resp.read().decode())
        assert len(records) >= 1
        record = records[0]
        assert record["enrollment_status"] == "ENROLLED"
        assert record["face_embedding"] is not None
        print(f"  [OK] Supabase Persistence: Enrolled face profile in remote database (status={record['enrollment_status']}, quality={record['quality_score']})")

    # 3. Verify get_face_profile_status does NOT expose raw embedding
    status = await supabase_db.get_face_profile_status(student_id)
    assert status["enrollment_status"] == "ENROLLED"
    assert status["has_embedding"] is True
    assert "face_embedding" not in status
    print("  [OK] Biometric Privacy: get_face_profile_status returns has_embedding=True with NO raw bytes")

    # 4. Verify secure server-side retrieval for live surveillance cache
    cached_profiles = await supabase_db.get_exam_face_profiles("exam-01")
    assert student_id in cached_profiles
    assert isinstance(cached_profiles[student_id], bytes)
    print(f"  [OK] Secure Server-side Cache: Retrieved {len(cached_profiles[student_id])} bytes embedding for surveillance engine")

    print("\n" + "=" * 60)
    print("FACE ENROLLMENT PERSISTENCE: PASS")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_face_enrollment())
