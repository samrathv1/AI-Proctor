import urllib.request
import json
import ssl

SUPABASE_URL = "https://wxsodwupyieseegvniuq.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind4c29kd3VweWllc2VlZ3ZuaXVxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MDc2NTc4MCwiZXhwIjoyMTA2MzQxNzgwfQ.ajxW-Mq23qDDwhSKeLJXO5zzI3F6PDST72QH3cH7Tfs"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind4c29kd3VweWllc2VlZ3ZuaXVxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA3NjU3ODAsImV4cCI6MjEwNjM0MTc4MH0.XHqfDWRqJ433SYPCaNTq7CbAIVwB5ASs9lC0Vc-F3Lo"

headers = {
    "apikey": SERVICE_KEY,
    "Authorization": f"Bearer {SERVICE_KEY}"
}

anon_headers = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}"
}

def inspect():
    print("=== INSPECTING SUPABASE PROJECT: wxsodwupyieseegvniuq ===")
    
    # 1. PostgREST OpenAPI Schema (exposes public tables, columns, constraints)
    req_schema = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/", headers=headers)
    try:
        with urllib.request.urlopen(req_schema) as res:
            openapi = json.loads(res.read().decode())
            definitions = openapi.get("definitions", {})
            paths = openapi.get("paths", {})
            print(f"\n1. POSTGREST EXPOSED TABLES: {len(definitions)} found")
            for t_name in sorted(definitions.keys()):
                t_def = definitions[t_name]
                props = t_def.get("properties", {})
                req_cols = t_def.get("required", [])
                print(f"  - Table: {t_name}")
                for col_name, col_info in props.items():
                    col_type = col_info.get("type", "unknown")
                    col_format = col_info.get("format", "")
                    col_desc = col_info.get("description", "")
                    is_req = "*" if col_name in req_cols else ""
                    print(f"      {col_name}{is_req}: {col_type} ({col_format}) {col_desc}")
    except Exception as e:
        print("Error fetching OpenAPI schema:", e)

    # 2. Known AI-Proctor tables test read with Service Role & Anon Key
    known_tables = [
        "profiles",
        "students",
        "student_face_profiles",
        "exam_sessions",
        "exam_students",
        "cameras",
        "alerts",
        "iot_devices",
        "iot_events",
        "audit_logs"
    ]
    print("\n2. QUERYING KNOWN TABLES (ROW COUNT & RLS):")
    for tbl in known_tables:
        url = f"{SUPABASE_URL}/rest/v1/{tbl}?select=count"
        # Service role check
        req_srv = urllib.request.Request(url, headers={**headers, "Prefer": "count=exact"})
        srv_status = ""
        srv_count = None
        try:
            with urllib.request.urlopen(req_srv) as r:
                content_range = r.headers.get("Content-Range", "")
                srv_count = content_range.split("/")[-1] if "/" in content_range else "0"
                srv_status = f"EXISTS (Count: {srv_count})"
        except urllib.error.HTTPError as e:
            srv_status = f"MISSING / HTTP {e.code}: {e.read().decode()[:80]}"
        except Exception as e:
            srv_status = f"ERROR: {e}"

        # Anon check (tests RLS)
        req_anon = urllib.request.Request(url, headers={**anon_headers, "Prefer": "count=exact"})
        anon_status = ""
        try:
            with urllib.request.urlopen(req_anon) as r:
                content_range = r.headers.get("Content-Range", "")
                cnt = content_range.split("/")[-1] if "/" in content_range else "0"
                anon_status = f"Accessible to Anon (Count: {cnt})"
        except urllib.error.HTTPError as e:
            anon_status = f"RLS Restricted / HTTP {e.code}"
        except Exception as e:
            anon_status = f"Anon Error: {e}"

        print(f"  - {tbl:22}: Service Role -> {srv_status} | Anon -> {anon_status}")

    # 3. Storage Buckets
    print("\n3. STORAGE BUCKETS:")
    req_buckets = urllib.request.Request(f"{SUPABASE_URL}/storage/v1/bucket", headers=headers)
    try:
        with urllib.request.urlopen(req_buckets) as res:
            buckets = json.loads(res.read().decode())
            print(f"  Total Buckets: {len(buckets)}")
            for b in buckets:
                print(f"  - Bucket: {b.get('id')} | Name: {b.get('name')} | Public: {b.get('public')}")
    except Exception as e:
        print("  Error fetching storage buckets:", e)

    # 4. Auth Users
    print("\n4. AUTHENTICATION (USERS):")
    req_auth = urllib.request.Request(f"{SUPABASE_URL}/auth/v1/admin/users", headers=headers)
    try:
        with urllib.request.urlopen(req_auth) as res:
            auth_data = json.loads(res.read().decode())
            users = auth_data.get("users", [])
            print(f"  Total Auth Users: {len(users)}")
            for u in users:
                print(f"  - User ID: {u.get('id')} | Email: {u.get('email')} | Role: {u.get('role')} | Created: {u.get('created_at')}")
    except Exception as e:
        print("  Error fetching auth users:", e)

if __name__ == "__main__":
    inspect()
