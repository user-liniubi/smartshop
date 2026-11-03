from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.core.exceptions import AppError, register_exception_handlers


def create_error_test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/validation")
    async def validation_endpoint(limit: int) -> dict[str, int]:
        return {"limit": limit}

    @app.get("/expected-error")
    async def expected_error_endpoint() -> None:
        raise AppError(
            status_code=409,
            code="handoff_conflict",
            message="该会话已被接管",
        )

    @app.get("/unexpected-error")
    async def unexpected_error_endpoint() -> None:
        raise RuntimeError("sensitive internal detail")

    return app


def test_validation_error_uses_common_error_format():
    with TestClient(create_error_test_app()) as client:
        response = client.get("/validation")

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "请求参数校验失败"
    assert body["error"]["details"][0]["loc"] == ["query", "limit"]


def test_expected_application_error_preserves_status_and_code():
    with TestClient(create_error_test_app()) as client:
        response = client.get("/expected-error")

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "handoff_conflict",
            "message": "该会话已被接管",
        }
    }


def test_unhandled_error_does_not_leak_internal_details():
    app = create_error_test_app()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "internal_server_error",
            "message": "服务暂时不可用",
        }
    }
    assert "sensitive internal detail" not in response.text
