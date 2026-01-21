# Sentinel's Journal

## 2025-01-21 - Generic Error Responses
**Vulnerability:** API endpoints were catching exceptions and returning `str(e)` in the 500 response. This could leak sensitive internal details (secrets, file paths, stack traces) to the client.
**Learning:** Even seemingly harmless exception messages can contain secrets if those secrets are part of the error context (e.g. "Connection failed to user:password@host").
**Prevention:** Always sanitize error responses sent to the client. Log the full details server-side, but return a generic "Internal Server Error" to the client.
