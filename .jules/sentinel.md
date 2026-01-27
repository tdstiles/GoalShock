# Sentinel's Journal

## 2025-01-21 - Generic Error Responses
**Vulnerability:** API endpoints were catching exceptions and returning `str(e)` in the 500 response. This could leak sensitive internal details (secrets, file paths, stack traces) to the client.
**Learning:** Even seemingly harmless exception messages can contain secrets if those secrets are part of the error context (e.g. "Connection failed to user:password@host").
**Prevention:** Always sanitize error responses sent to the client. Log the full details server-side, but return a generic "Internal Server Error" to the client.

## 2025-05-24 - Content Security Policy & Documentation
**Vulnerability:** Implementing a strict default Content Security Policy (CSP) (`default-src 'self'`) unexpectedly broke the interactive API documentation (Swagger UI/ReDoc) because they rely on external CDNs (cdn.jsdelivr.net).
**Learning:** Security controls like CSP must account for development tools embedded in production builds. Strictly blocking external scripts breaks standard FastAPI documentation features.
**Prevention:** Whitelist necessary CDNs for documentation tools in the CSP configuration, or serve documentation assets locally/self-hosted to maintain a strict policy.
