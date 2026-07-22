# Security Rules

## Input Validation
- Always validate and sanitize user inputs
- Use parameterized queries for database operations
- Implement input length limits and type checking
- Escape output data to prevent XSS

## Authentication & Authorization
- Use established libraries (bcrypt, argon2) for password hashing
- Implement proper session management with secure tokens
- Apply principle of least privilege for permissions
- Use rate limiting on authentication endpoints

## Secrets Management
- Never commit secrets, API keys, or credentials to source control
- Use environment variables or dedicated secrets management
- Rotate credentials regularly
- Implement proper key derivation for encryption

## Secure Coding Patterns
- Avoid `eval()`, `exec()`, and dynamic code execution
- Use safe deserialization practices
- Implement proper error handling without leaking stack traces
- Apply Content Security Policy (CSP) headers

## Dependency Security
- Keep dependencies updated to latest secure versions
- Audit dependencies for known vulnerabilities
- Use lock files for reproducible builds
- Minimize dependency surface area

## Code Review Checklist
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all user-supplied data
- [ ] Parameterized queries for database access
- [ ] Proper error handling without information leakage
- [ ] Authentication and authorization checks in place
- [ ] Secure communication (HTTPS, TLS)
- [ ] Rate limiting on sensitive endpoints
