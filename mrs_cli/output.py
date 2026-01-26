"""Output formatting for CLI."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

from mrs_client.geo import format_distance
from mrs_client.models import Registration, SearchResult, ServerInfo

console = Console()
error_console = Console(stderr=True)


def print_error(message: str) -> None:
    """Print an error message."""
    error_console.print(f"[red]Error:[/red] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    error_console.print(f"[yellow]Warning:[/yellow] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_json(data: Any) -> None:
    """Print data as JSON."""
    print(json.dumps(data, indent=2, default=str))


def format_registration_human(reg: Registration, index: int | None = None) -> str:
    """Format a registration for human display."""
    lines = []

    # Header
    header = reg.id
    if index is not None:
        header = f"{index}. {header}"
    if reg.distance is not None:
        header += f" ({format_distance(reg.distance)} away)"
    lines.append(header)

    # Space info
    space = reg.space
    space_desc = f"   Space: {space.type}, radius {format_distance(space.radius)}"
    lines.append(space_desc)

    # Service or FOAD
    if reg.foad:
        lines.append("   [yellow]FOAD: This space declines to provide services[/yellow]")
    elif reg.service_point:
        lines.append(f"   Service: {reg.service_point}")

    # Owner
    lines.append(f"   Owner: {reg.owner}")

    return "\n".join(lines)


def print_search_result(result: SearchResult, as_json: bool = False) -> None:
    """Print search results."""
    if as_json:
        print_json(result.to_dict())
        return

    if not result.results:
        console.print("No registrations found.")
        return

    summary = (
        f"Found {len(result.results)} registration(s) "
        f"(queried {len(result.servers_queried)} server(s), "
        f"followed {result.referrals_followed} referral(s)):"
    )
    console.print(summary)
    console.print()

    for i, reg in enumerate(result.results, 1):
        console.print(format_registration_human(reg, i))
        console.print()


def print_registration(reg: Registration, as_json: bool = False) -> None:
    """Print a single registration."""
    if as_json:
        print_json(reg.to_dict())
        return

    console.print(format_registration_human(reg))


def print_registrations(
    registrations: list[Registration], server: str, as_json: bool = False
) -> None:
    """Print a list of registrations."""
    if as_json:
        print_json({"registrations": [r.to_dict() for r in registrations]})
        return

    if not registrations:
        console.print(f"No registrations on {server}")
        return

    console.print(f"Your registrations on {server}:")
    console.print()

    for i, reg in enumerate(registrations, 1):
        lines = [f"{i}. {reg.id}"]
        space = reg.space
        lines.append(
            f"   Space: {space.type} at "
            f"({space.center.lat:.6f}, {space.center.lon:.6f}), "
            f"radius {format_distance(space.radius)}"
        )
        if reg.foad:
            lines.append("   FOAD: true")
        elif reg.service_point:
            lines.append(f"   Service: {reg.service_point}")
        lines.append(f"   Created: {reg.created.isoformat()}")

        for line in lines:
            console.print(line)
        console.print()


def print_server_info(info: ServerInfo, as_json: bool = False) -> None:
    """Print server information."""
    if as_json:
        data = {
            "server": info.url,
            "mrs_version": info.mrs_version,
            "operator": info.operator,
            "authoritative_regions": [r.to_dict() for r in info.authoritative_regions],
            "known_peers": [p.to_dict() for p in info.known_peers],
            "capabilities": info.capabilities,
        }
        print_json(data)
        return

    console.print(f"[bold]Server:[/bold] {info.url}")
    console.print(f"[bold]MRS Version:[/bold] {info.mrs_version}")

    if info.operator:
        console.print(f"[bold]Operator:[/bold] {info.operator}")

    console.print()

    if info.authoritative_regions:
        console.print("[bold]Authoritative Regions:[/bold]")
        for region in info.authoritative_regions:
            console.print(
                f"  - {region.type} at "
                f"({region.center.lat:.6f}, {region.center.lon:.6f}), "
                f"radius {format_distance(region.radius)}"
            )
    else:
        console.print("[bold]Authoritative Regions:[/bold] (none)")

    console.print()

    if info.known_peers:
        console.print("[bold]Known Peers:[/bold]")
        for peer in info.known_peers:
            hint = f" ({peer.hint})" if peer.hint else ""
            console.print(f"  - {peer.server}{hint}")
    else:
        console.print("[bold]Known Peers:[/bold] (none)")

    console.print()

    if info.capabilities:
        console.print("[bold]Capabilities:[/bold]")
        for key, value in info.capabilities.items():
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            console.print(f"  {key}: {value}")


def print_identity(
    identity_id: str | None,
    key_id: str | None,
    tokens: dict[str, Any],
    as_json: bool = False,
) -> None:
    """Print identity information."""
    if as_json:
        data = {
            "identity": identity_id,
            "key_id": key_id,
            "tokens": list(tokens.keys()),
        }
        print_json(data)
        return

    if identity_id:
        console.print(f"[bold]Current identity:[/bold] {identity_id}")
        if key_id:
            console.print(f"[bold]Key ID:[/bold] {key_id}")
    else:
        console.print("[yellow]No identity configured[/yellow]")
        console.print("Run: mrs identity create --username NAME --server DOMAIN")

    console.print()

    if tokens:
        console.print("[bold]Stored tokens:[/bold]")
        for server, token_data in tokens.items():
            expires = token_data.get("expires_at", "no expiry")
            console.print(f"  {server}: valid ({expires})")
    else:
        console.print("[bold]Stored tokens:[/bold] (none)")
