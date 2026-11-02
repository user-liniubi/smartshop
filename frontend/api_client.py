import os
from typing import Any

import httpx


class ApiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ApiClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = 30,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("SMARTSHOP_API_URL") or "http://127.0.0.1:8000"
        ).rstrip("/")
        self.token = token
        self.timeout = timeout

    def login(self, username: str, password: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/auth/login",
            json={"username": username, "password": password},
            include_auth=False,
        )

    def create_session(self) -> dict[str, Any]:
        return self._request("POST", "/chat/sessions")

    def list_sessions(self) -> list[dict[str, Any]]:
        return self._request("GET", "/chat/sessions")

    def get_messages(self, session_id: int) -> list[dict[str, Any]]:
        return self._request("GET", f"/chat/sessions/{session_id}/messages")

    def get_order_by_number(self, order_no: str) -> dict[str, Any]:
        return self._request("GET", f"/orders/by-number/{order_no}")

    def send_message(self, session_id: int, content: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/chat/sessions/{session_id}/messages",
            json={"content": content},
            timeout=120,
        )

    def request_handoff(self, session_id: int, reason: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/chat/sessions/{session_id}/handoff",
            json={"reason": reason},
        )

    def list_pending_handoffs(self) -> list[dict[str, Any]]:
        return self._request("GET", "/agent/handoffs")

    def list_my_handoffs(self) -> list[dict[str, Any]]:
        return self._request("GET", "/agent/handoffs/mine")

    def claim_handoff(self, handoff_id: int) -> dict[str, Any]:
        return self._request("POST", f"/agent/handoffs/{handoff_id}/claim")

    def get_agent_session(self, session_id: int) -> dict[str, Any]:
        return self._request("GET", f"/agent/sessions/{session_id}")

    def reply_as_agent(self, session_id: int, content: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/agent/sessions/{session_id}/reply",
            json={"content": content},
        )

    def close_agent_session(self, session_id: int) -> dict[str, Any]:
        return self._request("POST", f"/agent/sessions/{session_id}/close")

    def _request(
        self,
        method: str,
        path: str,
        *,
        include_auth: bool = True,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> Any:
        headers = kwargs.pop("headers", {})
        if include_auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=timeout or self.timeout,
            ) as client:
                response = client.request(
                    method,
                    path,
                    headers=headers,
                    **kwargs,
                )
        except httpx.HTTPError:
            raise ApiError("无法连接智能客服服务，请确认后端已经启动") from None

        if response.is_success:
            return response.json()

        try:
            error = response.json().get("error", {})
        except ValueError:
            error = {}
        raise ApiError(
            error.get("message") or "请求失败，请稍后重试",
            status_code=response.status_code,
            code=error.get("code"),
        )
