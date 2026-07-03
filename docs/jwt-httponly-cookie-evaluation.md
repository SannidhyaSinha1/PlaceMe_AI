# Evaluation: moving the JWT from localStorage to httpOnly cookies

**Status: recommended, not yet implemented.** This changes the API contract
and the frontend auth flow, so it ships only as its own reviewed change.

## Current state

- The API returns the JWT in the login/register response body; the frontend
  stores it in `localStorage` ([api.js](../frontend/src/services/api.js)) and
  attaches it as a `Bearer` header.
- Risk: any XSS (or a compromised npm dependency running in the page) can read
  `localStorage` and exfiltrate the token. The token is currently valid for
  24h, so a single leak is long-lived.

## Mitigations already in place

- Strict CORS allowlist (single frontend origin in production).
- Security headers on every response; `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, HSTS in production.
- React escapes rendered content by default; no `dangerouslySetInnerHTML`
  in the codebase today.
- Rate limiting on auth endpoints (brute-force cost).

## Proposed design (dual-mode, backward compatible)

1. On login/register, ALSO set the token as a cookie:
   `Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=86400`.
2. `get_current_user` accepts the Bearer header first (unchanged contract for
   existing clients), falling back to the cookie.
3. Frontend drops localStorage over time: axios gains `withCredentials: true`;
   the interceptor and the `token` slice field become derived state
   (`/auth/me` succeeds ⇒ session exists).
4. Add a `POST /auth/logout` that clears the cookie (client-side `logout`
   reducer alone can't remove an httpOnly cookie).

## Costs / gotchas

- **CSRF becomes a real concern** once auth rides on cookies. `SameSite=Lax`
  covers navigations and blocks cross-site POSTs in modern browsers; for
  defense in depth add a double-submit CSRF token on mutating routes.
- **Cross-origin deployment** (Vercel frontend + Render API on different
  registrable domains) requires `SameSite=None; Secure` — weakening the CSRF
  posture above — or serving the API under the same site via a rewrite/proxy
  (Vercel rewrite of `/api/*` → Render) which keeps `SameSite=Lax` viable.
  This is the main open decision.
- Local dev must keep working over plain http (`Secure` flag conditional on
  `settings.is_production`).
- The Gmail OAuth `state` JWT flow is unaffected (query param, not storage).

## Recommendation

Adopt the dual-mode design after settling the deployment-topology question
(same-site proxy strongly preferred). Effort ≈ 1 focused day including tests.
Until then the current posture is acceptable for a student project given the
mitigations above; the 24h token lifetime could be shortened to 12h cheaply.
