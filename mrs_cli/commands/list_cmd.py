"""List command for MRS CLI."""

from __future__ import annotations

import click

from mrs_cli.output import print_error, print_registrations


@click.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List your registrations.

    Examples:

        mrs list

        mrs list --server https://sydney.mrs.example
    """
    from mrs_client import MRSClient
    from mrs_client.exceptions import MRSAuthError, MRSError

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

        effective_server = client.default_server if not server else server
        registrations = client.list_registrations_sync(server=server)

        print_registrations(registrations, effective_server, as_json=as_json)

    except MRSAuthError as e:
        print_error(str(e))
        ctx.exit(3)
    except MRSError as e:
        print_error(str(e))
        ctx.exit(1)
