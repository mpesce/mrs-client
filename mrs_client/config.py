"""Configuration management for MRS client."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def get_config_dir() -> Path:
    """Get platform-appropriate configuration directory.

    - Windows: %APPDATA%/mrs
    - macOS: ~/Library/Application Support/mrs
    - Linux: ~/.config/mrs (following XDG spec)
    """
    if sys.platform == "win32":
        # Windows: use APPDATA
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / "mrs"
        # Fallback to user home
        return Path.home() / ".mrs"
    elif sys.platform == "darwin":
        # macOS: use Application Support
        return Path.home() / "Library" / "Application Support" / "mrs"
    else:
        # Linux/Unix: follow XDG spec
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            return Path(xdg_config) / "mrs"
        return Path.home() / ".config" / "mrs"


@dataclass
class Config:
    """MRS client configuration."""

    default_server: str = "https://owen.iz.net"
    max_referral_depth: int = 5
    max_servers: int = 20
    timeout_seconds: float = 30.0
    servers: dict[str, dict[str, str]] = field(default_factory=dict)

    # Test mode settings
    test_mode: bool = False
    test_server_url: str | None = None

    @classmethod
    def load(cls, config_dir: Path | None = None) -> Config:
        """Load configuration from disk."""
        if config_dir is None:
            config_dir = get_config_dir()

        config_file = config_dir / "config.json"
        if not config_file.exists():
            return cls()

        try:
            data = json.loads(config_file.read_text())
            return cls(
                default_server=data.get("default_server", cls.default_server),
                max_referral_depth=data.get("max_referral_depth", cls.max_referral_depth),
                max_servers=data.get("max_servers", cls.max_servers),
                timeout_seconds=data.get("timeout_seconds", cls.timeout_seconds),
                servers=data.get("servers", {}),
                test_mode=data.get("test_mode", False),
                test_server_url=data.get("test_server_url"),
            )
        except (json.JSONDecodeError, KeyError):
            # Return defaults if config is corrupted
            return cls()

    def save(self, config_dir: Path | None = None) -> None:
        """Save configuration to disk."""
        if config_dir is None:
            config_dir = get_config_dir()

        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        data = {
            "default_server": self.default_server,
            "max_referral_depth": self.max_referral_depth,
            "max_servers": self.max_servers,
            "timeout_seconds": self.timeout_seconds,
            "servers": self.servers,
        }
        if self.test_mode:
            data["test_mode"] = self.test_mode
        if self.test_server_url:
            data["test_server_url"] = self.test_server_url

        config_file.write_text(json.dumps(data, indent=2))

    def get_effective_server(self, server: str | None = None) -> str:
        """Get the effective server URL to use.

        Priority:
        1. Explicitly passed server
        2. Test server (if test mode enabled)
        3. Default server
        """
        if server:
            return server
        if self.test_mode and self.test_server_url:
            return self.test_server_url
        return self.default_server


@dataclass
class TokenStore:
    """Storage for bearer tokens."""

    tokens: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def load(cls, config_dir: Path | None = None) -> TokenStore:
        """Load tokens from disk."""
        if config_dir is None:
            config_dir = get_config_dir()

        tokens_file = config_dir / "tokens.json"
        if not tokens_file.exists():
            return cls()

        try:
            data = json.loads(tokens_file.read_text())
            return cls(tokens=data)
        except (json.JSONDecodeError, KeyError):
            return cls()

    def save(self, config_dir: Path | None = None) -> None:
        """Save tokens to disk."""
        if config_dir is None:
            config_dir = get_config_dir()

        config_dir.mkdir(parents=True, exist_ok=True)
        tokens_file = config_dir / "tokens.json"

        # Set restrictive permissions on tokens file (Unix only)
        tokens_file.write_text(json.dumps(self.tokens, indent=2))
        if sys.platform != "win32":
            tokens_file.chmod(0o600)

    def get_token(self, server: str) -> str | None:
        """Get bearer token for a server."""
        token_data = self.tokens.get(server)
        if not token_data:
            return None
        return token_data.get("token")

    def set_token(self, server: str, token: str, expires_at: str | None = None) -> None:
        """Store bearer token for a server."""
        self.tokens[server] = {"token": token}
        if expires_at:
            self.tokens[server]["expires_at"] = expires_at

    def remove_token(self, server: str) -> None:
        """Remove token for a server."""
        self.tokens.pop(server, None)


@dataclass
class IdentityStore:
    """Storage for MRS identity."""

    identity_id: str | None = None
    public_key: str | None = None  # base64 encoded
    private_key: str | None = None  # base64 encoded
    key_id: str | None = None

    @classmethod
    def load(cls, config_dir: Path | None = None) -> IdentityStore:
        """Load identity from disk."""
        if config_dir is None:
            config_dir = get_config_dir()

        identity_file = config_dir / "identity.json"
        if not identity_file.exists():
            return cls()

        try:
            data = json.loads(identity_file.read_text())
            return cls(
                identity_id=data.get("id"),
                public_key=data.get("public_key"),
                private_key=data.get("private_key"),
                key_id=data.get("key_id"),
            )
        except (json.JSONDecodeError, KeyError):
            return cls()

    def save(self, config_dir: Path | None = None) -> None:
        """Save identity to disk."""
        if config_dir is None:
            config_dir = get_config_dir()

        config_dir.mkdir(parents=True, exist_ok=True)
        identity_file = config_dir / "identity.json"

        data: dict[str, Any] = {}
        if self.identity_id:
            data["id"] = self.identity_id
        if self.public_key:
            data["public_key"] = self.public_key
        if self.private_key:
            data["private_key"] = self.private_key
        if self.key_id:
            data["key_id"] = self.key_id

        identity_file.write_text(json.dumps(data, indent=2))
        # Set restrictive permissions (Unix only)
        if sys.platform != "win32":
            identity_file.chmod(0o600)

    def has_identity(self) -> bool:
        """Check if identity is configured."""
        return bool(self.identity_id and self.public_key and self.key_id)

    def has_private_key(self) -> bool:
        """Check if private key is available for signing."""
        return bool(self.private_key)
