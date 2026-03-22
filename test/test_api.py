from fastapi.testclient import TestClient

def test_get_info(api_client: TestClient):
    response = api_client.get("/api/info")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "env" in data

def test_add_entry_via_api(api_client: TestClient):
    payload = {
        "title": "API Apple",
        "kcal": 100,
        "fat_g": 0.5,
        "carbs_g": 20,
        "protein_g": 1.0,
        "serving_amount": 1,
        "confidence": 0.7,
        "entry_date": "2023-01-02",
        "entry_time": "12:00:00"
    }
    
    response = api_client.post("/api/entries", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["title"] == "API Apple"
    assert "id" in data
