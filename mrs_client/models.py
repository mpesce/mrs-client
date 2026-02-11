"""Data models for MRS client."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from mrs_client.validation import sanitize_service_point_uri


@dataclass
class Location:
    """A point in 3D space using WGS84 coordinates."""

    lat: float
    lon: float
    ele: float = 0.0

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat <= 90.0:
            raise ValueError(f"Latitude must be between -90 and 90, got {self.lat}")
        if not -180.0 <= self.lon <= 180.0:
            raise ValueError(f"Longitude must be between -180 and 180, got {self.lon}")

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {"lat": self.lat, "lon": self.lon, "ele": self.ele}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Location:
        """Create from dictionary."""
        return cls(
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            ele=float(data.get("ele", 0.0)),
        )


@dataclass
class Sphere:
    """A spherical space definition."""

    center: Location
    radius: float  # meters

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError(f"Radius must be positive, got {self.radius}")
        if self.radius > 1_000_000:
            raise ValueError(f"Radius must be <= 1,000,000 meters, got {self.radius}")

    @property
    def type(self) -> str:
        return "sphere"

    def volume(self) -> float:
        """Compute volume in cubic meters."""
        return (4 / 3) * math.pi * (self.radius**3)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": "sphere",
            "center": self.center.to_dict(),
            "radius": self.radius,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Sphere:
        """Create from dictionary."""
        return cls(
            center=Location.from_dict(data["center"]),
            radius=float(data["radius"]),
        )


# Type alias for space geometries (sphere only for now)
Space = Sphere


@dataclass
class Registration:
    """A registration binding a space to a service point."""

    id: str
    space: Space
    foad: bool
    owner: str
    created: datetime
    updated: datetime
    origin_server: str | None = None
    origin_id: str | None = None
    version: int = 1
    service_point: str | None = None
    distance: float | None = None  # Populated in search results

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {
            "id": self.id,
            "space": self.space.to_dict(),
            "foad": self.foad,
            "owner": self.owner,
            "created": self.created.isoformat(),
            "updated": self.updated.isoformat(),
            "version": self.version,
        }
        if self.origin_server is not None:
            result["origin_server"] = self.origin_server
        if self.origin_id is not None:
            result["origin_id"] = self.origin_id
        if self.service_point:
            result["service_point"] = self.service_point
        if self.distance is not None:
            result["distance"] = self.distance
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Registration:
        """Create from dictionary."""
        space_data = data["space"]
        if space_data.get("type") == "sphere":
            space = Sphere.from_dict(space_data)
        else:
            raise ValueError(f"Unsupported space type: {space_data.get('type')}")

        # Parse datetime - handle both ISO format and already-parsed
        created = data["created"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created.replace("Z", "+00:00"))
        updated = data["updated"]
        if isinstance(updated, str):
            updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))

        return cls(
            id=data["id"],
            space=space,
            service_point=sanitize_service_point_uri(data.get("service_point")),
            foad=bool(data.get("foad", False)),
            owner=data["owner"],
            created=created,
            updated=updated,
            origin_server=data.get("origin_server"),
            origin_id=data.get("origin_id"),
            version=int(data.get("version", 1)),
            distance=data.get("distance"),
        )


@dataclass
class Referral:
    """A referral to another MRS server."""

    server: str
    hint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, Any] = {"server": self.server}
        if self.hint:
            result["hint"] = self.hint
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Referral:
        """Create from dictionary."""
        return cls(
            server=data["server"],
            hint=data.get("hint"),
        )


@dataclass
class SearchResult:
    """Result of a search operation."""

    results: list[Registration]
    servers_queried: list[str]
    referrals_followed: int
    total_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "results": [r.to_dict() for r in self.results],
            "servers_queried": self.servers_queried,
            "referrals_followed": self.referrals_followed,
            "total_time_ms": self.total_time_ms,
        }


@dataclass
class Identity:
    """An MRS identity with cryptographic keys."""

    id: str  # user@domain
    public_key: bytes
    key_id: str
    private_key: bytes | None = None  # None for remote identities

    @property
    def username(self) -> str:
        """Extract username from identity."""
        return self.id.split("@")[0]

    @property
    def domain(self) -> str:
        """Extract domain from identity."""
        return self.id.split("@")[1]


@dataclass
class ServerInfo:
    """Information about an MRS server."""

    url: str
    mrs_version: str
    operator: str | None = None
    authoritative_regions: list[Space] = field(default_factory=list)
    known_peers: list[Referral] = field(default_factory=list)
    capabilities: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any], url: str) -> ServerInfo:
        """Create from dictionary."""
        regions = []
        for region_data in data.get("authoritative_regions", []):
            if region_data.get("type") == "sphere":
                regions.append(Sphere.from_dict(region_data))

        peers = [Referral.from_dict(p) for p in data.get("known_peers", [])]

        return cls(
            url=url,
            mrs_version=data.get("mrs_version", "unknown"),
            operator=data.get("operator"),
            authoritative_regions=regions,
            known_peers=peers,
            capabilities=data.get("capabilities", {}),
        )
