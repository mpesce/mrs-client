"""Search command for MRS CLI."""

from __future__ import annotations

import click

from mrs_cli.output import print_error, print_search_result


@click.command()
@click.argument("lat", type=float)
@click.argument("lon", type=float)
@click.option("--ele", type=float, default=0.0, help="Elevation in meters (default: 0)")
@click.option(
    "--range", "range_meters", type=float, default=0.0,
    help="Search radius in meters (default: 0)"
)
@click.option(
    "--max-depth", type=int, default=None,
    help="Maximum referral depth (default: 5)"
)
@click.pass_context
def search(
    ctx: click.Context,
    lat: float,
    lon: float,
    ele: float,
    range_meters: float,
    max_depth: int | None,
) -> None:
    """Search for registrations at a location.

    LAT: Latitude (-90 to 90)

    LON: Longitude (-180 to 180)

    Examples:

        mrs search -33.8568 151.2153

        mrs search -33.8568 151.2153 --range 100

        mrs search 40.7128 -74.0060 --range 500 --json
    """
    from mrs_client import MRSClient
    from mrs_client.exceptions import MRSError

    as_json = ctx.obj.get("json", False)
    verbose = ctx.obj.get("verbose", False)
    server = ctx.obj.get("server")
    config_dir = ctx.obj.get("config_dir")

    try:
        client = MRSClient(
            default_server=server,
            config_dir=config_dir,
            max_referral_depth=max_depth,
            verbose=verbose,
        )

        servers = [server] if server else None
        result = client.search_sync(
            lat=lat,
            lon=lon,
            ele=ele,
            range_meters=range_meters,
            servers=servers,
        )

        print_search_result(result, as_json=as_json)

    except MRSError as e:
        print_error(str(e))
        ctx.exit(1)
    except ValueError as e:
        print_error(str(e))
        ctx.exit(2)
