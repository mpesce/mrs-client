"""Geospatial utilities for MRS client."""

from __future__ import annotations

import math

from mrs_client.models import Location, Sphere

# Earth radius in meters (WGS84 mean radius)
EARTH_RADIUS_M = 6_371_000


def haversine_distance(loc1: Location, loc2: Location) -> float:
    """Calculate distance in meters between two points using Haversine formula.

    Args:
        loc1: First location
        loc2: Second location

    Returns:
        Distance in meters
    """
    lat1, lon1 = math.radians(loc1.lat), math.radians(loc1.lon)
    lat2, lon2 = math.radians(loc2.lat), math.radians(loc2.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return EARTH_RADIUS_M * c


def distance_to_sphere(point: Location, sphere: Sphere) -> float:
    """Calculate distance from a point to a sphere's boundary.

    Returns 0 if the point is inside the sphere.
    Returns the distance to the sphere's surface if outside.

    Args:
        point: Query point
        sphere: Sphere to measure distance to

    Returns:
        Distance in meters (0 if inside sphere)
    """
    distance_to_center = haversine_distance(point, sphere.center)
    if distance_to_center <= sphere.radius:
        return 0.0
    return distance_to_center - sphere.radius


def point_in_sphere(point: Location, sphere: Sphere) -> bool:
    """Check if a point is inside a sphere.

    Args:
        point: Point to check
        sphere: Sphere to check against

    Returns:
        True if point is inside sphere
    """
    return haversine_distance(point, sphere.center) <= sphere.radius


def spheres_intersect(sphere1: Sphere, sphere2: Sphere) -> bool:
    """Check if two spheres intersect.

    Args:
        sphere1: First sphere
        sphere2: Second sphere

    Returns:
        True if spheres intersect
    """
    distance = haversine_distance(sphere1.center, sphere2.center)
    return distance <= (sphere1.radius + sphere2.radius)


def search_sphere_intersects_registration(
    query_center: Location,
    query_range: float,
    registration_sphere: Sphere,
) -> bool:
    """Check if a search sphere intersects a registration sphere.

    Args:
        query_center: Center of search
        query_range: Search radius in meters
        registration_sphere: Registered space sphere

    Returns:
        True if search intersects registration
    """
    if query_range == 0:
        # Point query - check if point is in registration sphere
        return point_in_sphere(query_center, registration_sphere)

    # Range query - check if spheres intersect
    query_sphere = Sphere(center=query_center, radius=query_range)
    return spheres_intersect(query_sphere, registration_sphere)


def compute_bounding_box(
    center: Location, radius: float
) -> tuple[float, float, float, float]:
    """Compute lat/lon bounding box for a sphere.

    Args:
        center: Center of sphere
        radius: Radius in meters

    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    # Convert radius in meters to degrees (approximate)
    lat_delta = radius / EARTH_RADIUS_M * (180 / math.pi)
    # Longitude delta depends on latitude
    lon_delta = lat_delta / math.cos(math.radians(center.lat))

    return (
        center.lat - lat_delta,
        center.lat + lat_delta,
        center.lon - lon_delta,
        center.lon + lon_delta,
    )


def format_distance(meters: float) -> str:
    """Format a distance for human display.

    Args:
        meters: Distance in meters

    Returns:
        Human-readable string like "12.5m" or "2.3km"
    """
    if meters < 1000:
        return f"{meters:.1f}m"
    return f"{meters / 1000:.2f}km"
