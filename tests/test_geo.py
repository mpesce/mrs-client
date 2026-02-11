"""Tests for geospatial utilities."""

import math

import pytest

from mrs_client.geo import (
    haversine_distance,
    distance_to_sphere,
    point_in_sphere,
    spheres_intersect,
    search_sphere_intersects_registration,
    compute_bounding_box,
    format_distance,
)
from mrs_client.models import Location, Sphere


class TestHaversineDistance:
    """Tests for haversine distance calculation."""

    def test_same_point(self) -> None:
        loc = Location(lat=-33.8568, lon=151.2153)
        assert haversine_distance(loc, loc) == 0.0

    def test_known_distance(self) -> None:
        # Sydney Opera House to Sydney Harbour Bridge
        # Approximately 1.1 km
        opera_house = Location(lat=-33.8568, lon=151.2153)
        harbour_bridge = Location(lat=-33.8523, lon=151.2108)
        distance = haversine_distance(opera_house, harbour_bridge)
        # Should be roughly 650 meters
        assert 600 < distance < 700

    def test_long_distance(self) -> None:
        # Sydney to London - approximately 17,000 km
        sydney = Location(lat=-33.8688, lon=151.2093)
        london = Location(lat=51.5074, lon=-0.1278)
        distance = haversine_distance(sydney, london)
        # Should be roughly 17,000 km
        assert 16_000_000 < distance < 18_000_000

    def test_equator_to_pole(self) -> None:
        # Equator to North Pole - approximately 10,000 km
        equator = Location(lat=0.0, lon=0.0)
        north_pole = Location(lat=90.0, lon=0.0)
        distance = haversine_distance(equator, north_pole)
        # Should be roughly 10,000 km
        assert 9_900_000 < distance < 10_100_000


class TestPointInSphere:
    """Tests for point-in-sphere testing."""

    def test_point_at_center(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=100.0)
        assert point_in_sphere(center, sphere) is True

    def test_point_inside(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=1000.0)
        point = Location(lat=0.001, lon=0.001)  # Very close
        assert point_in_sphere(point, sphere) is True

    def test_point_outside(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=100.0)
        point = Location(lat=1.0, lon=1.0)  # About 157 km away
        assert point_in_sphere(point, sphere) is False

    def test_point_on_boundary(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=111_000.0)
        # Convert meters to degrees latitude using the same spherical Earth model
        # as haversine_distance, so this point lies on the boundary.
        lat_delta_deg = (sphere.radius / 6_371_000) * (180 / math.pi)
        point = Location(lat=lat_delta_deg, lon=0.0)
        assert point_in_sphere(point, sphere) is True


class TestSpheresIntersect:
    """Tests for sphere intersection."""

    def test_same_sphere(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=100.0)
        assert spheres_intersect(sphere, sphere) is True

    def test_overlapping_spheres(self) -> None:
        center1 = Location(lat=0.0, lon=0.0)
        center2 = Location(lat=0.0001, lon=0.0)  # About 11 meters apart
        sphere1 = Sphere(center=center1, radius=100.0)
        sphere2 = Sphere(center=center2, radius=100.0)
        assert spheres_intersect(sphere1, sphere2) is True

    def test_touching_spheres(self) -> None:
        # Two spheres that just touch (distance == sum of radii).
        center1 = Location(lat=0.0, lon=0.0)
        sphere1 = Sphere(center=center1, radius=100.0)
        sphere2 = Sphere(center=Location(lat=0.0, lon=0.0), radius=100.0)

        # Convert 200m center separation to latitude degrees using same Earth model.
        lat_delta_deg = ((sphere1.radius + sphere2.radius) / 6_371_000) * (180 / math.pi)
        center2 = Location(lat=lat_delta_deg, lon=0.0)
        sphere2 = Sphere(center=center2, radius=100.0)

        assert spheres_intersect(sphere1, sphere2) is True

    def test_non_overlapping_spheres(self) -> None:
        center1 = Location(lat=0.0, lon=0.0)
        center2 = Location(lat=1.0, lon=1.0)  # About 157 km apart
        sphere1 = Sphere(center=center1, radius=100.0)
        sphere2 = Sphere(center=center2, radius=100.0)
        assert spheres_intersect(sphere1, sphere2) is False


class TestDistanceToSphere:
    """Tests for distance to sphere calculation."""

    def test_point_inside_sphere(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=1000.0)
        point = Location(lat=0.001, lon=0.0)
        assert distance_to_sphere(point, sphere) == 0.0

    def test_point_outside_sphere(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        sphere = Sphere(center=center, radius=100.0)
        point = Location(lat=0.01, lon=0.0)  # About 1.1 km away
        distance = distance_to_sphere(point, sphere)
        # Should be distance to center minus radius
        assert distance > 0
        assert distance < 1200  # Less than distance to center


class TestSearchSphereIntersectsRegistration:
    """Tests for search intersection."""

    def test_point_query_inside(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        reg_sphere = Sphere(center=center, radius=100.0)
        query_point = Location(lat=0.0001, lon=0.0)
        assert search_sphere_intersects_registration(query_point, 0.0, reg_sphere) is True

    def test_point_query_outside(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        reg_sphere = Sphere(center=center, radius=100.0)
        query_point = Location(lat=1.0, lon=0.0)
        assert search_sphere_intersects_registration(query_point, 0.0, reg_sphere) is False

    def test_range_query_intersecting(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        reg_sphere = Sphere(center=center, radius=100.0)
        query_point = Location(lat=0.001, lon=0.0)  # About 111 meters away
        assert search_sphere_intersects_registration(query_point, 100.0, reg_sphere) is True

    def test_range_query_not_intersecting(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        reg_sphere = Sphere(center=center, radius=100.0)
        query_point = Location(lat=1.0, lon=0.0)  # About 111 km away
        assert search_sphere_intersects_registration(query_point, 100.0, reg_sphere) is False


class TestComputeBoundingBox:
    """Tests for bounding box computation."""

    def test_small_radius(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        min_lat, max_lat, min_lon, max_lon = compute_bounding_box(center, 1000.0)
        assert min_lat < 0.0 < max_lat
        assert min_lon < 0.0 < max_lon
        # Should be roughly symmetric
        assert abs(abs(min_lat) - abs(max_lat)) < 0.001
        assert abs(abs(min_lon) - abs(max_lon)) < 0.001

    def test_at_equator(self) -> None:
        center = Location(lat=0.0, lon=0.0)
        min_lat, max_lat, min_lon, max_lon = compute_bounding_box(center, 111_000.0)
        # At equator, 1 degree latitude ≈ 1 degree longitude in distance
        lat_range = max_lat - min_lat
        lon_range = max_lon - min_lon
        # Should be roughly equal at equator
        assert 0.8 < lat_range / lon_range < 1.2


class TestFormatDistance:
    """Tests for distance formatting."""

    def test_meters(self) -> None:
        assert format_distance(100.0) == "100.0m"
        assert format_distance(999.9) == "999.9m"

    def test_kilometers(self) -> None:
        assert format_distance(1000.0) == "1.00km"
        assert format_distance(1500.0) == "1.50km"
        assert format_distance(10000.0) == "10.00km"

    def test_zero(self) -> None:
        assert format_distance(0.0) == "0.0m"
