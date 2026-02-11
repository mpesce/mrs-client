# MRS Client

**Mixed Reality Service client library and CLI for Python**

MRS is like DNS for physical space: it maps coordinates to service URIs. This client lets you query and register spaces in the federated MRS network.

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/mpesce/mrs-client.git

# Or clone and install locally
git clone https://github.com/mpesce/mrs-client.git
cd mrs-client
pip install .
```

Requires Python 3.11 or later. See [INSTALL.md](INSTALL.md) for detailed platform-specific instructions.

## 90-Second Setup

```bash
git clone https://github.com/mpesce/mrs-client.git
cd mrs-client
./scripts/bootstrap.sh
./scripts/verify.sh
```

For a short walkthrough, see [QUICKSTART.md](QUICKSTART.md).

## Quick Start

### CLI Usage

```bash
# Search for registrations near a location
mrs search -33.8568 151.2153

# Search with a radius
mrs search -33.8568 151.2153 --range 100

# Get JSON output for scripting
mrs search -33.8568 151.2153 --json

# Get server information
mrs info

# See verbose HTTP output
mrs search -33.8568 151.2153 --verbose
```

### Library Usage

```python
from mrs_client import MRSClient

# Create client
client = MRSClient()

# Search (synchronous)
result = client.search_sync(lat=-33.8568, lon=151.2153, range_meters=100)

for reg in result.results:
    if reg.foad:
        print(f"{reg.id}: [FOAD - no services]")
    else:
        print(f"{reg.id}: {reg.service_point}")

# Search (async)
import asyncio

async def search_async():
    async with MRSClient() as client:
        result = await client.search(lat=-33.8568, lon=151.2153, range_meters=100)
        return result

result = asyncio.run(search_async())
```

## Authentication

MRS search is public, but registration requires authentication:

```bash
# Create an identity (generates Ed25519 keypair)
mrs identity create --username yourname --server owen.iz.net

# Store a bearer token from your server
mrs identity login --server https://owen.iz.net --token YOUR_TOKEN

# Verify authentication works
mrs identity verify --server https://owen.iz.net

# Show current identity
mrs identity show
```

## Registering Spaces

```bash
# Register a space with a service endpoint
mrs register --lat -33.8568 --lon 151.2153 --radius 50 \
    --service https://example.com/my-space

# Register a FOAD space (declines to provide services)
mrs register --lat -33.8568 --lon 151.2153 --radius 100 --foad

# List your registrations
mrs list

# Release (delete) a registration
mrs release reg_abc123
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `mrs search LAT LON` | Search for registrations at a location |
| `mrs register` | Register a new space |
| `mrs release ID` | Release (delete) a registration |
| `mrs list` | List your registrations |
| `mrs info [URL]` | Get server information |
| `mrs identity show` | Show current identity |
| `mrs identity create` | Create new identity |
| `mrs identity login` | Store authentication token |
| `mrs identity logout` | Remove authentication token |
| `mrs identity verify` | Test authentication |
| `mrs identity export-key` | Export public key |

### Global Options

| Option | Description |
|--------|-------------|
| `--server URL` | Override default server |
| `--config DIR` | Custom config directory |
| `--json` | Output as JSON |
| `--verbose` | Show HTTP request/response details |

## Configuration

Configuration is stored in a platform-appropriate location:

- **Windows:** `%APPDATA%\mrs\`
- **macOS:** `~/Library/Application Support/mrs/`
- **Linux:** `~/.config/mrs/`

You can override this with `--config` or the `MRS_CONFIG_DIR` environment variable.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `MRS_SERVER` | Default server URL |
| `MRS_CONFIG_DIR` | Configuration directory |

## Library API

### MRSClient

```python
from mrs_client import MRSClient

client = MRSClient(
    default_server="https://owen.iz.net",  # Override default server
    config_dir=None,                        # Use default config location
    max_referral_depth=5,                   # Max referral chain length
    timeout=30.0,                           # HTTP timeout in seconds
    verbose=False,                          # Enable verbose logging
)
```

### Search

```python
# Synchronous
result = client.search_sync(
    lat=-33.8568,
    lon=151.2153,
    ele=0.0,           # Elevation (optional)
    range_meters=100,  # Search radius
)

# Async
result = await client.search(lat=-33.8568, lon=151.2153)

# Result contains:
# - results: List[Registration] - found registrations
# - servers_queried: List[str] - servers that were queried
# - referrals_followed: int - number of referrals followed
# - total_time_ms: float - total query time
```

### Register

```python
# Synchronous
registration = client.register_sync(
    lat=-33.8568,
    lon=151.2153,
    radius=50,
    service_point="https://example.com/my-space",
    foad=False,
)

# Async
registration = await client.register(
    lat=-33.8568,
    lon=151.2153,
    radius=50,
    service_point="https://example.com/my-space",
)
```

### Other Operations

```python
# Release a registration
client.release_sync(registration_id="reg_abc123")

# List your registrations
registrations = client.list_registrations_sync()

# Get server info
info = client.get_server_info_sync()

# Verify authentication
user_info = client.verify_auth_sync()
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Authentication error |
| 4 | Connection error |
| 5 | Not found |

## FOAD Flag

When a registration has `foad=True`, it means "Forbidden/Off-limits And Declared":

- The space is claimed
- It explicitly declines to provide services
- Agents should not attempt to interact with this space

This is a privacy mechanism. Respect it.

## Federation

MRS is federated - no single server knows everything. When you search, the client automatically:

1. Queries the initial server(s)
2. Follows referrals to other servers
3. Deduplicates results
4. Sorts by specificity (smallest volume first)

This is transparent to you - just search and get results.

## Development

```bash
# Clone the repo
git clone https://github.com/mpesce/mrs-client.git
cd mrs-client

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=mrs_client --cov=mrs_cli

# Type checking
mypy mrs_client mrs_cli

# Linting
ruff check mrs_client mrs_cli
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Mark D. Pesce (mpesce@gmail.com)

## Links

- [GitHub Repository](https://github.com/mpesce/mrs-client)
- [MRS Protocol Specification](MRS-SPEC-DRAFT.md)
