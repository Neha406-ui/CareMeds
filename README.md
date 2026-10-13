# CareMeds

CareMeds is a medication-management and adherence-monitoring application for care homes. It uses a React/Vite frontend, a FastAPI backend, SQLAlchemy/Alembic, and PostgreSQL (including Supabase PostgreSQL). Authorization is enforced by the API; frontend navigation is not an authorization boundary.

## Implemented workflows

- Five account roles with separately named dashboards and role-based navigation: Admin, Doctor, Caretaker, Resident, and Family Member.
- Account activation/deactivation, token-version revocation, server-side logout, doctor/caretaker assignments, and resident-controlled family consent.
- Resident, medicine-catalog, prescription, dose-scheduling, administration-outcome, reminder, and escalation workflows.
- Explicit prescription schedule times and IANA time zones. Dose occurrences are persistent and idempotent per prescription schedule revision.
- Care-team inventory batches with expiry dates, stock receipts/issues, non-negative stock checks, reorder indicators, and transaction history.
- Family contact requests limited to actively linked family accounts and assigned care-team responses.
- Caretaker shift handovers limited to caretakers assigned to that resident; only the assigned incoming caretaker can acknowledge.
- Access-scoped adherence reports with counts for administered, refused, withheld, not administered, unable to confirm, and unresolved doses. The report rate is `administered / all occurred, non-cancelled scheduled doses`; unresolved doses remain in the denominator. Future doses are excluded.
- An append-only-through-the-API audit log for sensitive account, resident, assignment, consent, prescription, dose, inventory, escalation, contact, and handover changes. Audit-log listing is administrator-only.

## Role permission matrix

| Major action | Admin | Doctor | Caretaker | Resident | Family Member |
|---|---|---|---|---|---|
| View resident profile | All residents | Assigned residents | Assigned residents | Own profile | Explicit profile permission + active consent |
| View prescriptions / dose history | All | Assigned residents | Assigned residents | Own profile | Explicit prescription permission + active consent |
| Create/modify/discontinue a prescription | No | Only own prescriptions for currently assigned residents | No | No | No |
| Record medication administration outcome | No | No | Assigned residents | No | No |
| Acknowledge own dose reminder | No | No | No | Own doses; acknowledgement is not administration | No |
| View active medicine catalog | Yes | Yes | Yes | Yes | Yes |
| Create medicine catalog item | Yes | Yes | No | No | No |
| View inventory and stock transactions | Yes | Yes | Yes | No | No |
| Receive/issue inventory stock | Yes | No | Yes | No | No |
| Manage accounts and care assignments | Yes | No | No | No | No |
| Grant/update family consent | Revoke only | No | No | Own profile | No |
| Request resident access | No | No | No | No | Yes; resident consent required |
| Create/view family contact request | No | No | No | No | Current linked resident |
| Respond to a family contact request | All | Assigned residents | Assigned residents | No | No |
| Create shift handover | No | No | Assigned resident | No | No |
| Acknowledge shift handover | No | No | Assigned incoming caretaker | No | No |
| Review/resolve dose escalation | All | Assigned residents | Assigned residents | No | No |
| View adherence analytics | All residents | Assigned residents | Assigned residents | Own profile | Prescription-consented residents |
| View audit log | Yes | No | No | No | No |

The API returns not-found responses for many out-of-scope resident/resource IDs to avoid confirming their existence. Sensitive endpoints also check the current active assignment or consent at request time.

## Local setup (Windows PowerShell)

Requirements: Python 3.10+, Node.js 18+, and PostgreSQL. From the repository root:

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` and a unique `SECRET_KEY` in `backend\.env`. The signing key must be at least 32 characters and is mandatory for non-development deployments. Keep all database connection strings, passwords, signing keys, and Supabase service-role credentials on the backend; do not put them in `frontend\.env`, browser storage, or source control.

Apply schema migrations to the database you configured:

```powershell
Set-Location backend
alembic upgrade head
```

### Create the first administrator

Public signup is intentionally disabled: a user must not be able to choose an elevated role or gain access to resident records by self-registering. After migrations have been applied, bootstrap the first administrator from a trusted local terminal:

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
python -m app.bootstrap_admin --username admin --full-name "CareMeds Administrator"
```

The command prompts twice for the password without echoing it. Choose a strong unique password with at least 12 characters. The command refuses to run without a configured database, rejects password/username collisions, and can create an administrator only when no administrator exists. It is a local operator command, not an unauthenticated API endpoint. Use it once; subsequent administrators and all Doctor, Caretaker, Resident, and Family Member accounts should be created by an authenticated Admin from **Access Management → Create user account**. The Admin supplies an initial password and delivers it through the organization’s approved secure channel.

If an administrator account already exists but its credentials are lost, do not rerun bootstrap or add a public signup endpoint. Use the deployment’s approved database administrator/recovery procedure to restore authorized admin access.

The migration chain includes the initial schema, RBAC hardening, dose schedules, reminders/escalations, and operations tables. PostgreSQL RLS is enabled on protected application tables without permissive client policies. The backend must connect using a server-side database identity configured for the intended access model. Supabase grants, Data API exposure, and production database roles are project-level settings and must be reviewed separately. No live Supabase database was configured or migrated as part of this repository work.

Start the API in one terminal:

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the reminder worker in another backend terminal:

```powershell
Set-Location backend
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

The worker persists in-app upcoming/due notifications and overdue review escalations. It does not classify a dose as missed, and it does not send SMS, email, or push notifications. Run one worker instance unless deployment-level coordination is added.

Start the frontend:

```powershell
Set-Location frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The frontend defaults to `http://localhost:8000/api`. Set `VITE_API_BASE_URL` in `frontend\.env` only to the API URL; never put privileged credentials there.

## Inventory and analytics notes

- Stock receipts use medicine + lot code + expiry date; an existing lot can be incremented only when its expiry matches. Expired lots are visible but cannot be received or issued.
- Stock issue is manually recorded. Administration outcomes do not silently deduct stock because the app cannot infer a reliable quantity from a clinical outcome.
- Adherence analytics are based on persisted dose occurrences. Keep the reminder worker running for ongoing schedule generation and notification processing. Historical analytics before occurrence records were generated may be incomplete; the application does not fabricate missing dose history.

## Tests and production build

From the repository root:

```powershell
Set-Location backend
python -m pytest tests -q

Set-Location ..\frontend
npm test
npm run build
```

The backend authorization tests use an isolated SQLite test database; the PostgreSQL migration chain can be rendered offline with `DATABASE_URL` set to a PostgreSQL URL and `alembic upgrade head --sql`. Offline SQL generation does not verify connectivity, Supabase grants, or a live migration.

## Remaining deployment checks

- Configure and verify the real PostgreSQL/Supabase connection, grants, RLS behavior, backups, TLS, and migration execution in the target environment.
- Use HTTPS, secure secret management, rate limiting, monitoring, and an operational process for database backups and migration rollback.
- Integrate a real notification provider only if required; the current implementation is in-app only.
- Run the worker under a supervised process manager and monitor its logs/errors.
- Evaluate accessibility, clinical workflow, privacy/legal, and production load requirements before handling real patient data.
