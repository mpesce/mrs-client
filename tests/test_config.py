"""Tests for configuration management."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

from mrs_client.config import (
    Config,
    TokenStore,
    IdentityStore,
    get_config_dir,
)


class TestGetConfigDir:
    """Tests for platform-appropriate config directory."""

    def test_returns_path(self) -> None:
        config_dir = get_config_dir()
        assert isinstance(config_dir, Path)

    def test_contains_mrs(self) -> None:
        config_dir = get_config_dir()
        assert "mrs" in str(config_dir).lower()


class TestConfig:
    """Tests for Config class."""

    def test_defaults(self) -> None:
        config = Config()
        assert config.default_server == "https://owen.iz.net"
        assert config.max_referral_depth == 5
        assert config.max_servers == 20
        assert config.timeout_seconds == 30.0
        assert config.test_mode is False

    def test_load_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config.load(Path(tmpdir))
            assert config.default_server == "https://owen.iz.net"

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Save config
            config = Config(
                default_server="https://test.example.com",
                max_referral_depth=10,
            )
            config.save(config_dir)

            # Load it back
            loaded = Config.load(config_dir)
            assert loaded.default_server == "https://test.example.com"
            assert loaded.max_referral_depth == 10

    def test_get_effective_server_explicit(self) -> None:
        config = Config(default_server="https://default.com")
        assert config.get_effective_server("https://explicit.com") == "https://explicit.com"

    def test_get_effective_server_default(self) -> None:
        config = Config(default_server="https://default.com")
        assert config.get_effective_server(None) == "https://default.com"

    def test_get_effective_server_test_mode(self) -> None:
        config = Config(
            default_server="https://default.com",
            test_mode=True,
            test_server_url="https://test.com",
        )
        assert config.get_effective_server(None) == "https://test.com"

    def test_get_effective_server_test_mode_explicit_override(self) -> None:
        config = Config(
            default_server="https://default.com",
            test_mode=True,
            test_server_url="https://test.com",
        )
        assert config.get_effective_server("https://explicit.com") == "https://explicit.com"


class TestTokenStore:
    """Tests for TokenStore class."""

    def test_empty_store(self) -> None:
        store = TokenStore()
        assert store.get_token("https://example.com") is None

    def test_set_and_get_token(self) -> None:
        store = TokenStore()
        store.set_token("https://example.com", "my-token")
        assert store.get_token("https://example.com") == "my-token"

    def test_set_token_with_expiry(self) -> None:
        store = TokenStore()
        store.set_token("https://example.com", "my-token", "2026-12-31T23:59:59Z")
        assert store.get_token("https://example.com") == "my-token"
        assert store.tokens["https://example.com"]["expires_at"] == "2026-12-31T23:59:59Z"

    def test_remove_token(self) -> None:
        store = TokenStore()
        store.set_token("https://example.com", "my-token")
        store.remove_token("https://example.com")
        assert store.get_token("https://example.com") is None

    def test_remove_nonexistent_token(self) -> None:
        store = TokenStore()
        # Should not raise
        store.remove_token("https://example.com")

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Save tokens
            store = TokenStore()
            store.set_token("https://example.com", "my-token")
            store.save(config_dir)

            # Load them back
            loaded = TokenStore.load(config_dir)
            assert loaded.get_token("https://example.com") == "my-token"


class TestIdentityStore:
    """Tests for IdentityStore class."""

    def test_empty_store(self) -> None:
        store = IdentityStore()
        assert store.has_identity() is False
        assert store.has_private_key() is False

    def test_with_identity(self) -> None:
        store = IdentityStore(
            identity_id="test@example.com",
            public_key="cHVibGljLWtleQ==",
            private_key="cHJpdmF0ZS1rZXk=",
            key_id="key-2026-01",
        )
        assert store.has_identity() is True
        assert store.has_private_key() is True

    def test_with_identity_no_private_key(self) -> None:
        store = IdentityStore(
            identity_id="test@example.com",
            public_key="cHVibGljLWtleQ==",
            key_id="key-2026-01",
        )
        assert store.has_identity() is True
        assert store.has_private_key() is False

    def test_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Save identity
            store = IdentityStore(
                identity_id="test@example.com",
                public_key="cHVibGljLWtleQ==",
                private_key="cHJpdmF0ZS1rZXk=",
                key_id="key-2026-01",
            )
            store.save(config_dir)

            # Load it back
            loaded = IdentityStore.load(config_dir)
            assert loaded.identity_id == "test@example.com"
            assert loaded.public_key == "cHVibGljLWtleQ=="
            assert loaded.private_key == "cHJpdmF0ZS1rZXk="
            assert loaded.key_id == "key-2026-01"
