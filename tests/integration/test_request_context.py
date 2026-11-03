import re


def test_requests_receive_unique_traceable_request_ids(client):
    first = client.get("/health")
    second = client.get("/health")

    first_id = first.headers["X-Request-ID"]
    second_id = second.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", first_id)
    assert re.fullmatch(r"[0-9a-f]{32}", second_id)
    assert first_id != second_id
