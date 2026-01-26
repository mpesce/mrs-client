"""Main CLI entry point for MRS."""

from __future__ import annotations

from pathlib import Path

import click

from mrs_cli.commands.identity import identity
from mrs_cli.commands.info import info
from mrs_cli.commands.list_cmd import list_cmd
from mrs_cli.commands.register import register
from mrs_cli.commands.release import release
from mrs_cli.commands.search import search


@click.group()
@click.option(
    "--server", "-s",
    envvar="MRS_SERVER",
    help="Override default server URL"
)
@click.option(
    "--config", "-c", "config_dir",
    type=click.Path(path_type=Path),
    envvar="MRS_CONFIG_DIR",
    help="Config directory (default: platform-specific)"
)
@click.option(
    "--json", "-j", "output_json",
    is_flag=True,
    help="Output as JSON (for machine consumption)"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Verbose output (show HTTP requests/responses)"
)
@click.version_option(package_name="mrs-client")
@click.pass_context
def cli(
    ctx: click.Context,
    server: str | None,
    config_dir: Path | None,
    output_json: bool,
    verbose: bool,
) -> None:
    """MRS - Mixed Reality Service client.

    Query and register spaces in the federated MRS network.
    MRS is like DNS for physical space: coordinates map to service URIs.

    \b
    Examples:
        mrs search -33.8568 151.2153 --range 100
        mrs register --lat -33.8568 --lon 151.2153 --radius 50 --service https://example.com
        mrs info
        mrs identity show

    \b
    Environment variables:
        MRS_SERVER      Default server URL
        MRS_CONFIG_DIR  Configuration directory
    """
    ctx.ensure_object(dict)
    ctx.obj["server"] = server
    ctx.obj["config_dir"] = config_dir
    ctx.obj["json"] = output_json
    ctx.obj["verbose"] = verbose


# Register commands
cli.add_command(search)
cli.add_command(register)
cli.add_command(release)
cli.add_command(list_cmd)
cli.add_command(info)
cli.add_command(identity)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
