def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unknown_route_returns_structured_404(client):
    response = client.get("/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "http_404",
            "message": "Not Found",
        }
    }


def test_health_rejects_unsupported_method(client):
    response = client.post("/health")

    assert response.status_code == 405
    assert response.json() == {
        "error": {
            "code": "http_405",
            "message": "Method Not Allowed",
        }
    }
