# Security review: Localr

A self-audit of this project: what was wrong, what I changed, and what is still open. Severity ratings are my own judgement for a small hobby app, not a formal scoring.

## Findings and fixes

| # | Finding | Rating | Fix |
|---|---------|--------|-----|
| 1 | **Hardcoded `secret_key`** in source. Anyone with the repo could forge session cookies and log in as any user. | High | Key now comes from `SECRET_KEY` in the environment; the app refuses to start without a strong one. The old key must be treated as compromised and rotated. |
| 2 | **No CSRF protection.** Any website could make a logged-in user's browser POST to `/save`, `/skip`, delete routes, etc. | High | Per-session random token, checked in a `before_request` hook for every POST (form field or `X-CSRFToken` header), compared with `hmac.compare_digest`. |
| 3 | **DOM / stored XSS sinks.** `results.html` rebuilt cards with `innerHTML` from AI-generated text, and `saved.html` passed an HTML string to Leaflet's `bindPopup`. `/save` also stored whatever text the client sent. Combined with #2, a third-party page could plant a payload in a victim's saved list. | High | All dynamic content is built with DOM APIs and `textContent`; Leaflet receives a DOM node. Server side, every field is length-capped and type-checked. Photo links must be `https://`. Jinja autoescaping (already on) covers server-rendered pages. |
| 4 | **Costly endpoints open to anyone.** `/search`, `/place`, `/images` needed no login but call paid APIs. | Medium | `@login_required` plus per-user rate limits. |
| 5 | **No rate limiting on login/register**, so brute force was unrestricted. | Medium | In-memory sliding-window limiter: login 10 per 5 min per IP and 5 per 5 min per username; register 5 per hour per IP. |
| 6 | **Logout was a GET request**, so another site could log users out. | Low | POST-only, with CSRF token. |
| 7 | **Untrusted LLM input and output.** City and mood went straight into the prompt; the reply was parsed with a bare `except` and rendered as-is. | Medium | Mood is checked against an allow-list, city against a strict pattern; user values are passed to the model as JSON data, not interpolated into instructions; replies are parsed defensively and coerced to a fixed schema with length caps. Prompt injection cannot be fully prevented, so the goal is to limit the damage to some odd (escaped) text on a card. |
| 8 | **Outbound HTTP calls had no timeouts** and failures were swallowed or crashed the request. | Low | 10 s timeouts, specific exceptions, logging that never includes API keys. |
| 9 | **Session cookie and session handling.** No explicit flags. | Medium | `HttpOnly`, `SameSite=Lax`, `Secure` (default on), 7-day lifetime, Flask-Login `session_protection="strong"`, and `session.clear()` on login/register/logout (prevents session fixation). |
| 10 | **Database committed to the repo** (`instance/localr.db`, with a user's password hash), and `.gitignore` did not exclude it. | Medium | Removed; `*.db` and `instance/` ignored. **If the repo was ever public, the file remains in git history**: rewrite history (e.g. `git filter-repo`) or treat that hash as exposed and change that password anywhere it was reused. |
| 11 | **Weak account hygiene.** No username or password rules; login timing differed for unknown users. | Low | Username pattern, password 10-128 characters, a dummy hash check so unknown and known users take similar time, generic login error. |
| 12 | **No security headers.** | Low | CSP, `X-Content-Type-Options`, `X-Frame-Options`/`frame-ancestors`, `Referrer-Policy`, `Permissions-Policy`, HSTS when cookies are Secure. |
| 13 | **Unencoded values in a URL** (`/place?name={{ place.name }}`). | Low | `|urlencode`. |
| 14 | **Misleading product claims** (fake quotes, fake "mentions" counts, fake site statistics, "reads real Reddit posts"). Not a classic vulnerability, but a data-integrity and trust problem. | n/a | Removed everywhere; output is labelled as AI-generated. Google results scraping (a terms-of-service problem and broken in practice) was removed along with its dependency. |

## Open items and accepted risks

- **CSP still allows `'unsafe-inline'` scripts** because the templates use inline `<script>` blocks and `onclick` attributes. Next step: move to external JS or a nonce-based CSP, which would make the XSS fixes defence-in-depth rather than the only line of defence.
- **No Subresource Integrity** on third-party scripts (Hammer.js from cdnjs, Leaflet from unpkg). Generate hashes with `curl -s <url> | openssl dgst -sha384 -binary | openssl base64 -A` and add `integrity="sha384-..." crossorigin="anonymous"`, or self-host the files. I could not verify hashes offline, so I did not guess.
- **Rate limiter is in-memory and per-process**: it resets on restart and is not shared between workers. Use Flask-Limiter with Redis for real deployments. The per-username limit can also be abused to lock a specific user out for five minutes (a deliberate trade-off).
- **`/save` and `/skip` trust the name and summary the browser sends.** This only affects the user's own list now (escaped everywhere, length-capped), but a stricter design would keep results server-side and save by ID.
- **No email verification, password reset, password change page or MFA.** Registration still reveals whether a username is taken.
- **No audit logging or alerting** for failed logins or rate-limit hits.
- **Dependencies are version-ranged, not pinned or scanned.** Run `pip freeze` into a lock file and `pip-audit` in CI.
- **TLS is not handled by the app.** Deploy behind a reverse proxy with HTTPS and set `BEHIND_PROXY=1` so rate limits see real client IPs.
- **City autocomplete calls Nominatim from the browser.** This sends what users type to a third party, and Nominatim's public usage policy may not permit autocomplete-style use; check it before deploying.

## Verification

Run during this review:

- `python -m unittest tests.test_security -v`: 10 tests for input validation, the rate limiter, the CSRF helpers and LLM-output sanitising (all pass; one test caught a real ordering bug in my sanitiser, now fixed).
- All templates parse, and rendering them with an `<img onerror>` payload shows it escaped on results, detail and saved pages; every POST form contains a CSRF token.

**Not run:** the full Flask app end to end (Flask-SQLAlchemy and Flask-Login could not be installed in the review environment) and the JavaScript changes in a real browser. Check these yourself after installing the requirements, with `SESSION_COOKIE_SECURE=0` for local http:

```bash
curl -i -X POST localhost:5000/login -d 'username=a&password=b'   # expect 400 (no CSRF token)
curl -i localhost:5000/logout                                      # expect 405
curl -i 'localhost:5000/place?name=x&city=Paris'                   # expect 302 to /login
curl -I localhost:5000/login                                       # expect CSP, nosniff, X-Frame-Options
```

Then in the browser: swipe, save, open details and the saved map; submit six wrong passwords and confirm you get the 429 page; save a place named `<img src=x onerror=alert(1)>` (edit the request in dev tools) and confirm nothing executes.
