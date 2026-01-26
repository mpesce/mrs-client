# MRS Client Installation Guide

This guide covers installing the MRS client library and CLI tool on Windows, macOS, and Linux.

## Requirements

- **Python 3.11 or later**
- **pip** (Python package manager)

### Checking Your Python Version

```bash
python3 --version
```

If you see a version less than 3.11, you'll need to upgrade Python first.

## Installation Methods

### Method 1: Install from PyPI (Recommended)

Once published to PyPI:

```bash
pip install mrs-client
```

### Method 2: Install from GitHub

```bash
pip install git+https://github.com/mpesce/mrs-client.git
```

### Method 3: Install from Source

```bash
# Clone the repository
git clone https://github.com/mpesce/mrs-client.git
cd mrs-client

# Install in editable mode (for development)
pip install -e .

# Or install normally
pip install .
```

## Platform-Specific Instructions

### Windows

1. **Install Python 3.11+**

   Download from [python.org](https://www.python.org/downloads/windows/) or use winget:
   ```powershell
   winget install Python.Python.3.11
   ```

2. **Open PowerShell or Command Prompt**

3. **Install MRS client**
   ```powershell
   pip install mrs-client
   ```

4. **Verify installation**
   ```powershell
   mrs --version
   mrs --help
   ```

**Configuration location:** `%APPDATA%\mrs\`

### macOS

1. **Install Python 3.11+**

   Using Homebrew (recommended):
   ```bash
   brew install python@3.11
   ```

   Or download from [python.org](https://www.python.org/downloads/macos/)

2. **Install MRS client**
   ```bash
   pip3 install mrs-client
   ```

3. **Verify installation**
   ```bash
   mrs --version
   mrs --help
   ```

**Configuration location:** `~/Library/Application Support/mrs/`

### Linux (Ubuntu/Debian)

1. **Install Python 3.11+**
   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv python3-pip
   ```

2. **Install MRS client**
   ```bash
   pip3 install mrs-client
   ```

   Or use a virtual environment:
   ```bash
   python3.11 -m venv ~/.venv/mrs
   source ~/.venv/mrs/bin/activate
   pip install mrs-client
   ```

3. **Verify installation**
   ```bash
   mrs --version
   mrs --help
   ```

**Configuration location:** `~/.config/mrs/`

### Linux (Fedora/RHEL)

1. **Install Python 3.11+**
   ```bash
   sudo dnf install python3.11 python3-pip
   ```

2. **Install MRS client**
   ```bash
   pip3 install mrs-client
   ```

3. **Verify installation**
   ```bash
   mrs --version
   ```

### Linux (Arch)

1. **Install Python**
   ```bash
   sudo pacman -S python python-pip
   ```

2. **Install MRS client**
   ```bash
   pip install mrs-client
   ```

## Virtual Environments (Recommended)

Using a virtual environment keeps MRS client isolated from other Python packages:

```bash
# Create virtual environment
python3 -m venv ~/.venv/mrs

# Activate it
# On macOS/Linux:
source ~/.venv/mrs/bin/activate
# On Windows:
~\.venv\mrs\Scripts\activate

# Install MRS client
pip install mrs-client

# Deactivate when done
deactivate
```

## Installing for Development

If you want to modify the code or run tests:

```bash
# Clone the repo
git clone https://github.com/mpesce/mrs-client.git
cd mrs-client

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=mrs_client --cov=mrs_cli

# Type checking
mypy mrs_client mrs_cli

# Linting
ruff check mrs_client mrs_cli
```

## Verifying Installation

After installation, verify everything works:

```bash
# Check version
mrs --version

# Show help
mrs --help

# Get server info (tests network connectivity)
mrs info

# Test a search (no authentication required)
mrs search -33.8568 151.2153 --range 100
```

## Configuration

The first time you run `mrs`, it creates a configuration directory:

| Platform | Location |
|----------|----------|
| Windows | `%APPDATA%\mrs\` |
| macOS | `~/Library/Application Support/mrs/` |
| Linux | `~/.config/mrs/` |

You can override this with `--config` or the `MRS_CONFIG_DIR` environment variable.

### Configuration Files

```
~/.config/mrs/           # (Linux example)
├── config.json          # Client settings
├── identity.json        # Your MRS identity
└── tokens.json          # Stored authentication tokens
```

## Setting Up Authentication

Search is public, but registration requires authentication:

```bash
# 1. Create an identity (generates Ed25519 keypair)
mrs identity create --username yourname --server owen.iz.net

# 2. Get a token from your server admin and store it
mrs identity login --server https://owen.iz.net --token YOUR_TOKEN

# 3. Verify it works
mrs identity verify

# 4. View your identity
mrs identity show
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `MRS_SERVER` | Default server URL |
| `MRS_CONFIG_DIR` | Configuration directory |

Example:
```bash
export MRS_SERVER=https://owen.iz.net
export MRS_CONFIG_DIR=/custom/path/mrs
```

## Troubleshooting

### "command not found: mrs"

The `mrs` command isn't in your PATH. Solutions:

1. **Use the full path:**
   ```bash
   python3 -m mrs_cli.main --help
   ```

2. **Add pip's bin directory to PATH:**
   ```bash
   # Find where pip installs scripts
   python3 -m site --user-base
   # Add that path + /bin to your PATH
   ```

3. **Use a virtual environment** (recommended)

### "ModuleNotFoundError: No module named 'mrs_client'"

The package isn't installed. Run:
```bash
pip install mrs-client
```

### "Python version X.X not in '>=3.11'"

You need Python 3.11 or later. Check your version:
```bash
python3 --version
```

Install a newer Python version for your platform (see above).

### SSL/TLS errors

If you see certificate errors, ensure your system's CA certificates are up to date:

```bash
# macOS
brew install ca-certificates

# Ubuntu/Debian
sudo apt install ca-certificates

# Fedora/RHEL
sudo dnf install ca-certificates
```

### Connection refused / timeout

- Check your network connection
- Verify the server URL is correct
- The server may be down - try later

## Uninstalling

```bash
pip uninstall mrs-client
```

To also remove configuration:
```bash
# macOS
rm -rf ~/Library/Application\ Support/mrs

# Linux
rm -rf ~/.config/mrs

# Windows (PowerShell)
Remove-Item -Recurse $env:APPDATA\mrs
```

## Getting Help

- **CLI help:** `mrs --help` or `mrs <command> --help`
- **GitHub Issues:** https://github.com/mpesce/mrs-client/issues
- **Documentation:** See README.md in the repository
