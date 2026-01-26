"""Register command for MRS CLI."""

from __future__ import annotations

import click

from mrs_cli.output import print_error, print_json, print_registration, print_success


@click.command()
@click.option("--lat", type=float, required=True, help="Center latitude")
@click.option("--lon", type=float, required=True, help="Center longitude")
@click.option("--ele", type=float, default=0.0, help="Center elevation (default: 0)")
@click.option("--radius", type=float, required=True, help="Radius in meters")
@click.option("--service", "service_point", type=str, help="Service point URI")
@click.option("--foad", is_flag=True, help="Register as FOAD (no services)")
@click.pass_context
def register(
    ctx: click.Context,
    lat: float,
    lon: float,
    ele: float,
    radius: float,
    service_point: str | None,
    foad: bool,
) -> None:
    """Register a space.

    Examples:

        mrs register --lat -33.8568 --lon 151.2153 --radius 50 --service https://example.com/my-place

        mrs register --lat -33.8568 --lon 151.2153 --radius 100 --foad
    """
    from mrs_client import MRSClient
    from mrs_client.exceptions import MRSAuthError, MRSError, MRSValidationError

    as_json = ctx.obj.get("json", False)
    verbose = ctx.obj.get("verbose", False)
    server = ctx.obj.get("server")
    config_dir = ctx.obj.get("config_dir")

    # Validate inputs
    if not foad and not service_point:
        print_error("--service is required unless --foad is specified")
        ctx.exit(2)

    try:
        client = MRSClient(
            default_server=server,
            config_dir=config_dir,
            verbose=verbose,
        )

        registration = client.register_sync(
            lat=lat,
            lon=lon,
            ele=ele,
            radius=radius,
            service_point=service_point,
            foad=foad,
            server=server,
        )

        if as_json:
            print_json({
                "status": "registered",
                "registration": registration.to_dict(),
            })
        else:
            print_success("Registered space successfully!")
            print()
            print_registration(registration)

    except MRSAuthError as e:
        print_error(str(e))
        ctx.exit(3)
    except MRSValidationError as e:
        print_error(str(e))
        ctx.exit(2)
    except MRSError as e:
        print_error(str(e))
        ctx.exit(1)
    except ValueError as e:
        print_error(str(e))
        ctx.exit(2)


def print() -> None:
    """Print a blank line."""
    import builtins
    builtins.print()
