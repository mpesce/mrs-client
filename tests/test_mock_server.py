"""Tests for mock server."""

import pytest

from mrs_client.mock_server import MockServer, reset_mock_server


@pytest.fixture
def server() -> MockServer:
    """Get a fresh mock server for each test."""
    return reset_mock_server()


class TestMockServerAuth:
    """Tests for mock server authentication."""

    def test_default_user_exists(self, server: MockServer) -> None:
        assert "test@localhost" in server.users
        assert "test-token-12345" in server.tokens

    def test_authenticate_valid_token(self, server: MockServer) -> None:
        identity = server.authenticate("Bearer test-token-12345")
        assert identity == "test@localhost"

    def test_authenticate_invalid_token(self, server: MockServer) -> None:
        identity = server.authenticate("Bearer invalid-token")
        assert identity is None

    def test_authenticate_missing_header(self, server: MockServer) -> None:
        identity = server.authenticate(None)
        assert identity is None

    def test_add_user(self, server: MockServer) -> None:
        server.add_user("newuser@localhost", "new-token")
        identity = server.authenticate("Bearer new-token")
        assert identity == "newuser@localhost"


class TestMockServerWellKnown:
    """Tests for /.well-known/mrs endpoint."""

    def test_wellknown(self, server: MockServer) -> None:
        status, body = server.handle_request("GET", "/.well-known/mrs", None, {})
        assert status == 200
        assert body["mrs_version"] == "0.5.0"
        assert body["server"] == "http://localhost:8000"

    def test_wellknown_with_peers(self, server: MockServer) -> None:
        server.add_peer("https://peer.example.com", "Test peer")
        status, body = server.handle_request("GET", "/.well-known/mrs", None, {})
        assert status == 200
        assert len(body["known_peers"]) == 1
        assert body["known_peers"][0]["server"] == "https://peer.example.com"


class TestMockServerSearch:
    """Tests for /search endpoint."""

    def test_search_empty(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "POST", "/search",
            {"location": {"lat": 0.0, "lon": 0.0}, "range": 0.0},
            {}
        )
        assert status == 200
        assert body["status"] == "ok"
        assert body["results"] == []

    def test_search_with_results(self, server: MockServer) -> None:
        # Add a registration
        server.add_registration(
            lat=0.0, lon=0.0, radius=100.0,
            service_point="https://example.com/space"
        )

        status, body = server.handle_request(
            "POST", "/search",
            {"location": {"lat": 0.0, "lon": 0.0}, "range": 0.0},
            {}
        )
        assert status == 200
        assert len(body["results"]) == 1
        assert body["results"][0]["service_point"] == "https://example.com/space"

    def test_search_outside_range(self, server: MockServer) -> None:
        # Add a registration at origin
        server.add_registration(
            lat=0.0, lon=0.0, radius=100.0,
            service_point="https://example.com/space"
        )

        # Search far away
        status, body = server.handle_request(
            "POST", "/search",
            {"location": {"lat": 10.0, "lon": 10.0}, "range": 0.0},
            {}
        )
        assert status == 200
        assert len(body["results"]) == 0

    def test_search_with_range(self, server: MockServer) -> None:
        # Add a registration at origin
        server.add_registration(
            lat=0.0, lon=0.0, radius=100.0,
            service_point="https://example.com/space"
        )

        # Search nearby with range
        status, body = server.handle_request(
            "POST", "/search",
            {"location": {"lat": 0.001, "lon": 0.0}, "range": 200.0},
            {}
        )
        assert status == 200
        assert len(body["results"]) == 1


class TestMockServerRegister:
    """Tests for /register endpoint."""

    def test_register_requires_auth(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "POST", "/register",
            {
                "space": {"type": "sphere", "center": {"lat": 0.0, "lon": 0.0}, "radius": 50.0},
                "service_point": "https://example.com/space",
                "foad": False,
            },
            {}
        )
        assert status == 401

    def test_register_success(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "POST", "/register",
            {
                "space": {"type": "sphere", "center": {"lat": 0.0, "lon": 0.0}, "radius": 50.0},
                "service_point": "https://example.com/space",
                "foad": False,
            },
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 201
        assert body["status"] == "registered"
        assert "registration" in body
        assert body["registration"]["id"].startswith("reg_")

    def test_register_foad(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "POST", "/register",
            {
                "space": {"type": "sphere", "center": {"lat": 0.0, "lon": 0.0}, "radius": 50.0},
                "foad": True,
            },
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 201
        assert body["registration"]["foad"] is True

    def test_register_missing_service_point(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "POST", "/register",
            {
                "space": {"type": "sphere", "center": {"lat": 0.0, "lon": 0.0}, "radius": 50.0},
                "foad": False,
            },
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 400
        assert "service_point" in body["message"]

    def test_register_invalid_radius(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "POST", "/register",
            {
                "space": {"type": "sphere", "center": {"lat": 0.0, "lon": 0.0}, "radius": -50.0},
                "service_point": "https://example.com/space",
                "foad": False,
            },
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 400


class TestMockServerRelease:
    """Tests for /release endpoint."""

    def test_release_requires_auth(self, server: MockServer) -> None:
        reg_id = server.add_registration(lat=0.0, lon=0.0, radius=50.0, service_point="https://example.com")
        status, body = server.handle_request(
            "POST", "/release",
            {"id": reg_id},
            {}
        )
        assert status == 401

    def test_release_success(self, server: MockServer) -> None:
        reg_id = server.add_registration(lat=0.0, lon=0.0, radius=50.0, service_point="https://example.com")
        status, body = server.handle_request(
            "POST", "/release",
            {"id": reg_id},
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 200
        assert body["status"] == "released"
        assert reg_id not in server.registrations

    def test_release_not_found(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "POST", "/release",
            {"id": "reg_nonexistent"},
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 404

    def test_release_not_owner(self, server: MockServer) -> None:
        # Add registration owned by different user
        reg_id = server.add_registration(
            lat=0.0, lon=0.0, radius=50.0,
            service_point="https://example.com",
            owner="other@localhost"
        )
        status, body = server.handle_request(
            "POST", "/release",
            {"id": reg_id},
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 403


class TestMockServerList:
    """Tests for /registrations endpoint."""

    def test_list_requires_auth(self, server: MockServer) -> None:
        status, body = server.handle_request("GET", "/registrations", None, {})
        assert status == 401

    def test_list_empty(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "GET", "/registrations", None,
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 200
        assert body["registrations"] == []
        assert body["total"] == 0

    def test_list_with_registrations(self, server: MockServer) -> None:
        server.add_registration(lat=0.0, lon=0.0, radius=50.0, service_point="https://example.com/1")
        server.add_registration(lat=1.0, lon=1.0, radius=50.0, service_point="https://example.com/2")

        status, body = server.handle_request(
            "GET", "/registrations", None,
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 200
        assert len(body["registrations"]) == 2
        assert body["total"] == 2

    def test_list_only_own_registrations(self, server: MockServer) -> None:
        server.add_registration(lat=0.0, lon=0.0, radius=50.0, service_point="https://example.com/1")
        server.add_registration(
            lat=1.0, lon=1.0, radius=50.0,
            service_point="https://example.com/2",
            owner="other@localhost"
        )

        status, body = server.handle_request(
            "GET", "/registrations", None,
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 200
        assert len(body["registrations"]) == 1


class TestMockServerAuthMe:
    """Tests for /auth/me endpoint."""

    def test_auth_me_requires_auth(self, server: MockServer) -> None:
        status, body = server.handle_request("GET", "/auth/me", None, {})
        assert status == 401

    def test_auth_me_success(self, server: MockServer) -> None:
        status, body = server.handle_request(
            "GET", "/auth/me", None,
            {"Authorization": "Bearer test-token-12345"}
        )
        assert status == 200
        assert body["id"] == "test@localhost"
        assert body["can_register"] is True
