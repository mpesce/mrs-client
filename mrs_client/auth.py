"""Authentication management for MRS client."""

from __future__ import annotations

import base64
import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from mrs_client.config import IdentityStore, TokenStore, get_config_dir
from mrs_client.exceptions import MRSAuthError
from mrs_client.models import Identity


class AuthManager:
    """Handles identity, keys, and request signing."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize auth manager.

        Args:
            config_dir: Configuration directory. Uses platform default if None.
        """
        self.config_dir = config_dir or get_config_dir()
        self._identity_store: IdentityStore | None = None
        self._token_store: TokenStore | None = None
        self._identity: Identity | None = None

    @property
    def identity_store(self) -> IdentityStore:
        """Get or load identity store."""
        if self._identity_store is None:
            self._identity_store = IdentityStore.load(self.config_dir)
        return self._identity_store

    @property
    def token_store(self) -> TokenStore:
        """Get or load token store."""
        if self._token_store is None:
            self._token_store = TokenStore.load(self.config_dir)
        return self._token_store

    def get_identity(self) -> Identity | None:
        """Get current identity, loading from disk if needed."""
        if self._identity is not None:
            return self._identity

        store = self.identity_store
        if not store.has_identity():
            return None

        assert store.identity_id is not None
        assert store.public_key is not None
        assert store.key_id is not None

        self._identity = Identity(
            id=store.identity_id,
            public_key=base64.b64decode(store.public_key),
            private_key=(
                base64.b64decode(store.private_key) if store.private_key else None
            ),
            key_id=store.key_id,
        )
        return self._identity

    def generate_identity(self, username: str, domain: str) -> Identity:
        """Generate new Ed25519 keypair for identity.

        Args:
            username: Username part of identity
            domain: Domain part of identity

        Returns:
            New Identity with generated keys
        """
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        identity = Identity(
            id=f"{username}@{domain}",
            public_key=public_key.public_bytes_raw(),
            private_key=private_key.private_bytes_raw(),
            key_id=f"key-{datetime.utcnow().strftime('%Y-%m')}",
        )

        self._save_identity(identity)
        self._identity = identity
        return identity

    def _save_identity(self, identity: Identity) -> None:
        """Save identity to disk."""
        store = IdentityStore(
            identity_id=identity.id,
            public_key=base64.b64encode(identity.public_key).decode(),
            private_key=(
                base64.b64encode(identity.private_key).decode()
                if identity.private_key
                else None
            ),
            key_id=identity.key_id,
        )
        store.save(self.config_dir)
        self._identity_store = store

    def get_bearer_token(self, server: str) -> str | None:
        """Get stored bearer token for a server."""
        return self.token_store.get_token(server)

    def store_bearer_token(
        self, server: str, token: str, expires_at: str | None = None
    ) -> None:
        """Store bearer token for a server."""
        self.token_store.set_token(server, token, expires_at)
        self.token_store.save(self.config_dir)

    def remove_bearer_token(self, server: str) -> None:
        """Remove bearer token for a server."""
        self.token_store.remove_token(server)
        self.token_store.save(self.config_dir)

    def get_auth_headers(self, server: str) -> dict[str, str]:
        """Get authentication headers for a server.

        Returns Bearer token header if available.
        """
        token = self.get_bearer_token(server)
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def sign_request(
        self,
        method: str,
        url: str,
        body: bytes | None,
        identity: Identity | None = None,
    ) -> dict[str, str]:
        """Generate HTTP Signature headers for a request.

        This implements RFC 9421 HTTP Message Signatures with Ed25519.

        Args:
            method: HTTP method
            url: Full request URL
            body: Request body (for POST/PUT)
            identity: Identity to sign with (uses current if None)

        Returns:
            Dict of headers to add to request

        Raises:
            MRSAuthError: If signing fails
        """
        if identity is None:
            identity = self.get_identity()

        if identity is None:
            raise MRSAuthError("No identity configured")

        if identity.private_key is None:
            raise MRSAuthError("Cannot sign without private key")

        # Reconstruct private key
        private_key = Ed25519PrivateKey.from_private_bytes(identity.private_key)

        # Parse URL to get path
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"

        headers: dict[str, str] = {}

        # Compute content digest if body present
        content_digest = None
        if body:
            digest = hashlib.sha256(body).digest()
            content_digest = f"sha-256=:{base64.b64encode(digest).decode()}:"
            headers["Content-Digest"] = content_digest

        # Build signature base
        created = int(time.time())
        key_url = (
            f"https://{identity.domain}/.well-known/mrs/keys/"
            f"{identity.username}#{identity.key_id}"
        )

        # Signature components
        sig_components = ['"@method"', '"@path"']
        sig_base_parts = [f'"@method": {method}', f'"@path": {path}']

        if content_digest:
            sig_components.append('"content-digest"')
            sig_base_parts.append(f'"content-digest": {content_digest}')

        sig_components.append('"mrs-identity"')
        sig_base_parts.append(f'"mrs-identity": {identity.id}')

        sig_params = (
            f"({' '.join(sig_components)}); "
            f'keyid="{key_url}"; created={created}; alg="ed25519"'
        )
        sig_base_parts.append(f'"@signature-params": {sig_params}')

        sig_base = "\n".join(sig_base_parts)

        # Sign
        signature = private_key.sign(sig_base.encode())
        sig_b64 = base64.b64encode(signature).decode()

        headers["Signature-Input"] = f"sig1={sig_params}"
        headers["Signature"] = f"sig1=:{sig_b64}:"
        headers["MRS-Identity"] = identity.id

        return headers

    def export_public_key(self) -> dict[str, Any]:
        """Export public key in MRS format.

        Returns:
            Dict suitable for JSON serialization
        """
        identity = self.get_identity()
        if identity is None:
            raise MRSAuthError("No identity configured")

        return {
            "id": identity.id,
            "public_key": {
                "type": "Ed25519",
                "key": base64.b64encode(identity.public_key).decode(),
            },
            "key_id": identity.key_id,
        }


def verify_signature(
    method: str,
    path: str,
    body: bytes | None,
    headers: dict[str, str],
    public_key: bytes,
) -> bool:
    """Verify an HTTP signature.

    This is primarily for testing; servers do the real verification.

    Args:
        method: HTTP method
        path: Request path
        body: Request body
        headers: Request headers including signature
        public_key: Ed25519 public key bytes

    Returns:
        True if signature is valid
    """
    try:
        sig_input = headers.get("Signature-Input", "")
        signature_header = headers.get("Signature", "")
        mrs_identity = headers.get("MRS-Identity", "")
        content_digest = headers.get("Content-Digest")

        if not all([sig_input, signature_header, mrs_identity]):
            return False

        # Parse signature input to extract components
        # Format: sig1=("@method" "@path" ...); keyid="..."; created=...; alg="ed25519"
        if not sig_input.startswith("sig1="):
            return False

        sig_params = sig_input[5:]  # Remove "sig1="

        # Reconstruct signature base
        sig_base_parts = [f'"@method": {method}', f'"@path": {path}']

        if content_digest:
            sig_base_parts.append(f'"content-digest": {content_digest}')

        sig_base_parts.append(f'"mrs-identity": {mrs_identity}')
        sig_base_parts.append(f'"@signature-params": {sig_params}')

        sig_base = "\n".join(sig_base_parts)

        # Extract signature value
        if not signature_header.startswith("sig1=:") or not signature_header.endswith(
            ":"
        ):
            return False
        sig_b64 = signature_header[6:-1]  # Remove "sig1=:" and trailing ":"
        signature = base64.b64decode(sig_b64)

        # Verify
        pub_key = Ed25519PublicKey.from_public_bytes(public_key)
        pub_key.verify(signature, sig_base.encode())
        return True

    except Exception:
        return False
