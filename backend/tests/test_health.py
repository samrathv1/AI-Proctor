def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "ai-proctor-backend"
    assert "version" in data
    assert "dependencies" in data
    assert "supabase" in data["dependencies"]
    assert "ai_engine" in data["dependencies"]
    assert "worker_queue" in data["dependencies"]
