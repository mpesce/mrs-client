"""Tests for data models."""

import pytest
from datetime import datetime, timezone

from mrs_client.models import (
    Location,
    Sphere,
    Registration,
    Referral,
    SearchResult,
    ServerInfo,
)


class TestLocation:
    """Tests for Location model."""

    def test_valid_location(self) -> None:
        loc = Location(lat=-33.8568, lon=151.2153, ele=10.0)
        assert loc.lat == -33.8568
        assert loc.lon == 151.2153
        assert loc.ele == 10.0

    def test_default_elevation(self) -> None:
        loc = Location(lat=0.0, lon=0.0)
        assert loc.ele == 0.0

    def test_invalid_latitude_high(self) -> None:
        with pytest.raises(ValueError, match="Latitude"):
            Location(lat=91.0, lon=0.0)

    def test_invalid_latitude_low(self) -> None:
        with pytest.raises(ValueError, match="Latitude"):
            Location(lat=-91.0, lon=0.0)

    def test_invalid_longitude_high(self) -> None:
        with pytest.raises(ValueError, match="Longitude"):
            Location(lat=0.0, lon=181.0)

    def test_invalid_longitude_low(self) -> None:
        with pytest.raises(ValueError, match="Longitude"):
            Location(lat=0.0, lon=-181.0)

    def test_to_dict(self) -> None:
        loc = Location(lat=-33.8568, lon=151.2153, ele=10.0)
        d = loc.to_dict()
        assert d == {"lat": -33.8568, "lon": 151.2153, "ele": 10.0}

    def test_from_dict(self) -> None:
        d = {"lat": -33.8568, "lon": 151.2153, "ele": 10.0}
        loc = Location.from_dict(d)
        assert loc.lat == -33.8568
        assert loc.lon == 151.2153
        assert loc.ele == 10.0

    def test_from_dict_default_elevation(self) -> None:
        d = {"lat": -33.8568, "lon": 151.2153}
        loc = Location.from_dict(d)
        assert loc.ele == 0.0


class TestSphere:
    """Tests for Sphere model."""

    def test_valid_sphere(self) -> None:
        center = Location(lat=-33.8568, lon=151.2153)
        sphere = Sphere(center=center, radius=50.0)
        assert sphere.center == center
        assert sphere.radius == 50.0
        assert sphere.type == "sphere"

    def test_invalid_radius_zero(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        with pytest.raises(ValueError, match="positive"):
            Sphere(center=center, radius=0.0)

    def test_invalid_radius_negative(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        with pytest.raises(ValueError, match="positive"):
            Sphere(center=center, radius=-10.0)

    def test_invalid_radius_too_large(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        with pytest.raises(ValueError, match="1,000,000"):
            Sphere(center=center, radius=1_000_001.0)

    def test_volume(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=100.0)
        # Volume = (4/3) * pi * r^3
        expected = (4 / 3) * 3.14159265359 * (100.0 ** 3)
        assert abs(sphere.volume() - expected) < 1000  # Allow small error

    def test_to_dict(self) -> None:
        center = Location(lat=-33.8568, lon=151.2153, ele=10.0)
        sphere = Sphere(center=center, radius=50.0)
        d = sphere.to_dict()
        assert d == {
            "type": "sphere",
            "center": {"lat": -33.8568, "lon": 151.2153, "ele": 10.0},
            "radius": 50.0,
        }

    def test_from_dict(self) -> None:
        d = {
            "type": "sphere",
            "center": {"lat": -33.8568, "lon": 151.2153, "ele": 10.0},
            "radius": 50.0,
        }
        sphere = Sphere.from_dict(d)
        assert sphere.center.lat == -33.8568
        assert sphere.radius == 50.0


class TestRegistration:
    """Tests for Registration model."""

    def test_registration_with_service_point(self) -> None:
        space = Sphere(center=Location(lat=0.0, lon=0.0), radius=50.0)
        now = datetime.now(timezone.utc)
        reg = Registration(
            id="reg_abc123",
            space=space,
            service_point="https://example.com/space",
            foad=False,
            owner="test@example.com",
            created=now,
            updated=now,
        )
        assert reg.id == "reg_abc123"
        assert reg.service_point == "https://example.com/space"
        assert reg.foad is False

    def test_registration_foad(self) -> None:
        space = Sphere(center=Location(lat=0.0, lon=0.0), radius=50.0)
        now = datetime.now(timezone.utc)
        reg = Registration(
            id="reg_abc123",
            space=space,
            foad=True,
            owner="test@example.com",
            created=now,
            updated=now,
        )
        assert reg.foad is True
        assert reg.service_point is None

    def test_to_dict(self) -> None:
        space = Sphere(center=Location(lat=0.0, lon=0.0), radius=50.0)
        now = datetime.now(timezone.utc)
        reg = Registration(
            id="reg_abc123",
            space=space,
            service_point="https://example.com/space",
            foad=False,
            owner="test@example.com",
            created=now,
            updated=now,
            distance=12.5,
        )
        d = reg.to_dict()
        assert d["id"] == "reg_abc123"
        assert d["service_point"] == "https://example.com/space"
        assert d["distance"] == 12.5

    def test_from_dict(self) -> None:
        d = {
            "id": "reg_abc123",
            "space": {
                "type": "sphere",
                "center": {"lat": 0.0, "lon": 0.0, "ele": 0.0},
                "radius": 50.0,
            },
            "service_point": "https://example.com/space",
            "foad": False,
            "owner": "test@example.com",
            "created": "2026-01-15T10:30:00Z",
            "updated": "2026-01-15T10:30:00Z",
            "distance": 12.5,
        }
        reg = Registration.from_dict(d)
        assert reg.id == "reg_abc123"
        assert reg.distance == 12.5


class TestReferral:
    """Tests for Referral model."""

    def test_referral_with_hint(self) -> None:
        ref = Referral(server="https://example.com", hint="Test server")
        assert ref.server == "https://example.com"
        assert ref.hint == "Test server"

    def test_referral_without_hint(self) -> None:
        ref = Referral(server="https://example.com")
        assert ref.hint is None

    def test_to_dict_with_hint(self) -> None:
        ref = Referral(server="https://example.com", hint="Test server")
        d = ref.to_dict()
        assert d == {"server": "https://example.com", "hint": "Test server"}

    def test_to_dict_without_hint(self) -> None:
        ref = Referral(server="https://example.com")
        d = ref.to_dict()
        assert d == {"server": "https://example.com"}


class TestSearchResult:
    """Tests for SearchResult model."""

    def test_search_result(self) -> None:
        result = SearchResult(
            results=[],
            servers_queried=["https://server1.com", "https://server2.com"],
            referrals_followed=1,
            total_time_ms=125.5,
        )
        assert len(result.results) == 0
        assert len(result.servers_queried) == 2
        assert result.referrals_followed == 1
        assert result.total_time_ms == 125.5


class TestServerInfo:
    """Tests for ServerInfo model."""

    def test_from_dict(self) -> None:
        d = {
            "mrs_version": "0.5.0",
            "operator": "admin@example.com",
            "authoritative_regions": [],
            "known_peers": [
                {"server": "https://peer.example.com", "hint": "Peer server"}
            ],
            "capabilities": {"geometry_types": ["sphere"], "max_radius": 1000000},
        }
        info = ServerInfo.from_dict(d, "https://example.com")
        assert info.url == "https://example.com"
        assert info.mrs_version == "0.5.0"
        assert info.operator == "admin@example.com"
        assert len(info.known_peers) == 1
        assert info.known_peers[0].server == "https://peer.example.com"
