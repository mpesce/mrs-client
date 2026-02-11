#!/usr/bin/env python3
"""Query a Level-0 static MRS JSON map.

Supports source as:
- local file path
- http(s) URL
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from mrs_client.geo import haversine_distance, search_sphere_intersects_registration
from mrs_client.models import Location, Registration, Sphere


def load_source(source: str) -> dict:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        with urlopen(source, timeout=15) as r:  # noqa: S310
            return json.loads(r.read().decode("utf-8"))
    return json.loads(Path(source).read_text(encoding="utf-8"))


def parse_registration(item: dict) -> Registration:
    return Registration.from_dict(item)


def main() -> int:
    p = argparse.ArgumentParser(description="Query static MRS JSON")
    p.add_argument("--source", required=True, help="Path or URL to static MRS JSON")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--ele", type=float, default=0.0)
    p.add_argument("--range", dest="range_m", type=float, default=0.0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    payload = load_source(args.source)
    regs_raw = payload.get("registrations", [])

    q = Location(lat=args.lat, lon=args.lon, ele=args.ele)
    out: list[Registration] = []

    for item in regs_raw:
        reg = parse_registration(item)
        if not isinstance(reg.space, Sphere):
            continue
        if reg.foad:
            continue
        if search_sphere_intersects_registration(q, args.range_m, reg.space):
            reg.distance = haversine_distance(q, reg.space.center)
            out.append(reg)

    out.sort(key=lambda r: (r.space.volume(), r.distance if r.distance is not None else 10**18))

    if args.json:
        print(
            json.dumps(
                {
                    "status": "ok",
                    "results": [r.to_dict() for r in out],
                    "source": args.source,
                    "count": len(out),
                },
                indent=2,
            )
        )
    else:
        print(f"Found {len(out)} result(s) from {args.source}")
        for r in out:
            sp = r.service_point or "[FOAD]"
            dist = f"{r.distance:.1f}m" if r.distance is not None else "n/a"
            print(f"- {r.id} :: {sp} :: {dist}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
