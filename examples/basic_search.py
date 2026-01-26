#!/usr/bin/env python3
"""Basic MRS search example."""

import asyncio
from mrs_client import MRSClient


def search_sync() -> None:
    """Synchronous search example."""
    print("=== Synchronous Search ===")

    client = MRSClient(verbose=True)

    # Search near Sydney Opera House
    result = client.search_sync(
        lat=-33.8568,
        lon=151.2153,
        range_meters=100,
    )

    print(f"\nFound {len(result.results)} registration(s)")
    print(f"Queried {len(result.servers_queried)} server(s)")
    print(f"Followed {result.referrals_followed} referral(s)")
    print(f"Total time: {result.total_time_ms:.1f}ms")

    for reg in result.results:
        if reg.foad:
            print(f"  - {reg.id}: [FOAD - no services]")
        else:
            print(f"  - {reg.id}: {reg.service_point}")


async def search_async() -> None:
    """Asynchronous search example."""
    print("\n=== Asynchronous Search ===")

    async with MRSClient(verbose=True) as client:
        # Search near Times Square
        result = await client.search(
            lat=40.7580,
            lon=-73.9855,
            range_meters=500,
        )

        print(f"\nFound {len(result.results)} registration(s)")
        print(f"Queried {len(result.servers_queried)} server(s)")

        for reg in result.results:
            if reg.foad:
                print(f"  - {reg.id}: [FOAD - no services]")
            else:
                print(f"  - {reg.id}: {reg.service_point}")


if __name__ == "__main__":
    # Run synchronous example
    search_sync()

    # Run async example
    asyncio.run(search_async())
