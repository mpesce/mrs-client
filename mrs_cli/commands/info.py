"""Info command for MRS CLI."""

from __future__ import annotations

import click

from mrs_cli.output import print_error, print_server_info


@click.command()
@click.argument("server", required=False)
@click.pass_context
def info(ctx: click.Context, server: str | None) -> None:
    """Get server information.

    SERVER: Server URL (optional, uses default if not specified)

    Examples:

        mrs info

        mrs info https://sydney.mrs.example
    """
    from mrs_client import MRSClient
    from mrs_client.exceptions import MRSConnectionError, MRSError

    as_json = ctx.obj.get("json", False)
    verbose = ctx.obj.get("verbose", False)
    config_server = ctx.obj.get("server")
    config_dir = ctx.obj.get("config_dir")

    # Use argument server, then --server option, then default
    effective_server = server or config_server

    try:
        client = MRSClient(
            default_server=effective_server,
            config_dir=config_dir,
            verbose=verbose,
        )

        server_info = client.get_server_info_sync(server=effective_server)
        print_server_info(server_info, as_json=as_json)

    except MRSConnectionError as e:
        print_error(str(e))
        ctx.exit(4)
    except MRSError as e:
        print_error(str(e))
        ctx.exit(1)
