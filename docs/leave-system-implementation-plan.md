# Leave / Absence System Implementation Plan

Status: Proposed  
Date: 2026-06-29  
Scope: PeopleForce-like leave types, leave policies, accruals, assignments, requests, approvals, balances, and employee history for HR Vidnova.

## Why This Document Exists

We need to implement the leave/absence system fully, not only the visual settings page. The target behavior is close to PeopleForce:

- HR configures absence types such as `Відпустка`, `Лікарняний`, `За власний рахунок`.
- Each absence type contains one or more policies.
- A policy can accrue balance automatically, be manual/no-accrual, or be externally balanced.
- Policies are assigned to employees with an effective date.
- Employee profile shows current balances, requests, and a ledger/history such as monthly `+2.0` accruals and request deductions.

This document is both an implementation plan and a design review. It intentionally calls out where our current code is incomplete or currently maps PeopleForce fields incorrectly.

## Sources Reviewed

Local code:

- `apps/leave/models.py`
- `apps/leave/serializers.py`
- `apps/leave/views.py`
- `apps/integrations/peopleforce/importer.py`
- `frontend/src/views/settings/SettingsLeaveTypesView.tsx`

Local PeopleForce API snapshot:

- `docs/external/peopleforce/reference/reference__get-leave_policies.md`
- `docs/external/peopleforce/reference/reference__post-employees-id-employee_leave_types.md`
- `docs/external/peopleforce/reference/reference__get-employees-id-leave_balances.md`
- `docs/external/peopleforce/reference/reference__create-leave-request.md`
- `docs/external/peopleforce/reference/reference__create-leave-adjustment.md`
- `docs/external/peopleforce/guides/docs__erp-integration.md`

UI references:

- `docs/фото/image copy 49.png` through `docs/фото/image copy 56.png`

Important limitation: PeopleForce public API exposes policy type and high-level fields, but not the full internal UI schema for accrual formulas. The accrual model below is inferred from PeopleForce UI behavior, imported data, screenshots, and standard HR leave policy requirements.

## PeopleForce Mental Model

PeopleForce separates leave into these concepts:

1. Leave type
   Example: `Відпустка`, `Лікарняний`, `Віддалена робота`.

2. Leave policy
   A policy belongs to one leave type and defines rules:
   - activity type: `not_working_paid`, `not_working_unpaid`, `working_paid`;
   - counted days: `working_days` or `calendar_days`;
   - policy type: `accrual`, `manual`, or `external`;
   - approval flow;
   - restrictions;
   - balance visibility and rounding;
   - accrual/carryover rules if policy type is `accrual`.

3. Employee policy assignment
   A policy must be assigned to an employee. PeopleForce API assigns `leave_type_id + leave_type_policy_id + effective_on` to an employee.

4. Balance and ledger/history
   The profile page shows the resulting balance and history:
   - `З нарахуванням +2.0`;
   - `Запит -4.0`;
   - `Перенесення -24.0`;
   - corrections/adjustments.

The `+2.0` monthly example from the screenshot is not a default value. It is the result of an accrual policy, likely configured as `24 days/year`, accrued monthly as `2 days/month`.

## Current HR Vidnova State

Current backend models:

- `LeaveType`
- `LeaveRequest`
- `LeaveApprovalStep`
- `LeaveBalance`

Current limitations:

- There is no first-class `LeavePolicy` model.
- There is no assignment model linking employees to policies.
- There is no ledger/history table.
- There is no accrual engine or scheduled job.
- There is no daily request entry table.
- Current `LeaveBalance` stores only current imported balance plus a few policy text fields.
- Imported policy fields currently stored:
  - `policy_name`
  - `policy_activity_type`
  - `policy_counted_as`
  - raw `legacy_payload`
- Current frontend builds a policy list by grouping balances, not by real policy records.

Critical review finding:

The current frontend labels `policy_counted_as` as `З нарахуванням / Без нарахування`. In PeopleForce, `counted_as` means `working_days` vs `calendar_days`. Accrual/no-accrual corresponds to policy `type`: `accrual`, `manual`, `external`. Before implementing persistence, this must be corrected.

## Target Domain Model

### LeaveType

Purpose: visual/category shell.

Fields:

- `id`
- `name`
- `code`
- `legacy_peopleforce_id`
- `unit`: `days` or `hours`
- `icon`
- `color`
- `order`
- `is_active`
- `legacy_payload`

Keep mostly as-is.

### LeavePolicy

Purpose: actual rules for one type of absence.

Fields:

- `id`
- `leave_type_id`
- `name`
- `legacy_peopleforce_id`
- `policy_type`: `accrual`, `manual`, `external`
- `activity_type`: `not_working_paid`, `not_working_unpaid`, `working_paid`
- `counted_as`: `working_days`, `calendar_days`
- `visibility`: `everyone`, `self_only`, maybe future `custom`
- `instructions_html`
- `allow_negative_balance`
- `is_active`
- `legacy_payload`
- timestamps

Notes:

- `policy_type=accrual`: system creates balance entries automatically.
- `policy_type=manual`: balance changes only by requests/adjustments/manual admin actions.
- `policy_type=external`: HR Vidnova does not calculate balance; balance is imported/synced from another system.

### LeavePolicyAccrualRule

Purpose: accrual formula for `policy_type=accrual`.

Fields:

- `policy_id`
- `enabled`
- `annual_allowance`
- `period_amount`
- `frequency`: `monthly`, `yearly`, `semi_monthly`, `weekly`, `custom`
- `accrual_timing`: `period_start`, `period_end`
- `first_accrual`: `assignment_date`, `hire_date`, `next_period`
- `proration`: `none`, `daily`, `monthly`
- `rounding_method`: `nearest`, `up`, `down`
- `rounding_precision`: `integer`, `one_decimal`, `two_decimals`
- `max_balance`
- `carryover_enabled`
- `carryover_limit`
- `carryover_expire_month`
- `carryover_expire_day`

Example for screenshot behavior:

- `annual_allowance=24`
- `frequency=monthly`
- `period_amount=2`
- `accrual_timing=period_start`
- ledger posts `+2.0` on `01.01`, `01.02`, `01.03`, etc.

Implementation note:

Store both `annual_allowance` and `period_amount` only if needed for UI transparency. The engine should derive `period_amount = annual_allowance / 12` when frequency is monthly unless explicitly overridden.

### LeavePolicyRestriction

Purpose: constraints from the policy wizard.

Fields:

- `policy_id`
- `prevent_overlapping_requests`
- `forbid_probation_requests`
- `forbid_breakdown_edit`
- `restrict_adjustments_for_employees`
- `direct_reports_only`
- `min_daily_amount`
- `min_total_amount`
- `max_total_amount`
- `min_notice_days`
- `max_notice_days`
- `request_deadline_days`
- `allow_attachments`
- `attachment_required`
- `mandatory_comment`
- `allow_withdraw`
- `withdraw_deadline_days`

Validation should happen server-side; frontend should only mirror fields.

### LeavePolicyApprovalRule

Purpose: approval chain template.

Fields:

- `policy_id`
- `enabled`
- `skip_unassigned_approvers`
- `allow_substitute_approvers`
- `steps`: JSON or normalized child table

Recommended normalized child table: `LeavePolicyApproverStep`.

`LeavePolicyApproverStep` fields:

- `policy_id`
- `order`
- `approver_type`: `manager`, `specific_employee`, `role`, `department_head`, `hr`
- `approver_employee_id`
- `approver_role`

### EmployeeLeavePolicyAssignment

Purpose: assigns one policy to one employee from a date.

Fields:

- `id`
- `employee_id`
- `leave_type_id`
- `policy_id`
- `effective_on`
- `ends_on`
- `initial_balance`
- `legacy_peopleforce_id`
- `is_active`
- timestamps

Constraints:

- An employee should not have two active assignments for the same leave type with overlapping date ranges.
- A request can only be created if an active assignment exists for that leave type on the request dates.

### LeaveLedgerEntry

Purpose: source of truth for balance history.

Fields:

- `id`
- `employee_id`
- `leave_type_id`
- `policy_id`
- `assignment_id`
- `occurred_on`
- `entry_type`: `opening_balance`, `accrual`, `request`, `adjustment`, `carryover`, `expiration`, `import`
- `amount`
- `balance_after`
- `description`
- `source_model`
- `source_id`
- `idempotency_key`
- `legacy_peopleforce_id`
- timestamps

Rules:

- Balance is the sum of ledger entries, or the latest `balance_after` after ordered replay.
- Ledger entries are immutable except administrative reversal entries.
- Scheduled accruals must be idempotent by key, e.g. `accrual:{assignment_id}:2026-02`.
- Request approval posts negative ledger entries.
- Request cancellation/rejection posts reversal only if a deduction was already posted.

### LeaveRequest and LeaveRequestEntry

Current `LeaveRequest` should be expanded.

Recommended `LeaveRequest` fields:

- `employee_id`
- `leave_type_id`
- `policy_id`
- `assignment_id`
- `date_from`
- `date_to`
- `amount`
- `tracking_time_in`
- `status`: `draft`, `submitted`, `approved`, `rejected`, `cancelled`, `withdrawn`
- `reason`
- `submitted_at`
- `decided_at`
- `decided_by`
- `skip_approval`
- `legacy_peopleforce_id`
- `legacy_payload`

Add `LeaveRequestEntry`:

- `request_id`
- `occurs_on`
- `amount`
- `is_working_day`
- `source`: `auto`, `manual`

Reason:

PeopleForce API accepts `leave_request_entries`. We need entries to support half-days, manual breakdown, holidays/weekends, calendar days vs working days, and exact request deductions.

### LeaveAdjustment

Purpose: admin-created balance changes.

Fields:

- `employee_id`
- `leave_type_id`
- `policy_id`
- `occurred_on`
- `amount`
- `description`
- `created_by`
- `ledger_entry_id`
- `legacy_peopleforce_id`

This maps to PeopleForce `POST /leave_adjustments`.

## Balance Calculation

The ledger is the canonical source.

Algorithm:

1. Find active policy assignment for employee and leave type.
2. Build request entries for the requested period:
   - if policy `counted_as=working_days`, count employee working pattern days and exclude holidays;
   - if `calendar_days`, count every calendar date;
   - if type unit is `hours`, amount is hours from entries.
3. Validate restrictions:
   - overlap rules;
   - probation restrictions;
   - min/max daily amount;
   - min/max total amount;
   - notice windows;
   - negative balance permission.
4. On approval:
   - create `LeaveLedgerEntry(entry_type=request, amount=-request.amount)`;
   - update cached balance if we keep a denormalized balance table.
5. On cancellation/withdrawal:
   - create reversal ledger entry if the request had posted balance usage.
6. Accrual job posts `LeaveLedgerEntry(entry_type=accrual, amount=period_amount)`.

Do not directly mutate balance without a ledger entry.

## Accrual Engine

Run as a daily scheduled task, but generate entries for due periods only.

Pseudo-flow:

1. Select active assignments where policy type is `accrual`.
2. For each assignment, determine due accrual periods up to today.
3. For each period:
   - compute amount;
   - apply proration if assignment/hire started mid-period;
   - apply rounding;
   - cap by `max_balance` if configured;
   - create ledger entry with idempotency key.
4. At year boundary:
   - apply carryover rule;
   - post carryover/expiration entries.

Example monthly policy:

- Employee assigned `Відпустка` policy on `2026-01-01`.
- Rule: `24/year`, `monthly`, `period_start`.
- Entries:
  - `2026-01-01`, `accrual`, `+2.0`, balance `2.0`
  - `2026-02-01`, `accrual`, `+2.0`, balance `4.0`
  - etc.

## API Plan

Backend endpoints under `/api/leave/`:

- `leave-types/`
- `leave-policies/`
- `leave-policies/{id}/`
- `leave-policies/{id}/copy/`
- `leave-policies/{id}/assignments/`
- `leave-policy-assignments/`
- `leave-requests/`
- `leave-requests/{id}/submit/`
- `leave-requests/{id}/approve/`
- `leave-requests/{id}/reject/`
- `leave-requests/{id}/cancel/`
- `leave-adjustments/`
- `leave-ledger/`
- `leave-balances/`

Recommended response for settings page:

`GET /api/leave/types-with-policies/`

```json
[
  {
    "id": 1,
    "name": "Відпустка",
    "unit": "days",
    "icon": "plane",
    "color": "#9e9cf7",
    "policies": [
      {
        "id": 10,
        "name": "Відпустка",
        "policy_type": "accrual",
        "activity_type": "not_working_paid",
        "counted_as": "working_days",
        "employee_count": 112
      }
    ]
  }
]
```

This avoids the current frontend workaround that reconstructs policies from balances.

## UI Plan

### Settings: Leave Types

Target:

- Width follows `Графік роботи` reference.
- Types are collapsed by default.
- Expand shows policies.
- Type header actions:
  - caret expand/collapse;
  - `+` opens policy type menu;
  - `...` opens type actions.
- Policy row actions:
  - `Редагувати`;
  - `Зробити копію`;
  - `Переглянути людей`;
  - `Видалити`.

Fix required:

- The `+` menu should offer `З нарахуванням`, `Без нарахування`, possibly later `Зовнішній баланс`.
- Internally map these to `policy_type=accrual`, `manual`, `external`.
- `Враховується як` in the wizard must be `Робочі дні / Календарні дні`, not accrual/no-accrual.

### Policy Wizard

Step 1: `Деталі`

- name;
- activity type;
- counted days;
- accrual policy type;
- instructions;
- restrictions.

For `policy_type=accrual`, add accrual section:

- annual allowance;
- frequency;
- period amount preview;
- accrual timing;
- proration;
- carryover;
- max balance.

Step 2: `Схвалення`

- enabled;
- approver steps;
- skip unassigned approvers;
- substitute approvers.

Step 3: `Налаштування`

- balance rounding;
- visibility;
- withdraw settings;
- comment/attachment settings;
- notification template.

### Assignments Page

Button `Призначення` should manage employee-policy assignments.

Required flows:

- assign policy to selected employees;
- change policy from date;
- end assignment;
- initial balance;
- bulk assignment by location, department, position, employment type, working pattern.

### Employee Profile: Absences

Profile tab should show:

- balance cards;
- `Створити запит`;
- request list;
- history/ledger table with year and policy filters;
- download/export.

History table should read from `LeaveLedgerEntry`, not from aggregated balance.

## Import / Migration From PeopleForce

Current importer maps employee leave balances into `LeaveBalance`.

Required importer upgrades:

1. Import/list `LeaveType`.
2. Import/list `LeavePolicy`.
3. Store policy `type`, `activity_type`, `counted_as`, `visibility`.
4. Import employee policy assignments from employee leave types/balances.
5. Store raw PeopleForce payload for unsupported fields.
6. Treat imported current balances as `opening_balance` or `import` ledger entries.
7. Import leave requests and create request ledger entries only if reliable.
8. Do not infer accrual formulas from balance history unless explicitly approved; imported history may be incomplete.

Open risk:

PeopleForce public API does not expose full accrual formula in the reviewed docs. For migration, we may need either:

- manual reconfiguration in HR Vidnova;
- additional PeopleForce export;
- DB/report export from PeopleForce UI;
- or reconstructing formulas from history with human review.

## Implementation Phases

### Phase 1: Correct model foundation

- Add `LeavePolicy`.
- Add `LeavePolicyAccrualRule`.
- Add `LeavePolicyRestriction`.
- Add `LeavePolicyApprovalRule` and approver steps.
- Add `EmployeeLeavePolicyAssignment`.
- Add `LeaveLedgerEntry`.
- Add `LeaveRequestEntry`.
- Add `LeaveAdjustment`.
- Keep existing `LeaveBalance` temporarily as imported snapshot/cache.

Verification:

- `python3 manage.py makemigrations --check --dry-run`
- migration tests for overlapping assignments and ledger idempotency.

### Phase 2: API and serializers

- Create CRUD APIs for policies and assignments.
- Create ledger API.
- Update leave request API to validate assignment/policy.
- Add policy copy endpoint.
- Add people count per policy.

Verification:

- DRF tests for policy create/update/copy/delete.
- assignment overlap tests.
- request validation tests.

### Phase 3: Accrual engine

- Implement pure service functions first.
- Add management command: `accrue_leave_balances --date YYYY-MM-DD --dry-run`.
- Add Celery beat/daily schedule after tests pass.
- Idempotency keys required.

Verification:

- monthly `24/year -> +2/month`;
- proration edge cases;
- rounding edge cases;
- carryover year boundary;
- rerun command does not duplicate entries.

### Phase 4: Frontend settings UI

- Replace local-only policy wizard with real API.
- Correct terminology.
- Add accrual fields.
- Add assignments modal/page.
- Add policy people list.

Verification:

- `npm run build`
- browser screenshots for desktop/mobile.

### Phase 5: Employee profile absences

- Balance cards from ledger/current balance endpoint.
- Request table from `LeaveRequest`.
- History from `LeaveLedgerEntry`.
- Create request flow validates and previews amount.

Verification:

- approved request deducts balance;
- cancelled request restores balance by reversal entry;
- yearly/monthly filters match screenshot behavior.

### Phase 6: Import compatibility

- Migrate current `LeaveBalance` rows into policies/assignments where possible.
- Store ambiguous rows for manual review.
- Add admin report for unmapped/imported policies.

Verification:

- sample imported employees preserve visible balances;
- no duplicate policies from repeated imports;
- raw payload retained.

## Review Findings / Risks

Critical:

- Current UI conflates PeopleForce `counted_as` with accrual/no-accrual. This must be fixed before persisting policies.
- Current `LeaveBalance` cannot support history, accrual idempotency, request reversals, or auditability.
- Without a ledger, any recalculation or correction will be fragile.

High:

- Accrual formulas may not be available from PeopleForce public API. We need a manual setup/import fallback.
- Timezone/date boundary matters. Accrual dates must use clinic/company timezone, not UTC midnight.
- Request amount calculation depends on working patterns and holidays; those must be linked reliably.
- Approval steps must be snapshot onto requests when submitted. Later policy changes must not rewrite old request approval chains.

Medium:

- External-balance policies should not be recalculated by HR Vidnova.
- Balance caps and carryover can create surprising ledger entries; UI must show why balance changed.
- Bulk assignment needs dry-run preview to avoid assigning wrong policies to many employees.

Low:

- Frontend can ship visual pages before all fields are active, but disabled/stub behavior must be explicit in code and hidden from production workflows.

## Test Plan

Backend:

- model constraints:
  - no overlapping active assignments;
  - unique ledger idempotency key;
  - valid policy type transitions.
- accrual:
  - monthly, yearly, period start/end;
  - proration;
  - rounding;
  - max balance;
  - carryover/expiration.
- requests:
  - working days vs calendar days;
  - holidays excluded for working day policies;
  - overlap blocking;
  - approval posting deduction;
  - cancellation reversal.
- import:
  - repeated import is idempotent;
  - unknown PeopleForce fields preserved.

Frontend:

- settings leave types collapsed by default;
- policy menu and wizard;
- accrual form validation;
- assignment page filters and bulk selection;
- profile history table.

Operational:

- dry-run accrual command output;
- rerun daily job;
- export ledger for one employee;
- reconcile cached balance against ledger sum.

## Acceptance Criteria

The implementation is complete when:

- HR can create an absence type and at least two policies under it.
- HR can configure monthly vacation accrual, e.g. `24/year -> +2/month`.
- HR can assign a policy to employees from an effective date.
- Employee profile shows current balance and ledger history.
- Approved leave requests deduct balance.
- Accrual job posts monthly ledger entries exactly once.
- Admin can add manual adjustments.
- Policy changes do not corrupt historical requests or ledger entries.
- Imported PeopleForce balances are preserved or explicitly marked for manual review.

## Recommended Next Work Item

Start with backend schema and services, not more frontend-only UI.

First concrete PR should:

1. Add `LeavePolicy`, `LeavePolicyAccrualRule`, `EmployeeLeavePolicyAssignment`, and `LeaveLedgerEntry`.
2. Add tests for `+2/month` accrual and ledger idempotency.
3. Expose read-only `types-with-policies` endpoint.
4. Fix frontend labels so `counted_as` means working/calendar days and `policy_type` means accrual/manual/external.
