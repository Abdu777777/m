# Arab Option — implementation baseline

## Purpose
Build a modular Arabic-first market-analysis and trade-idea platform. The initial deployment is an informational/demo environment, not a broker and not a payment processor.

## Planned modules
- Accounts: registration, verification status, account restrictions, staff roles.
- Payments: configurable payment methods; manual deposit/withdrawal requests; idempotency.
- Ledger: append-only double-entry accounting before any real-money feature.
- KYC: restricted document access, retention rules, review workflow.
- Market data: licensed provider adapters; show source and timestamp; no fabricated quotes.
- Trade ideas: publication, outcome review, transparent historical performance.
- Support: tickets and least-privilege staff access.
- Configuration: database-backed limits and feature flags with audit trail.
- Audit/reporting: event records and reconciliation exports.

## Safety gates before real-money launch
1. Legal/regulatory review for the jurisdictions served.
2. Payment provider integration and settlement/reconciliation tests.
3. Double-entry ledger, concurrency tests, duplicate-request prevention, withdrawal holds.
4. MFA for administrators, secure secrets, rate limiting, CSRF/session settings, security headers.
5. KYC data protection and restricted access.
6. Independent security review, backup/restore drill, monitoring and incident response.

## Initial policy defaults
- Deposit minimum: USD 5 (demo/manual request only).
- Withdrawal minimum: USD 10 (demo/manual request only).
- No automated transfer execution.
- Deactivate historical payment methods rather than deleting transaction references.
