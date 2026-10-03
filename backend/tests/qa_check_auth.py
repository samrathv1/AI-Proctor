import urllib.request
import json

def post(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'dev-proctor-secret-key'
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))

def test_auth():
    print("=== 1. Non-institutional email rejection ===")
    status, body = post('http://127.0.0.1:8000/api/v1/students/register', {
        'name': 'Test User',
        'roll_number': 'TEST-999',
        'email': 'user@gmail.com',
        'password': 'Password123!',
        'department': 'Computer Engineering'
    })
    print(f"Status: {status}, Detail: {body.get('detail')}")
    assert status == 400
    assert "INSTITUTIONAL_EMAIL_REQUIRED" in str(body.get('detail'))

    print("\n=== 2. Invalid Login (wrong credentials) ===")
    status, body = post('http://127.0.0.1:8000/api/v1/students/login', {
        'identifier': 'dev.sharma@institution.edu',
        'password': 'wrongpassword'
    })
    print(f"Status: {status}, Detail: {body.get('detail')}")
    assert status == 401

    print("\n=== 3. Valid Student Login (Dev Sharma via email) ===")
    status, body = post('http://127.0.0.1:8000/api/v1/students/login', {
        'identifier': 'dev.sharma@institution.edu',
        'password': 'Password123!'
    })
    print(f"Status: {status}, Student: {body.get('name')}, Roll: {body.get('roll_number')}, Enrolled: {body.get('face_enrolled')}")
    assert status == 200
    assert body.get('name') == 'Dev Sharma'

    print("\n=== 4. Valid Student Login (via Roll Number) ===")
    status, body = post('http://127.0.0.1:8000/api/v1/students/login', {
        'identifier': 'CS-2026-042',
        'password': 'Password123!'
    })
    print(f"Status: {status}, Student: {body.get('name')}, Roll: {body.get('roll_number')}")
    assert status == 200

    print("\n=== 5. Non-existent student login ===")
    status, body = post('http://127.0.0.1:8000/api/v1/students/login', {
        'identifier': 'nonexistent@spit.ac.in',
        'password': 'Password123!'
    })
    print(f"Status: {status}, Detail: {body.get('detail')}")
    assert status == 404

    print("\nALL AUTH CHECKS PASSED!")

if __name__ == '__main__':
    test_auth()
