"""Tests for authentication."""

import tempfile
from pathlib import Path

import pytest

from mrs_client.auth import AuthManager, verify_signature
from mrs_client.exceptions import MRSAuthError


class TestAuthManager:
    """Tests for AuthManager."""

    def test_no_identity_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            assert auth.get_identity() is None

    def test_generate_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            identity = auth.generate_identity("testuser", "example.com")

            assert identity.id == "testuser@example.com"
            assert identity.username == "testuser"
            assert identity.domain == "example.com"
            assert identity.public_key is not None
            assert identity.private_key is not None
            assert len(identity.public_key) == 32  # Ed25519 public key size

    def test_identity_persists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)

            # Generate identity
            auth1 = AuthManager(config_dir)
            identity1 = auth1.generate_identity("testuser", "example.com")

            # Create new AuthManager and verify it loads the identity
            auth2 = AuthManager(config_dir)
            identity2 = auth2.get_identity()

            assert identity2 is not None
            assert identity2.id == identity1.id
            assert identity2.public_key == identity1.public_key

    def test_bearer_token_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))

            # Store token
            auth.store_bearer_token("https://example.com", "my-token")

            # Retrieve token
            assert auth.get_bearer_token("https://example.com") == "my-token"

    def test_bearer_token_not_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            assert auth.get_bearer_token("https://nonexistent.com") is None

    def test_get_auth_headers_with_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            auth.store_bearer_token("https://example.com", "my-token")

            headers = auth.get_auth_headers("https://example.com")
            assert headers == {"Authorization": "Bearer my-token"}

    def test_get_auth_headers_without_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            headers = auth.get_auth_headers("https://example.com")
            assert headers == {}

    def test_sign_request_no_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            with pytest.raises(MRSAuthError, match="No identity"):
                auth.sign_request("POST", "https://example.com/register", None)

    def test_sign_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            identity = auth.generate_identity("testuser", "example.com")

            headers = auth.sign_request(
                "POST",
                "https://example.com/register",
                b'{"test": "data"}',
            )

            assert "Signature-Input" in headers
            assert "Signature" in headers
            assert "MRS-Identity" in headers
            assert "Content-Digest" in headers

            assert headers["MRS-Identity"] == "testuser@example.com"
            assert "sig1=" in headers["Signature-Input"]
            assert "sig1=:" in headers["Signature"]

    def test_export_public_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            auth.generate_identity("testuser", "example.com")

            key_data = auth.export_public_key()

            assert key_data["id"] == "testuser@example.com"
            assert key_data["public_key"]["type"] == "Ed25519"
            assert "key" in key_data["public_key"]

    def test_export_public_key_no_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            with pytest.raises(MRSAuthError, match="No identity"):
                auth.export_public_key()


class TestSignatureVerification:
    """Tests for signature verification."""

    def test_verify_own_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            identity = auth.generate_identity("testuser", "example.com")

            body = b'{"test": "data"}'
            headers = auth.sign_request("POST", "https://example.com/register", body)

            # Verify the signature we just created
            is_valid = verify_signature(
                method="POST",
                path="/register",
                body=body,
                headers=headers,
                public_key=identity.public_key,
            )
            assert is_valid is True

    def test_verify_tampered_signature(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth = AuthManager(Path(tmpdir))
            identity = auth.generate_identity("testuser", "example.com")

            body = b'{"test": "data"}'
            headers = auth.sign_request("POST", "https://example.com/register", body)

            # Tamper with the body
            is_valid = verify_signature(
                method="POST",
                path="/register",
                body=b'{"test": "tampered"}',
                headers=headers,
                public_key=identity.public_key,
            )
            assert is_valid is False

    def test_verify_wrong_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            auth1 = AuthManager(Path(tmpdir) / "user1")
            auth2 = AuthManager(Path(tmpdir) / "user2")

            identity1 = auth1.generate_identity("user1", "example.com")
            identity2 = auth2.generate_identity("user2", "example.com")

            body = b'{"test": "data"}'
            headers = auth1.sign_request("POST", "https://example.com/register", body)

            # Try to verify with wrong key
            is_valid = verify_signature(
                method="POST",
                path="/register",
                body=body,
                headers=headers,
                public_key=identity2.public_key,  # Wrong key
            )
            assert is_valid is False
