# MRS Client Quickstart

From a fresh clone:

```bash
git clone https://github.com/mpesce/mrs-client.git
cd mrs-client

./scripts/bootstrap.sh
./scripts/verify.sh
```

If verification passes, the CLI is ready:

```bash
source .venv/bin/activate
mrs --help
mrs info --server http://127.0.0.1:8000
```

For auth-required operations (`register`, `release`, `list`):

```bash
mrs identity create --username yourname --server localhost
mrs identity login --server http://127.0.0.1:8000 --token YOUR_TOKEN
```
