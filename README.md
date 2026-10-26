# URL Shortener API

A small URL-shortener service built with Flask, Flask-SQLAlchemy and SQLite.

- Create short links (optional custom alias, optional expiry)
- Redirect `GET /{code}` to the original URL (404 unknown, 410 expired)
- Click counting with `GET /links/{code}/stats`
- URL / alias / expiry validation with clear error messages

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py                    # http://127.0.0.1:5000
```

The SQLite database (`instance/links.db`) is created automatically on first start.

## Project layout

```
app/__init__.py   app factory, DB setup, JSON error handlers
app/models.py     Link model
app/routes.py     the three endpoints
app/utils.py      validation helpers, code generator, time helpers
run.py            entry point
tests/test_api.py pytest suite
```

## Endpoints

| Method | Path                | Success | Errors                                            |
|--------|---------------------|---------|---------------------------------------------------|
| POST   | `/links`            | 201     | 400 invalid input, 409 alias already in use       |
| GET    | `/{code}`           | 307     | 404 unknown code, 410 expired                     |
| GET    | `/links/{code}/stats` | 200   | 404 unknown code                                  |
| GET    | `/ping`             | 200     | health check                                      |

All errors are JSON: `{"error": "human readable message"}`.

### Create a link

Body: `original_url` (required), `custom_alias` (optional, 3-32 chars of letters,
digits, `-`, `_`), `expires_at` (optional ISO 8601, must be in the future; a
timezone offset is honoured, no offset means UTC).

```bash
curl -X POST http://127.0.0.1:5000/links \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com/very/long/path"}'
# 201 {"short_code":"aZ3kQ9","short_url":"http://127.0.0.1:5000/aZ3kQ9",
#      "original_url":"https://example.com/very/long/path","expires_at":null}

curl -X POST http://127.0.0.1:5000/links \
  -H "Content-Type: application/json" \
  -d '{"original_url": "https://example.com", "custom_alias": "promo", "expires_at": "2026-12-31T23:59:59Z"}'

# duplicate alias
# 409 {"error":"Alias 'promo' is already in use. Choose a different alias or leave it out to get a generated code."}
```

### Follow a link

```bash
curl -i http://127.0.0.1:5000/promo
# HTTP/1.1 307 TEMPORARY REDIRECT
# Location: https://example.com

curl -i http://127.0.0.1:5000/unknown   # 404 {"error":"Short code 'unknown' not found"}
# after expiry:                          # 410 {"error":"This link expired at 2026-12-31T23:59:59Z"}
```

### Stats

```bash
curl http://127.0.0.1:5000/links/promo/stats
# {"short_code":"promo","original_url":"https://example.com","total_clicks":3,
#  "last_clicked_at":"2026-10-26T09:15:00Z","created_at":"...","expires_at":"2026-12-31T23:59:59Z","expired":false}
```

## Design notes

- **307 + `Cache-Control: no-store`**: a cached (301) redirect would let browsers skip the
  service, so clicks would go uncounted.
- **Atomic click counter**: incremented with a single SQL `UPDATE`, so concurrent clicks are
  not lost.
- **Duplicate aliases** are rejected by the database `UNIQUE` constraint, not "check then
  insert", so a race can never create two links with the same code. Randomly generated
  codes that collide are retried automatically.
- **Expired links** return 410 and do not count as clicks; their stats stay readable.
  A link is expired from the exact moment `expires_at` is reached.
- Times are stored as naive UTC and returned as ISO 8601 with a `Z` suffix.
- Codes and aliases are case-sensitive; `links` and `ping` are reserved.

## Tests

```bash
pytest
```

The suite uses a temporary database per test and a fake clock, so expiry is tested
without waiting.