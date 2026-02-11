---
name: mrs-client-dev
description: "Work on the MRS client library/CLI: register/search/release flows, auth/signature handling, URI validation, and compatibility with mrs-server contracts. Use when changing client behavior, CLI UX, parsing, or safety controls."
---

# MRS Client Dev Skill

## Use this workflow
1. Activate env: `source .venv/bin/activate`
2. Run tests first: `pytest -q`
3. Implement change in library and CLI layers as needed
4. Re-run tests
5. Run a local smoke flow against `mrs-server`

## Project specifics
- Library package: `mrs_client`
- CLI package: `mrs_cli`
- Main command: `mrs`
- Core methods: `search`, `register`, `release`, identity login/verify

## Safety-critical rules
- Validate outbound `service_point` before register.
- Sanitize inbound `service_point` from untrusted search results.
- Keep behavior compatible with server contracts.

## Required checks before shipping
- `pytest -q` passes
- CLI `mrs search` works end-to-end against local server
- malformed URI samples are rejected/neutralized
