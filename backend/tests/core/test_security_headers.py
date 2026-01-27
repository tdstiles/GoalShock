
import pytest
from fastapi.testclient import TestClient
from backend.main_realtime import app

client = TestClient(app)

def test_security_headers_present():
    """
    Verify that security headers are present in the response.
    """
    response = client.get("/")
    assert response.status_code == 200

    headers = response.headers

    # Check for presence and correct values of security headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["X-XSS-Protection"] == "1; mode=block"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    csp = headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "cdn.jsdelivr.net" in csp
    assert "frame-ancestors 'none'" in csp

def test_cors_headers_still_present():
    """
    Verify that CORS headers are still present (middleware didn't break them).
    """
    # Simulate a cross-origin request
    response = client.get(
        "/",
        headers={"Origin": "http://localhost:3000"}
    )
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
