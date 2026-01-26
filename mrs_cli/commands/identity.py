"""Identity command for MRS CLI."""

from __future__ import annotations

import base64
import click

from mrs_cli.output import (
    console,
    print_error,
    print_identity,
    print_json,
    print_success,
    print_warning,
)


@click.group()
def identity() -> None:
    """Manage identity and authentication.

    Subcommands:

        show      Show current identity

        create    Create new identity

        login     Store a bearer token for a server

        logout    Remove stored token for a server

        export-key  Export public key

        verify    Test authentication with server
    """
    pass


@identity.command("show")
@click.pass_context
def identity_show(ctx: click.Context) -> None:
    """Show current identity."""
    from mrs_client.config import IdentityStore, TokenStore, get_config_dir

    as_json = ctx.obj.get("json", False)
    config_dir = ctx.obj.get("config_dir") or get_config_dir()

    identity_store = IdentityStore.load(config_dir)
    token_store = TokenStore.load(config_dir)

    print_identity(
        identity_id=identity_store.identity_id,
        key_id=identity_store.key_id,
        tokens=token_store.tokens,
        as_json=as_json,
    )


@identity.command("create")
@click.option("--username", required=True, help="Username for identity")
@click.option("--server", required=True, help="Server domain for identity")
@click.pass_context
def identity_create(ctx: click.Context, username: str, server: str) -> None:
    """Create a new identity with generated keys.

    This generates an Ed25519 keypair and stores it locally.

    Examples:

        mrs identity create --username mark --server owen.iz.net
    """
    from mrs_client import MRSClient
    from mrs_client.config import get_config_dir

    as_json = ctx.obj.get("json", False)
    config_dir = ctx.obj.get("config_dir") or get_config_dir()

    # Extract domain from server URL if needed
    domain = server
    if domain.startswith("https://"):
        domain = domain[8:]
    elif domain.startswith("http://"):
        domain = domain[7:]
    domain = domain.rstrip("/")

    try:
        client = MRSClient(config_dir=config_dir)
        identity = client.create_identity(username, domain)

        if as_json:
            print_json({
                "status": "created",
                "identity": identity.id,
                "key_id": identity.key_id,
                "public_key": base64.b64encode(identity.public_key).decode(),
            })
        else:
            print_success(f"Created identity: {identity.id}")
            console.print(f"Key ID: {identity.key_id}")
            console.print()
            console.print("To complete setup:")
            console.print(f"  1. Register with server: mrs identity login --server {server} --token YOUR_TOKEN")
            console.print("  2. Your public key can be exported with: mrs identity export-key")

    except Exception as e:
        print_error(str(e))
        ctx.exit(1)


@identity.command("login")
@click.option("--server", required=True, help="Server URL")
@click.option("--token", required=True, help="Bearer token")
@click.option("--expires", help="Token expiration (ISO format)")
@click.pass_context
def identity_login(
    ctx: click.Context, server: str, token: str, expires: str | None
) -> None:
    """Store a bearer token for a server.

    Get the token from the server's authentication system.

    Examples:

        mrs identity login --server https://owen.iz.net --token abc123...
    """
    from mrs_client import MRSClient
    from mrs_client.config import get_config_dir

    as_json = ctx.obj.get("json", False)
    config_dir = ctx.obj.get("config_dir") or get_config_dir()

    # Ensure server URL has scheme
    if not server.startswith("http://") and not server.startswith("https://"):
        server = f"https://{server}"

    try:
        client = MRSClient(config_dir=config_dir)
        client.store_token(server, token, expires)

        if as_json:
            print_json({"status": "stored", "server": server})
        else:
            print_success(f"Stored token for {server}")

    except Exception as e:
        print_error(str(e))
        ctx.exit(1)


@identity.command("logout")
@click.option("--server", required=True, help="Server URL")
@click.pass_context
def identity_logout(ctx: click.Context, server: str) -> None:
    """Remove stored token for a server.

    Examples:

        mrs identity logout --server https://owen.iz.net
    """
    from mrs_client import MRSClient
    from mrs_client.config import get_config_dir

    as_json = ctx.obj.get("json", False)
    config_dir = ctx.obj.get("config_dir") or get_config_dir()

    # Ensure server URL has scheme
    if not server.startswith("http://") and not server.startswith("https://"):
        server = f"https://{server}"

    try:
        client = MRSClient(config_dir=config_dir)
        client.remove_token(server)

        if as_json:
            print_json({"status": "removed", "server": server})
        else:
            print_success(f"Removed token for {server}")

    except Exception as e:
        print_error(str(e))
        ctx.exit(1)


@identity.command("export-key")
@click.pass_context
def identity_export_key(ctx: click.Context) -> None:
    """Export public key in MRS format.

    This outputs the public key in a format suitable for
    registering with an MRS server.

    Examples:

        mrs identity export-key

        mrs identity export-key --json
    """
    from mrs_client import MRSClient
    from mrs_client.config import get_config_dir
    from mrs_client.exceptions import MRSAuthError

    as_json = ctx.obj.get("json", False)
    config_dir = ctx.obj.get("config_dir") or get_config_dir()

    try:
        client = MRSClient(config_dir=config_dir)
        key_data = client.export_public_key()

        if as_json:
            print_json(key_data)
        else:
            console.print(f"[bold]Identity:[/bold] {key_data['id']}")
            console.print(f"[bold]Key ID:[/bold] {key_data['key_id']}")
            console.print(f"[bold]Algorithm:[/bold] {key_data['public_key']['type']}")
            console.print(f"[bold]Public Key:[/bold]")
            console.print(f"  {key_data['public_key']['key']}")

    except MRSAuthError as e:
        print_error(str(e))
        ctx.exit(3)
    except Exception as e:
        print_error(str(e))
        ctx.exit(1)


@identity.command("verify")
@click.option("--server", help="Server URL (uses default if not specified)")
@click.pass_context
def identity_verify(ctx: click.Context, server: str | None) -> None:
    """Test authentication with a server.

    This verifies that your stored token is valid and the server
    recognizes your identity.

    Examples:

        mrs identity verify

        mrs identity verify --server https://owen.iz.net
    """
    from mrs_client import MRSClient
    from mrs_client.config import get_config_dir
    from mrs_client.exceptions import MRSAuthError, MRSConnectionError

    as_json = ctx.obj.get("json", False)
    verbose = ctx.obj.get("verbose", False)
    config_server = ctx.obj.get("server")
    config_dir = ctx.obj.get("config_dir") or get_config_dir()

    effective_server = server or config_server

    try:
        client = MRSClient(
            default_server=effective_server,
            config_dir=config_dir,
            verbose=verbose,
        )

        target_server = effective_server or client.default_server

        # Check if we have a token
        token = client.get_token(target_server)
        if not token:
            if as_json:
                print_json({
                    "status": "error",
                    "server": target_server,
                    "error": "no_token",
                    "message": "No token stored for this server",
                })
            else:
                console.print(f"Testing authentication with {target_server}...")
                console.print()
                console.print("[red]x[/red] Bearer token: not found for this server")
                console.print(f"  Run: mrs identity login --server {target_server} --token YOUR_TOKEN")
                console.print()
                console.print("[red]Authentication FAILED[/red]")
            ctx.exit(3)

        # Verify with server
        user_info = client.verify_auth_sync(server=target_server)

        if as_json:
            print_json({
                "status": "ok",
                "server": target_server,
                "user": user_info,
            })
        else:
            console.print(f"Testing authentication with {target_server}...")
            console.print()
            console.print("[green]✓[/green] Bearer token: valid")
            console.print(f"[green]✓[/green] Server recognizes identity: {user_info.get('id', 'unknown')}")
            console.print(f"[green]✓[/green] Can create registrations: {'yes' if user_info.get('can_register') else 'no'}")
            console.print()
            console.print("[green]Authentication OK[/green]")

    except MRSAuthError as e:
        if as_json:
            print_json({
                "status": "error",
                "server": effective_server or "default",
                "error": "auth_failed",
                "message": str(e),
            })
        else:
            console.print(f"Testing authentication with {effective_server or 'default server'}...")
            console.print()
            console.print(f"[red]x[/red] Authentication failed: {e}")
            console.print()
            console.print("[red]Authentication FAILED[/red]")
        ctx.exit(3)
    except MRSConnectionError as e:
        if as_json:
            print_json({
                "status": "error",
                "server": effective_server or "default",
                "error": "connection_failed",
                "message": str(e),
            })
        else:
            print_error(f"Connection failed: {e}")
        ctx.exit(4)
    except Exception as e:
        print_error(str(e))
        ctx.exit(1)
