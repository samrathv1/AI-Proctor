import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status

from backend.app.integrations.supabase import supabase_db
from backend.app.services.biometric_cache import biometric_cache_manager
from backend.app.core.logging import logger
from backend.app.core.config import settings


class ExamService:
    """
    Authoritative Exam Lifecycle & Invigilator Control Service.
    Connects Student Identity -> Exam Roster -> Seat -> Camera Coverage -> Live Session -> Summary.
    """

    # In-memory fallback exams when database is disconnected or during offline testing
    _in_memory_exams: Dict[str, Dict[str, Any]] = {
        "exam-01": {
            "id": "exam-01",
            "exam_code": "CS-402-DSGT",
            "name": "Discrete Structures & Graph Theory (CS-402)",
            "subject": "Discrete Mathematics & CS",
            "exam_date": "2026-10-03",
            "start_time": "10:00 AM",
            "end_time": "12:00 PM",
            "duration_minutes": 120,
            "room": "Hall 304 - Engineering Wing B",
            "invigilator_name": "Dr. Robert Vance, Ph.D.",
            "status": "LIVE",
            "description": "Mid-term examination with real-time biometric and behavioural surveillance."
        }
    }

    async def list_exams(self) -> List[Dict[str, Any]]:
        """Lists all examinations with live student counts and session telemetry."""
        exams_list: List[Dict[str, Any]] = []

        if supabase_db._client:
            try:
                res = supabase_db._client.table("exams").select("*").order("exam_date", desc=True).execute()
                if res.data:
                    for ex in res.data:
                        eid = ex["id"]
                        # Count enrolled students
                        roster_res = supabase_db._client.table("exam_students").select("id", count="exact").eq("exam_id", eid).execute()
                        total_students = roster_res.count if roster_res.count is not None else 0

                        # Count alerts
                        alerts_res = supabase_db._client.table("alerts").select("id, severity", count="exact").eq("exam_id", eid).execute()
                        alert_count = alerts_res.count if alerts_res.count is not None else 0

                        # Check biometric cache state
                        is_cached = biometric_cache_manager.is_cached(eid)

                        exams_list.append({
                            "id": eid,
                            "title": ex.get("name", "Untitled Examination"),
                            "name": ex.get("name", "Untitled Examination"),
                            "subject": ex.get("subject", "General"),
                            "code": ex.get("exam_code", "EX-101"),
                            "exam_code": ex.get("exam_code", "EX-101"),
                            "date": ex.get("exam_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                            "exam_date": ex.get("exam_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                            "startTime": ex.get("start_time", "10:00 AM"),
                            "start_time": ex.get("start_time", "10:00 AM"),
                            "endTime": ex.get("end_time", "12:00 PM"),
                            "end_time": ex.get("end_time", "12:00 PM"),
                            "durationMinutes": ex.get("duration_minutes", 120),
                            "duration_minutes": ex.get("duration_minutes", 120),
                            "totalStudents": total_students,
                            "activeStudents": total_students if ex.get("status") == "LIVE" else 0,
                            "status": ex.get("status", "SCHEDULED"),
                            "room": ex.get("room", "Examination Hall"),
                            "invigilator": ex.get("invigilator_name", "Staff Invigilator"),
                            "invigilator_name": ex.get("invigilator_name", "Staff Invigilator"),
                            "activeCameras": 3,
                            "alertCount": alert_count,
                            "biometrics_cached": is_cached,
                            "description": ex.get("description", "")
                        })
                    return exams_list
            except Exception as e:
                logger.error(f"Error fetching exams from Supabase: {str(e)}")

        # Fallback to in-memory store
        for eid, ex in self._in_memory_exams.items():
            roster = await self.get_exam_roster(eid)
            exams_list.append({
                "id": eid,
                "title": ex["name"],
                "name": ex["name"],
                "subject": ex["subject"],
                "code": ex["exam_code"],
                "exam_code": ex["exam_code"],
                "date": ex["exam_date"],
                "exam_date": ex["exam_date"],
                "startTime": ex["start_time"],
                "start_time": ex["start_time"],
                "endTime": ex["end_time"],
                "end_time": ex["end_time"],
                "durationMinutes": ex["duration_minutes"],
                "duration_minutes": ex["duration_minutes"],
                "totalStudents": len(roster),
                "activeStudents": len(roster) if ex["status"] == "LIVE" else 0,
                "status": ex["status"],
                "room": ex["room"],
                "invigilator": ex["invigilator_name"],
                "invigilator_name": ex["invigilator_name"],
                "activeCameras": 3,
                "alertCount": 0,
                "biometrics_cached": biometric_cache_manager.is_cached(eid),
                "description": ex.get("description", "")
            })
        return exams_list

    async def get_exam(self, exam_id: str) -> Dict[str, Any]:
        """Fetches detailed exam state, active session, and biometric readiness."""
        if supabase_db._client:
            try:
                res = supabase_db._client.table("exams").select("*").or_(f"id.eq.{exam_id},exam_code.eq.{exam_id}").execute()
                if res.data and len(res.data) > 0:
                    ex = res.data[0]
                    eid = ex["id"]
                    roster = await self.get_exam_roster(eid)
                    enrolled_count = sum(1 for s in roster if s.get("face_enrolled") is True)

                    # Get active session if any
                    session_res = supabase_db._client.table("exam_sessions").select("*").eq("exam_id", eid).order("created_at", desc=True).limit(1).execute()
                    active_session = session_res.data[0] if session_res.data else None
                    active_session_id = active_session["id"] if active_session else f"ses-{eid}"

                    return {
                        "id": eid,
                        "title": ex.get("name", "Untitled Examination"),
                        "name": ex.get("name", "Untitled Examination"),
                        "subject": ex.get("subject", "General"),
                        "code": ex.get("exam_code", "EX-101"),
                        "exam_code": ex.get("exam_code", "EX-101"),
                        "date": ex.get("exam_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                        "exam_date": ex.get("exam_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
                        "startTime": ex.get("start_time", "10:00 AM"),
                        "start_time": ex.get("start_time", "10:00 AM"),
                        "endTime": ex.get("end_time", "12:00 PM"),
                        "end_time": ex.get("end_time", "12:00 PM"),
                        "durationMinutes": ex.get("duration_minutes", 120),
                        "duration_minutes": ex.get("duration_minutes", 120),
                        "room": ex.get("room", "Hall 304"),
                        "invigilator": ex.get("invigilator_name", "Dr. Robert Vance, Ph.D."),
                        "invigilator_name": ex.get("invigilator_name", "Dr. Robert Vance, Ph.D."),
                        "status": ex.get("status", "SCHEDULED"),
                        "totalStudents": len(roster),
                        "enrolled_biometrics_count": enrolled_count,
                        "active_session_id": active_session_id,
                        "session_status": active_session.get("status", "PENDING") if active_session else "PENDING",
                        "biometrics_cached": biometric_cache_manager.is_cached(eid),
                        "activeCameras": 3,
                        "description": ex.get("description", "")
                    }
            except Exception as e:
                logger.error(f"Error fetching exam {exam_id} from Supabase: {str(e)}")

        # Fallback
        if exam_id in self._in_memory_exams or exam_id in ["exam-01", "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"]:
            ex = self._in_memory_exams.get("exam-01", self._in_memory_exams.get(exam_id))
            roster = await self.get_exam_roster(ex["id"])
            enrolled_count = sum(1 for s in roster if s.get("face_enrolled") is True)
            return {
                "id": ex["id"],
                "title": ex["name"],
                "name": ex["name"],
                "subject": ex["subject"],
                "code": ex["exam_code"],
                "exam_code": ex["exam_code"],
                "date": ex["exam_date"],
                "exam_date": ex["exam_date"],
                "startTime": ex["start_time"],
                "start_time": ex["start_time"],
                "endTime": ex["end_time"],
                "end_time": ex["end_time"],
                "durationMinutes": ex["duration_minutes"],
                "duration_minutes": ex["duration_minutes"],
                "room": ex["room"],
                "invigilator": ex["invigilator_name"],
                "invigilator_name": ex["invigilator_name"],
                "status": ex["status"],
                "totalStudents": len(roster),
                "enrolled_biometrics_count": enrolled_count,
                "active_session_id": f"ses-{ex['id']}",
                "session_status": "RUNNING" if ex["status"] == "LIVE" else "PENDING",
                "biometrics_cached": biometric_cache_manager.is_cached(ex["id"]),
                "activeCameras": 3,
                "description": ex.get("description", "")
            }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Examination '{exam_id}' not found"
        )

    async def create_exam(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Creates a new exam session in Supabase with initial session and camera bindings."""
        exam_id = data.get("id") or f"exam-{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        record = {
            "id": exam_id,
            "exam_code": data.get("code") or data.get("exam_code") or f"EX-{uuid.uuid4().hex[:4].upper()}",
            "name": data.get("name") or data.get("title") or "Untitled Exam",
            "subject": data.get("subject", "General Examination"),
            "exam_date": data.get("date") or data.get("exam_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "start_time": data.get("startTime") or data.get("start_time") or "10:00 AM",
            "end_time": data.get("endTime") or data.get("end_time") or "12:00 PM",
            "duration_minutes": int(data.get("durationMinutes") or data.get("duration_minutes") or 120),
            "room": data.get("room") or "Hall 304 - Engineering Wing B",
            "invigilator_name": data.get("invigilator") or data.get("invigilator_name") or "Dr. Robert Vance, Ph.D.",
            "status": data.get("status") or "SCHEDULED",
            "description": data.get("description", ""),
            "created_at": now_iso,
            "updated_at": now_iso
        }

        if supabase_db._client:
            try:
                res = supabase_db._client.table("exams").insert(record).execute()
                if res.data and len(res.data) > 0:
                    record = res.data[0]
                    # Also create initial exam_sessions row
                    supabase_db._client.table("exam_sessions").insert({
                        "id": f"ses-{record['id']}",
                        "exam_id": record["id"],
                        "status": "PENDING",
                        "active_camera_count": 3,
                        "created_at": now_iso,
                        "updated_at": now_iso
                    }).execute()
            except Exception as e:
                logger.error(f"Error creating exam in Supabase: {str(e)}")

        # Keep in-memory store synchronized
        self._in_memory_exams[record["id"]] = record
        return record

    async def get_exam_roster(self, exam_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the authoritative candidate roster for an examination.
        Includes Student -> Seat -> Camera -> Face Enrollment Status.
        """
        roster_list: List[Dict[str, Any]] = []

        if supabase_db._client:
            try:
                res = supabase_db._client.table("exam_students").select(
                    "id, exam_id, student_id, seat_number, camera_id, attendance_status, face_verified, risk_score, students(id, name, roll_number, email)"
                ).eq("exam_id", exam_id).execute()

                if res.data:
                    for row in res.data:
                        st = row.get("students") or {}
                        sid = row.get("student_id") or st.get("id")

                        # Check face enrollment status
                        face_status = await supabase_db.get_face_profile_status(sid)
                        face_enrolled = bool(face_status and face_status.get("has_embedding"))

                        roster_list.append({
                            "id": sid,
                            "student_id": sid,
                            "name": st.get("name", "Unknown Candidate"),
                            "roll_number": st.get("roll_number", "N/A"),
                            "email": st.get("email", ""),
                            "seat_number": row.get("seat_number", "Unassigned"),
                            "camera_id": row.get("camera_id") or "cam-01",
                            "attendance_status": row.get("attendance_status", "PRESENT"),
                            "face_verified": row.get("face_verified", False),
                            "face_enrolled": face_enrolled,
                            "enrollment_status": face_status.get("enrollment_status") if face_status else "PENDING",
                            "quality_score": face_status.get("quality_score") if face_status else None,
                            "model_version": face_status.get("model_version") if face_status else None,
                            "risk_score": row.get("risk_score", 0),
                        })
                    if roster_list:
                        return roster_list
            except Exception as e:
                logger.error(f"Error fetching exam roster from Supabase: {str(e)}")

        # Fallback to in-memory exam roster
        raw_fallback = await supabase_db.get_exam_roster(exam_id)
        for r in raw_fallback:
            sid = r["student_id"]
            face_status = await supabase_db.get_face_profile_status(sid)
            face_enrolled = bool(face_status and face_status.get("has_embedding"))
            roster_list.append({
                "id": sid,
                "student_id": sid,
                "name": r.get("name", "Unknown Candidate"),
                "roll_number": r.get("roll_number", "N/A"),
                "email": f"{r.get('roll_number', 'cand').lower()}@institution.edu",
                "seat_number": r.get("seat_number", "B4-12"),
                "camera_id": "cam-01",
                "attendance_status": r.get("attendance_status", "PRESENT"),
                "face_verified": r.get("face_verified", False),
                "face_enrolled": face_enrolled,
                "enrollment_status": face_status.get("enrollment_status") if face_status else "PENDING",
                "quality_score": face_status.get("quality_score") if face_status else None,
                "model_version": face_status.get("model_version") if face_status else None,
                "risk_score": r.get("risk_score", 0),
            })
        return roster_list

    async def add_student_to_roster(
        self,
        exam_id: str,
        student_id: str,
        seat_number: str = "B4-01",
        camera_id: str = "cam-01"
    ) -> Dict[str, Any]:
        """Assigns a student to the exam roster with seat and camera coverage."""
        student = await supabase_db.get_student(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student ID '{student_id}' does not exist in student registry"
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        roster_item = {
            "id": str(uuid.uuid4()),
            "exam_id": exam_id,
            "student_id": student_id,
            "seat_number": seat_number,
            "camera_id": camera_id,
            "attendance_status": "PRESENT",
            "face_verified": False,
            "risk_score": 0,
            "created_at": now_iso,
            "updated_at": now_iso
        }

        if supabase_db._client:
            try:
                # Upsert into exam_students
                existing = supabase_db._client.table("exam_students").select("id").eq("exam_id", exam_id).eq("student_id", student_id).execute()
                if existing.data and len(existing.data) > 0:
                    supabase_db._client.table("exam_students").update({
                        "seat_number": seat_number,
                        "camera_id": camera_id,
                        "updated_at": now_iso
                    }).eq("id", existing.data[0]["id"]).execute()
                else:
                    supabase_db._client.table("exam_students").insert(roster_item).execute()
            except Exception as e:
                logger.error(f"Error assigning student {student_id} to exam {exam_id} in Supabase: {str(e)}")

        # Keep in-memory roster synchronized
        if exam_id not in supabase_db._in_memory_exam_rosters:
            supabase_db._in_memory_exam_rosters[exam_id] = []
        if not any(r["student_id"] == student_id for r in supabase_db._in_memory_exam_rosters[exam_id]):
            supabase_db._in_memory_exam_rosters[exam_id].append({
                "student_id": student_id,
                "name": student["name"],
                "roll_number": student["roll_number"],
                "seat_number": seat_number,
                "camera_id": camera_id,
                "attendance_status": "PRESENT",
                "face_verified": False,
                "risk_score": 0
            })

        # Invalidate cache if active so new student is included
        biometric_cache_manager.clear_cache(exam_id)
        return roster_item

    async def remove_student_from_roster(self, exam_id: str, student_id: str) -> bool:
        """Removes a student from an exam roster."""
        if supabase_db._client:
            try:
                supabase_db._client.table("exam_students").delete().eq("exam_id", exam_id).eq("student_id", student_id).execute()
            except Exception as e:
                logger.error(f"Error removing student from exam roster in Supabase: {str(e)}")

        if exam_id in supabase_db._in_memory_exam_rosters:
            supabase_db._in_memory_exam_rosters[exam_id] = [
                r for r in supabase_db._in_memory_exam_rosters[exam_id] if r["student_id"] != student_id
            ]

        biometric_cache_manager.clear_cache(exam_id)
        return True

    async def start_exam(self, exam_id: str) -> Dict[str, Any]:
        """
        Validates exam state, checks roster and biometric enrollment,
        mounts exam-specific biometric cache, and marks exam/session LIVE.
        """
        # 1. Fetch exam
        exam = await self.get_exam(exam_id)

        # 2. Check roster
        roster = await self.get_exam_roster(exam_id)
        if not roster:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"EMPTY_EXAM_ROSTER: Examination '{exam_id}' has no registered students in its roster."
            )

        # 3. Mount exam-specific biometric cache (strictly roster candidates)
        session_id = exam.get("active_session_id") or f"ses-{exam_id}"
        cache = await biometric_cache_manager.get_or_load_cache(exam_id, session_id, force_reload=True)

        # 4. Mark exam status as LIVE in Supabase
        now_iso = datetime.now(timezone.utc).isoformat()
        if supabase_db._client:
            try:
                supabase_db._client.table("exams").update({
                    "status": "LIVE",
                    "updated_at": now_iso
                }).eq("id", exam_id).execute()

                supabase_db._client.table("exam_sessions").update({
                    "status": "RUNNING",
                    "start_time": now_iso,
                    "updated_at": now_iso
                }).eq("exam_id", exam_id).execute()
            except Exception as e:
                logger.error(f"Error starting exam in Supabase: {str(e)}")

        if exam_id in self._in_memory_exams:
            self._in_memory_exams[exam_id]["status"] = "LIVE"

        # 5. Audit event
        await supabase_db.record_audit_event(
            actor="invigilator",
            action="EXAM_STARTED",
            entity_type="exam",
            entity_id=exam_id,
            metadata={
                "session_id": session_id,
                "roster_count": len(roster),
                "cached_templates_count": cache.size,
                "model_version": cache.model_version
            }
        )

        return {
            "exam_id": exam_id,
            "session_id": session_id,
            "status": "LIVE",
            "message": f"Examination '{exam['name']}' is now LIVE. Mounted {cache.size} candidate biometric templates.",
            "enrolled_candidates_cached_count": cache.size,
            "total_students": len(roster),
            "model_version": cache.model_version,
            "started_at": now_iso
        }

    async def end_exam(self, exam_id: str) -> Dict[str, Any]:
        """
        Stops live surveillance, clears biometric templates from server memory,
        returns ESP32 to safe idle state, marks exam ENDED, and generates summary.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. Clear biometric cache
        biometric_cache_manager.clear_cache(exam_id)

        # 2. Return ESP32 hardware to safe state (Buzzer OFF, LED OFF)
        try:
            from backend.app.services.iot_service import iot_service
            await iot_service.dispatch_alert_to_devices("ESP32-HALL304-01", "CLEAR_ALERTS", "LOW")
        except Exception as e:
            logger.debug(f"Hardware reset advisory on exam end: {e}")

        # 3. Update status in Supabase
        if supabase_db._client:
            try:
                supabase_db._client.table("exams").update({
                    "status": "ENDED",
                    "updated_at": now_iso
                }).eq("id", exam_id).execute()

                supabase_db._client.table("exam_sessions").update({
                    "status": "COMPLETED",
                    "end_time": now_iso,
                    "updated_at": now_iso
                }).eq("exam_id", exam_id).execute()
            except Exception as e:
                logger.error(f"Error ending exam in Supabase: {str(e)}")

        if exam_id in self._in_memory_exams:
            self._in_memory_exams[exam_id]["status"] = "ENDED"

        # 4. Generate summary
        summary = await self.get_exam_summary(exam_id)

        # 5. Audit event
        await supabase_db.record_audit_event(
            actor="invigilator",
            action="EXAM_ENDED",
            entity_type="exam",
            entity_id=exam_id,
            metadata={
                "ended_at": now_iso,
                "total_events": summary.get("observable_events_count", 0),
                "total_alerts": summary.get("alerts_count", 0)
            }
        )

        return {
            "exam_id": exam_id,
            "status": "ENDED",
            "ended_at": now_iso,
            "cache_cleared": True,
            "summary": summary,
            "message": "Examination surveillance ended successfully. All evidence preserved."
        }

    async def get_exam_summary(self, exam_id: str) -> Dict[str, Any]:
        """
        Generates comprehensive objective examination summary.
        Reports observable physical events, alerts, and verification metrics.
        STRICT ETHICS: Zero 'cheater' or definitive disciplinary labels.
        """
        exam = await self.get_exam(exam_id)
        roster = await self.get_exam_roster(exam_id)

        observable_events_count = 0
        alerts_count = 0
        critical_alerts_count = 0
        unknown_identities_count = 0
        uncertain_identities_count = 0
        hardware_alerts_dispatched = 0
        reviewed_alerts_count = 0

        if supabase_db._client:
            try:
                # Observable events
                ev_res = supabase_db._client.table("behaviour_events").select("id, behaviour_type", count="exact").execute()
                observable_events_count = ev_res.count if ev_res.count is not None else 0

                # Unknown identities
                unk_res = supabase_db._client.table("behaviour_events").select("id", count="exact").eq("behaviour_type", "UNKNOWN_PERSON").execute()
                unknown_identities_count = unk_res.count if unk_res.count is not None else 0

                # Alerts
                al_res = supabase_db._client.table("alerts").select("id, severity, status", count="exact").eq("exam_id", exam_id).execute()
                if al_res.data:
                    alerts_count = len(al_res.data)
                    for a in al_res.data:
                        if a.get("severity") in ["CRITICAL", "HIGH"]:
                            critical_alerts_count += 1
                        if a.get("status") in ["REVIEWED", "ACKNOWLEDGED", "DISMISSED"]:
                            reviewed_alerts_count += 1

                # IoT Events (Hardware dispatches)
                iot_res = supabase_db._client.table("iot_events").select("id", count="exact").execute()
                hardware_alerts_dispatched = iot_res.count if iot_res.count is not None else 0

            except Exception as e:
                logger.error(f"Error computing exam summary from Supabase: {str(e)}")

        return {
            "exam_id": exam_id,
            "exam_name": exam["name"],
            "subject": exam["subject"],
            "date": exam["date"],
            "duration_minutes": exam["duration_minutes"],
            "room": exam["room"],
            "invigilator": exam["invigilator"],
            "status": exam["status"],
            "total_students_enrolled": len(roster),
            "camera_sources_count": 3,
            "observable_events_count": observable_events_count,
            "alerts_count": alerts_count,
            "critical_alerts_count": critical_alerts_count,
            "hardware_alerts_dispatched": hardware_alerts_dispatched,
            "unknown_identities_detected": unknown_identities_count,
            "uncertain_identities_detected": uncertain_identities_count,
            "reviewed_alerts_count": reviewed_alerts_count,
            "reporting_standard": "OBJECTIVE_OBSERVABLE_FACTS_ONLY"
        }


exam_service = ExamService()
