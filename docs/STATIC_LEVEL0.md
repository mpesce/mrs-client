# Static MRS (Level 0)

Level 0 is a static JSON map of space→URI registrations at a well-known URL.

## Use case
- immediate publish/discover value
- no auth, no mutation API, no federation guarantees

## JSON shape

```json
{
  "mrs_static_version": "0.1",
  "generated_at": "2026-02-11T00:00:00Z",
  "registrations": [
    {
      "id": "reg_example",
      "space": {
        "type": "sphere",
        "center": {"lat": -33.8568, "lon": 151.2153, "ele": 0},
        "radius": 50
      },
      "service_point": "https://example.com/place",
      "foad": false,
      "owner": "publisher@example.com",
      "created": "2026-02-11T00:00:00Z",
      "updated": "2026-02-11T00:00:00Z"
    }
  ]
}
```

## Lint helper
Validate a dataset before publishing:

```bash
python scripts/static-mrs-lint.py /path/to/mrs-static.json
# strict mode (warnings fail build)
python scripts/static-mrs-lint.py /path/to/mrs-static.json --strict
```

## Query helper
Use the included script:

```bash
python scripts/static-mrs-query.py \
  --source /path/to/mrs-static.json \
  --lat -33.8568 --lon 151.2153 --range 100 --json
```

`--source` may also be an `https://...` URL.
