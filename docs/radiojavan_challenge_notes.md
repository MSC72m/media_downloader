# RadioJavan Cloudflare Challenge Notes

## Snapshot (2026-02-14)

- `https://www.radiojavan.com/*` endpoints intermittently return Cloudflare challenge behavior.
- Requests to blocked endpoints can return `cf-mitigated: challenge` with `403`.
- `play.radiojavan.com` may still load while `www.radiojavan.com` is challenged.
- Browser traffic shows Cloudflare JSD/oneshot endpoints under:
  - `/cdn-cgi/challenge-platform/...`
- A valid Cloudflare clearance cookie observed from browser context:
  - `cf_clearance` scoped to `.radiojavan.com`.

## Important Detection Detail

Cloudflare JSD script references can appear in normal pages. The string
`cdn-cgi/challenge-platform/scripts/jsd/main.js` alone is not a reliable
challenge indicator.

Reliable indicators are:

- Response header `cf-mitigated: challenge`
- `window._cf_chl_opt` in HTML
- Challenge page titles/content (`Just a moment...`, `Attention Required! | Cloudflare`)
- Orchestrate/challenge page routes (`/cdn-cgi/challenge-platform/h/.../chl_page`)

## Current Downloader Behavior

- RadioJavan host API lookup can be challenged on `www.radiojavan.com`.
- Downloader falls back through host candidates and best-effort URL construction.
- When challenge persists, download may still fail with `403`.

## Practical Hardening Strategy

1. Prefer non-challenged discovery sources first (`play.radiojavan.com` search extraction).
2. Reuse browser-acquired clearance (`cf_clearance`) and request headers when available.
3. Detect challenge via header + strong markers (avoid JSD-only false positives).
4. Retry once after session refresh, then fail fast with actionable logs.

## Why This Matters

The challenge is dynamic and can vary by IP/ASN/region/time. The robust path is
to keep challenge detection precise, session refresh conservative, and fallback
logic deterministic.
