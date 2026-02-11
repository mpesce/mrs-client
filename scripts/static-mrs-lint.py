#!/usr/bin/env python3
"""Lint a Level-0 static MRS JSON dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mrs_client.models import Location, Sphere
from mrs_client.validation import validate_service_point_uri


def err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def lint_registration(i: int, reg: dict[str, Any], errors: list[str], warnings: list[str], seen_ids: set[str]) -> None:
    prefix = f"registrations[{i}]"

    rid = reg.get("id")
    if not isinstance(rid, str) or not rid:
        err(errors, f"{prefix}.id missing/invalid")
    else:
        if rid in seen_ids:
            err(errors, f"{prefix}.id duplicate: {rid}")
        seen_ids.add(rid)

    space = reg.get("space")
    if not isinstance(space, dict):
        err(errors, f"{prefix}.space missing/invalid")
        return

    if space.get("type") != "sphere":
        err(errors, f"{prefix}.space.type must be 'sphere'")
        return

    center = space.get("center")
    radius = space.get("radius")
    try:
        loc = Location(
            lat=float(center["lat"]),
            lon=float(center["lon"]),
            ele=float(center.get("ele", 0.0)),
        )
        Sphere(center=loc, radius=float(radius))
    except Exception as e:
        err(errors, f"{prefix}.space invalid: {e}")

    foad = bool(reg.get("foad", False))
    sp = reg.get("service_point")
    if not foad:
        if not isinstance(sp, str):
            err(errors, f"{prefix}.service_point required when foad=false")
        else:
            try:
                validate_service_point_uri(sp)
            except Exception as e:
                err(errors, f"{prefix}.service_point invalid: {e}")
    else:
        if isinstance(sp, str):
            warnings.append(f"{prefix}.foad=true but service_point present")

    for tfield in ("created", "updated"):
        if tfield in reg and not isinstance(reg[tfield], str):
            err(errors, f"{prefix}.{tfield} must be ISO string if present")


def main() -> int:
    ap = argparse.ArgumentParser(description="Lint static MRS JSON")
    ap.add_argument("source", help="Path to mrs-static.json")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    args = ap.parse_args()

    p = Path(args.source)
    data = json.loads(p.read_text(encoding="utf-8"))

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        print("ERROR: root must be object")
        return 2

    regs = data.get("registrations")
    if not isinstance(regs, list):
        print("ERROR: root.registrations must be array")
        return 2

    seen_ids: set[str] = set()
    for i, reg in enumerate(regs):
        if not isinstance(reg, dict):
            err(errors, f"registrations[{i}] must be object")
            continue
        lint_registration(i, reg, errors, warnings, seen_ids)

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}")

    if errors or (args.strict and warnings):
        print(f"\nFAIL: {len(errors)} error(s), {len(warnings)} warning(s)")
        return 1

    print(f"PASS: {len(regs)} registrations checked, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
