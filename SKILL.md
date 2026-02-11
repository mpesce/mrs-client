---
name: mrs-client-dev
description: Work on the Mixed Reality Service client library and CLI. Use for client register/search/release behavior, CLI UX, auth/signature handling, URI validation/sanitization, and compatibility with mrs-server response contracts.
---

# MRS Client Dev

1. Activate virtual environment.
   - `source .venv/bin/activate`

2. Run client tests before changes.
   - `pytest -q`

3. Implement focused client/CLI changes.
   - Keep compatibility with current server contracts.
   - Validate outbound `service_point` before register.
   - Sanitize inbound untrusted `service_point` values.

4. Re-run tests after edits.
   - `pytest -q`

5. Verify end-to-end behavior against local server.
   - Use `mrs` CLI for register/search/release flow.

6. Confirm release gates when requested.
   - Use workspace harnesses from `../scripts/` as directed.

## Core behaviors
- Search results parsing
- Register request validation
- Release/list auth behavior
- Identity and token handling

## Security rules
- Never pass malformed URI data through to downstream agent flows.
- Do not weaken validation/sanitization without explicit approval and tests.
