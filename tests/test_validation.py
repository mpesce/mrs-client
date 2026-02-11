"""Tests for strict URI validation policy."""

from mrs_client.validation import sanitize_service_point_uri, validate_service_point_uri


def test_validate_accepts_https_uri() -> None:
    uri = "https://example.com/spaces/opera-house"
    assert validate_service_point_uri(uri) == uri


def test_validate_rejects_non_https_scheme() -> None:
    try:
        validate_service_point_uri("javascript:alert(1)")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "scheme" in str(e)


def test_validate_rejects_fragment() -> None:
    try:
        validate_service_point_uri("https://example.com/x#prompt")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "fragment" in str(e)


def test_validate_rejects_whitespace() -> None:
    try:
        validate_service_point_uri("https://example.com/ bad")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "whitespace" in str(e)


def test_sanitize_returns_none_for_invalid_uri() -> None:
    assert sanitize_service_point_uri("javascript:alert(1)") is None
