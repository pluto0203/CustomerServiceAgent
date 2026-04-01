from app.services.webtools.client import WebToolsService


def test_private_network_hosts_are_blocked() -> None:
    service = WebToolsService()

    assert service._is_url_allowed("http://127.0.0.1/internal") is False
    assert service._is_url_allowed("http://localhost:8000/health") is False


def test_invalid_scheme_is_blocked() -> None:
    service = WebToolsService()

    assert service._is_url_allowed("file:///etc/passwd") is False
    assert service._is_url_allowed("ftp://example.com/resource") is False
