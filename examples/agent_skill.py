#!/usr/bin/env python3
"""Example MRS skill for AI agent integration.

This shows how to wrap MRS client for use as an agent tool/skill.
"""

import json
from mrs_client import MRSClient


# Singleton client for reuse
_client: MRSClient | None = None


def get_client() -> MRSClient:
    """Get or create the MRS client."""
    global _client
    if _client is None:
        _client = MRSClient()
    return _client


def mrs_search(latitude: float, longitude: float, range_meters: float = 100) -> str:
    """Search for spatial metadata at a location.

    Use this when you need to know what services, permissions,
    or metadata are associated with a physical location.

    Args:
        latitude: Latitude in degrees (-90 to 90)
        longitude: Longitude in degrees (-180 to 180)
        range_meters: Search radius in meters (default: 100)

    Returns:
        JSON string with registrations found at the location
    """
    client = get_client()

    try:
        result = client.search_sync(
            lat=latitude,
            lon=longitude,
            range_meters=range_meters,
        )

        registrations = []
        for reg in result.results:
            entry = {
                "id": reg.id,
                "distance_meters": reg.distance,
                "radius_meters": reg.space.radius,
            }
            if reg.foad:
                entry["foad"] = True
                entry["note"] = "Space declines to provide services"
            else:
                entry["service_point"] = reg.service_point

            registrations.append(entry)

        return json.dumps({
            "status": "ok",
            "location": {"lat": latitude, "lon": longitude},
            "range_meters": range_meters,
            "count": len(registrations),
            "registrations": registrations,
            "servers_queried": result.servers_queried,
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
        })


def mrs_info(server: str | None = None) -> str:
    """Get information about an MRS server.

    Args:
        server: Server URL (optional, uses default if not specified)

    Returns:
        JSON string with server information
    """
    client = get_client()

    try:
        info = client.get_server_info_sync(server=server)

        return json.dumps({
            "status": "ok",
            "server": info.url,
            "mrs_version": info.mrs_version,
            "operator": info.operator,
            "known_peers": [p.server for p in info.known_peers],
            "capabilities": info.capabilities,
        }, indent=2)

    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
        })


# Tool definitions for various agent frameworks

# Claude tool definition
CLAUDE_MRS_SEARCH_TOOL = {
    "name": "mrs_search",
    "description": (
        "Search for services and metadata registered at a physical location "
        "using the Mixed Reality Service protocol. Use this when you need to "
        "know what's at a specific place - services, permissions, capabilities, "
        "or whether a space declines interaction (FOAD)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "latitude": {
                "type": "number",
                "description": "Latitude in degrees (-90 to 90)",
            },
            "longitude": {
                "type": "number",
                "description": "Longitude in degrees (-180 to 180)",
            },
            "range_meters": {
                "type": "number",
                "description": "Search radius in meters (default: 100)",
            },
        },
        "required": ["latitude", "longitude"],
    },
}


if __name__ == "__main__":
    # Demo the skill
    print("MRS Search Demo")
    print("=" * 40)

    # Search near Sydney Opera House
    print("\nSearching near Sydney Opera House...")
    result = mrs_search(-33.8568, 151.2153)
    print(result)

    # Get server info
    print("\n" + "=" * 40)
    print("\nGetting server info...")
    info = mrs_info()
    print(info)
