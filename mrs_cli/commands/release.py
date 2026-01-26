"""Release command for MRS CLI."""

from __future__ import annotations

import click

from mrs_cli.output import print_error, print_json, print_success


@click.command()
@click.argument("registration_id")
@click.pass_context
def release(ctx: click.Context, registration_id: str) -> None:
    """Release (delete) a registration.

    REGISTRATION_ID: ID of registration to release (e.g., reg_abc123)

    Examples:

        mrs release reg_abc123
    """
    from mrs_client import MRSClient
    from mrs_client.exceptions import MRSAuthError, MRSError, MRSNotFoundError

    as_json = ctx.obj.get("json", False)
    verbose = ctx.obj.get("verbose", False)
    server = ctx.obj.get("server")
    config_dir = ctx.obj.get("config_dir")

    try:
        client = MRSClient(
            default_server=server,
            config_dir=config_dir,
            verbose=verbose,
        )

        client.release_sync(registration_id, server=server)

        if as_json:
            print_json({"status": "released", "id": registration_id})
        else:
            print_success(f"Released registration {registration_id}")

    except MRSNotFoundError:
        print_error(f"Registration {registration_id} not found")
        ctx.exit(5)
    except MRSAuthError as e:
        print_error(str(e))
        ctx.exit(3)
    except MRSError as e:
        print_error(str(e))
        ctx.exit(1)
