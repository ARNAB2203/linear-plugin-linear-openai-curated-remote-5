# ClearBooks MVP specification

## User roles

| Role | Main capability |
| --- | --- |
| Owner | Review health, approve filing drafts, see proof and audit trail |
| Accountant | Import data and resolve matching exceptions |
| CA/CS | Prepare a filing draft, attach evidence, explain exceptions |
| Admin | Manage users, company settings, and integrations |

## MVP user stories

1. As an owner, I can see whether books, bank data, sales, and purchase data are ready for review.
2. As an accountant, I can view exceptions and mark them resolved or escalate them to the CA.
3. As a CA, I can see the evidence required before a return goes to the owner.
4. As an owner, I can approve a draft filing only when the review data is visible.
5. As an owner, I can retrieve the acknowledgement, challan, or filing proof after filing.

## Functional requirements

### Dashboard

- Four health indicators: bank reconciliation, unmatched transactions, input tax at risk, and filing progress.
- Priority action feed ordered by risk and deadline.
- Data-health bars for bank-to-books, sales-to-GSTR-1, and purchases-to-GSTR-2B.

### Reconciliation

- List exception source, amount, recommended action, and status.
- Support `open`, `resolved`, and `escalated` states.
- Preserve a status-change audit event.

### Filing control

- Track filing type, period, preparer, evidence status, owner approval, and filing status.
- Only a `draft` filing can be owner-approved in this MVP.
- A real production workflow must enforce evidence gates server-side.

## API contract

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/dashboard` | Dashboard summary, actions, health bars |
| GET | `/api/exceptions` | Reconciliation exceptions |
| PATCH | `/api/exceptions/{id}` | Change an exception's status |
| GET | `/api/filings` | Filing list |
| POST | `/api/filings/{id}/approve` | Record owner approval of a draft |
| GET/POST | `/api/documents` | List or upload an evidence document |
| GET/POST | `/api/ca-tasks` | List or create a CA task |
| PATCH | `/api/ca-tasks/{id}` | Mark a CA task open or done |
| GET | `/api/audit-events` | Recent demonstration audit trail |

## Production milestones

1. PostgreSQL, tenant isolation, encrypted document storage, user authentication, and role-based authorization.
2. Tally/Busy/Zoho import adapters and bank-statement parsers.
3. GST/GSTR-2B read-only integration through an authorised provider; do not store portal passwords.
4. Reconciliation rules, human review queues, evidence attachments, and immutable audit logging.
5. Penetration test, data-retention policy, backups, CA-reviewed compliance workflows, and pilot onboarding.

## Core entities

`Company`, `User`, `Transaction`, `Invoice`, `ReconciliationException`, `Filing`, `EvidenceDocument`, `Approval`, and `AuditEvent`.

