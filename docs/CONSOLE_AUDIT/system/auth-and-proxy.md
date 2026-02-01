# System: Auth, proxy, and headers

Auth flow (implemented)
- NextAuth with Keycloak (`console-web/src/lib/auth.ts`).
- Access token stored in NextAuth session; refresh handled via refresh token.
- `LoginButton` uses `signIn("keycloak")` and `signOut()`.

API proxy
- All browser calls go through `/api/proxy/*`.
- Proxy route: `console-web/src/app/api/proxy/[...path]/route.ts`.
  - Adds `Authorization: Bearer <accessToken>`.
  - Forwards `X-Company-Id`, `X-Client-Id`, `X-Branch-Id` when present.
  - Supports JSON and multipart (media upload).

Client wrappers
- `console-web/src/lib/api.ts`
  - Axios client to `/api/proxy`.
  - Attaches idempotency key for mutations.
  - Injects tenant headers from localStorage.
- `console-web/src/lib/api-client.ts`
  - Typed client wrappers (OpenAPI types) + RBAC helpers.

Tenant headers and localStorage
- `console:company_id`, `console:client_id`, `console:branch_id`.
- Populated via `ConsoleShell` context selectors.

Backend auth
- `truffles-api/app/services/console_auth.py` validates JWT, loads agent identity, applies RBAC and tenant context.
- `get_console_context` enforces selection gates and branch restrictions.
