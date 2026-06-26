# PeopleForce data model and import plan

Дата: 2026-06-24  
Статус: implementation plan for legacy migration

## Цель

Перенести из PeopleForce все данные, которые нужны HR Vidnova как стартовая
HR-база:

- сотрудники и их legacy identifiers;
- должности, департаменты, divisions, locations, employment types, job levels;
- подчинение и история назначений;
- teams и team memberships;
- custom employee fields, field histories, employee tables;
- база знаний: categories и articles;
- отпуска: leave types, leave requests, approvals, balances;
- employee documents/folders и вложения, где API дает ссылки;
- raw snapshot всех использованных PeopleForce endpoint-ов.

PeopleForce после миграции не должен быть runtime-зависимостью. Импорт работает
как read-only pull в HR Vidnova.

## Источники документации

Локальный snapshot официальной документации:

- `docs/external/peopleforce/llms.txt`;
- `docs/external/peopleforce/reference/`;
- `docs/external/peopleforce/guides/`;
- `docs/external/peopleforce/changelog/`.

API v3:

- base URL: `https://app.peopleforce.io/api/public/v3`;
- auth header: `X-API-KEY`;
- pagination: `page`, response `metadata.pages`;
- public limit: 300 requests/minute.

## Design principles

### Raw-first

Каждая полученная сущность сохраняется в `PeopleForceEntity`:

- `entity_type`;
- `external_id`;
- `endpoint`;
- `payload`;
- `payload_hash`;
- `fetched_at`;
- mapping status and HR object pointer.

Это позволяет:

- не потерять поля, которым еще нет HR-модели;
- повторно перемаппить данные без повторного API pull;
- делать reconciliation отчеты;
- безопасно расширять модель позже.

### Normalized working models

Поля, которые нужны UI и бизнес-логике, маппятся в рабочие Django-модели:

- `Employee`;
- `Clinic`, `Department`, `Division`;
- `Position`, `EmploymentType`, `JobLevel`;
- `ManagerAssignment`;
- `Team`, `TeamMembership`;
- `EmployeePositionHistory`;
- `EmployeeEmploymentStatus`;
- `KnowledgeCategory`, `KnowledgeDocument`;
- `LeaveType`, `LeaveRequest`, `LeaveApprovalStep`, `LeaveBalance`.

### No secrets in repo

PeopleForce API key хранится только в локальном `.env` или runtime env:

```env
PEOPLEFORCE_API_KEY=<secret>
PEOPLEFORCE_API_BASE_URL=https://app.peopleforce.io/api/public/v3
```

Запрещено писать API key в docs, память, migration files, git history и логи.

## PeopleForce endpoints in scope

### Employees

- `GET /employees?status=all`;
- `GET /employees/{employee_id}`;
- `GET /employees/terminated`;
- `GET /employee_fields`;
- `GET /employees/{employee_id}/field_histories`;
- `GET /employee_tables`;
- `GET /employee_tables/{internal_name}/columns`;
- `GET /employees/{employee_id}/tables/{internal_name}`;
- optional later: notes, emergency contacts, dependents, skills, certifications.

Mapping:

- PeopleForce `id` -> `Employee.legacy_peopleforce_id` and
  `ExternalEmployeeLink(source=peopleforce_legacy)`;
- `employee_number` -> `Employee.employee_number`;
- names/emails/phones/dates/gender/avatar/status -> `Employee`;
- custom `fields` -> `Employee.peopleforce_fields`;
- terminated status/dates -> `Employee.status`, `dismissed_on`, raw payload.

### Org structure

- `GET /locations`;
- `GET /departments`;
- `GET /divisions`;
- `GET /positions`;
- `GET /job_levels`;
- `GET /employment_types`;
- `GET /working_patterns`;
- `GET /teams`;

Mapping:

- PeopleForce location -> `Clinic` by default. This is a pragmatic MVP mapping
  because local `Department` currently requires clinic.
- PeopleForce department -> `Department`, preserving `parent_id` and manager
  links after employees are imported.
- PeopleForce division -> `Division`.
- PeopleForce position -> `Position`.
- PeopleForce job level -> `JobLevel`.
- PeopleForce employment type -> `EmploymentType`.
- PeopleForce team -> `Team` and `TeamMembership`.

Gap: PeopleForce department has no clinic/location FK in the listed API schema.
If a department belongs to several locations, HR Vidnova will need either
`Department.clinic = null` schema change or explicit mapping table. MVP creates
a default/import clinic when location is absent.

### Position and employment history

- `GET /employees/{employee_id}/positions`;
- `GET /employees/{employee_id}/employment_statuses`;
- `GET /employees/{employee_id}/job_profiles`;
- `GET /job_groups`;
- `GET /job_profiles`.

Mapping:

- positions history -> `EmployeePositionHistory`;
- employment status history -> `EmployeeEmploymentStatus`;
- current `reporting_to` and position-history `reporting_to` ->
  `ManagerAssignment`;
- job profiles/groups remain raw-first until HR UI needs them.

### Knowledge base

- `GET /knowledge_base/categories`;
- `GET /knowledge_base/categories/{category_id}/articles`;
- `GET /knowledge_base/articles/{article_id}`.

Mapping:

- category -> `KnowledgeCategory`;
- article -> `KnowledgeDocument`;
- `body` and `body_html` are both preserved.

Gap: docs do not show a separate knowledge attachment endpoint. If article body
contains file links, they stay in body/html and raw payload until discovered.

### Leave

- `GET /leave_types`;
- `GET /leave_policies`;
- `GET /employees/{employee_id}/leave_balances`;
- `GET /leave_requests`;
- `GET /leave_requests/{id}`;
- `GET /pending_leave_requests`;
- `GET /holidays`;
- `GET /holiday_policies`;
- `GET /employees/{employee_id}/holidays`.

Mapping:

- leave type -> `LeaveType`;
- leave request -> `LeaveRequest`;
- approvals -> `LeaveApprovalStep` where approver can be mapped to local
  `User`; otherwise approvals remain in `legacy_payload`;
- balances -> `LeaveBalance`.

Attachment warning: leave request attachment URLs are temporary. A production
file import must download files immediately during the same run.

### Employee documents

- `GET /document_folders`;
- `GET /employees/{employee_id}/documents`;
- `GET /employees/{employee_id}/documents/{id}`.

First pass:

- raw snapshot in `PeopleForceEntity`;
- normalized file model can be added once we confirm URL lifetime and file
  payload shape in the real tenant.

## Import order

1. Pull raw dictionaries:
   locations, divisions, departments, positions, job levels, employment types,
   working patterns, teams, job groups, job profiles, employee fields,
   employee tables, leave types, leave policies, document folders, knowledge
   categories.
2. Map dictionaries into HR reference tables.
3. Pull employees with `status=all`.
4. Pull employee details.
5. Map employees and external links.
6. Resolve department parents and department managers.
7. Resolve employee managers and teams.
8. Pull and map employee histories:
   positions, employment statuses, job profiles, field histories, custom tables.
9. Pull and map leave:
   leave requests, leave balances, approvals, raw entries.
10. Pull and map knowledge articles.
11. Pull employee documents raw; download attachments only when file URLs are
    available and still valid.
12. Produce reconciliation counters:
    unmapped employees, missing managers, missing departments, raw-only
    entities, failed downloads.

## Commands

Local database for first import rehearsal:

```bash
docker compose up -d db redis
DB_HOST=127.0.0.1 DB_PORT=5444 python manage.py migrate
```

Small dry run, no files and no timesheet history:

```bash
DB_HOST=127.0.0.1 DB_PORT=5444 python manage.py sync_peopleforce_legacy \
  --dry-run \
  --limit-employees 10 \
  --skip-documents \
  --skip-timesheet
```

Full dry run, including documents metadata and timesheet counters, without
downloading document files:

```bash
DB_HOST=127.0.0.1 DB_PORT=5444 python manage.py sync_peopleforce_legacy \
  --dry-run \
  --timesheet-start 2022-01-01 \
  --timesheet-end 2026-06-24
```

First real import, metadata only for employee documents:

```bash
DB_HOST=127.0.0.1 DB_PORT=5444 python manage.py sync_peopleforce_legacy \
  --timesheet-start 2022-01-01 \
  --timesheet-end 2026-06-24
```

Real import with employee document file downloads:

```bash
DB_HOST=127.0.0.1 DB_PORT=5444 python manage.py sync_peopleforce_legacy \
  --timesheet-start 2022-01-01 \
  --timesheet-end 2026-06-24 \
  --download-document-files
```

`PEOPLEFORCE_API_KEY` must be present in runtime env before any command that
calls the real PeopleForce API. Do not commit it or write it into documentation.

## Rollback

The importer is idempotent and does not delete local HR data. It only upserts
objects linked by PeopleForce IDs. If a mapping is wrong:

1. keep `PeopleForceEntity` raw rows;
2. adjust mapping code;
3. rerun importer;
4. manually archive or fix wrong normalized rows if needed.

Do not hard-delete imported HR rows until reconciliation is reviewed.

## Open decisions

1. Confirm whether PeopleForce locations map 1:1 to Vidnova clinics.
2. Decide whether employee documents must be stored in a first-class HR model.
3. Decide whether salary/compensation endpoints are in scope; they are sensitive
   and not needed for MVP UI.
4. Confirm how much custom employee table data should be visible in the UI.
5. Decide whether to create local Django users for PeopleForce employees during
   import or only link later after auth design.

## PeopleForce-compatible API for sunc_v4

Дата анализа `sunc_v4`: 2026-06-24. Production instance работает на
`172.16.33.14`, контейнер `sunc_v4_app`; рабочий код найден в
`/root/sunc_v4_extracted/app` и `/app` внутри контейнера.

Во время разработки `sunc_v4` должен слать присутствие в HR Vidnova
параллельно с PeopleForce. Чтобы не переписывать интеграцию полностью, HR
Vidnova предоставляет compatibility API, повторяющий минимальный набор
PeopleForce endpoint-ов, которые реально использует `sunc_v4`.

### Implemented namespaces

```text
/api/public/v3/...
/api/peopleforce-compatible/v3/...
```

`/api/public/v3` нужен для почти прямой замены `PEOPLEFORCE_BASE_URL` после
полного импорта сотрудников. `/api/peopleforce-compatible/v3` оставлен как
явный тестовый namespace.

Auth:

- header `X-API-KEY`;
- настройка HR Vidnova: `PEOPLEFORCE_COMPAT_API_KEY`;
- этот ключ не должен совпадать с настоящим PeopleForce API key;
- если ключ не настроен, compatibility API отвечает `503`.

### sunc_v4 endpoints in scope

Сотрудники:

- `GET /employees?page=&per_page=`;
- `GET /employees/{id}`.

`sunc_v4/sync_users.py` читает поля:

- `id`, `status`, `full_name`, `email`, `personal_email`;
- `fields.employee_number.value`;
- `fields.mobile_number.value`;
- `fields.work_phone_number.value`;
- `division.name`, `department.name`, `position.name`;
- `date_of_birth`, `avatar_url`.

Timesheet:

- `POST /time/timesheet_entries`;
- `POST /time/timesheet_entries/bulk`;
- `GET /time/timesheet_entries`;
- `DELETE /time/timesheet_entries/{id}`;
- `DELETE /time/timesheet_entries/bulk`.

`sunc_v4` отправляет `starts_at` и `ends_at` как Unix timestamp. HR Vidnova
также принимает ISO datetime строки для ручных проверок.

### Local model mapping

- incoming request -> `PeopleForceCompatRequest`;
- incoming timesheet row -> `PeopleForceCompatTimesheetEntry`;
- `employee_id` from `sunc_v4` -> `Employee.legacy_peopleforce_id` or
  `ExternalEmployeeLink(source=peopleforce_legacy)`;
- optional PeopleForce row id from mirror mode ->
  `PeopleForceCompatTimesheetEntry.legacy_peopleforce_entry_id`;
- if employee is mapped, row is normalized into `AttendancePeriod`;
- if employee is not mapped yet, raw row is still accepted and stored with
  `legacy_peopleforce_employee_id`, but request status is `partial`.

Timesheet entries are idempotent by active
`legacy_peopleforce_employee_id + starts_at + ends_at`. Exact retries update the
existing row. Overlapping active rows return a PeopleForce-like validation
error.

### Response compatibility

Single create:

```json
{"data": {"id": 123, "employee_id": 488, "starts_at": 1718000000, "ends_at": 1718030000, "minutes": 500, "status": "unsubmitted"}}
```

Bulk create returns HTTP 200 even with validation errors, matching PeopleForce
behavior observed in `sunc_v4` comments:

```json
{"records": {"count": 1, "data": []}, "errors": {"count": 1, "data": []}}
```

When there are no bulk errors, the `errors` key is omitted because one
`sunc_v4` script treats any truthy `errors` object as failure.

Bulk delete:

```json
{"count": 12}
```

### Rollout recommendation

Stage 1, safe mirror:

- keep `sunc_v4` `PEOPLEFORCE_BASE_URL` pointed to real PeopleForce;
- add a second HR Vidnova base URL/key in `sunc_v4`;
- mirror only `/time/timesheet_entries*` calls after successful PeopleForce
  writes;
- for single `POST`, pass the created PeopleForce row id as
  `peopleforce_entry_id` or `legacy_peopleforce_entry_id` in the mirrored HR
  payload, so later `DELETE /time/timesheet_entries/{id}` can resolve the
  mirrored row by PeopleForce ID;
- log mirror failures without breaking the existing PeopleForce flow.

Stage 2, full switch:

- finish PeopleForce employee import into HR Vidnova;
- verify `GET /api/public/v3/employees` returns the same PeopleForce IDs that
  `Users_PUZ.id_pf` already contains;
- point `sunc_v4` `PEOPLEFORCE_BASE_URL` to
  `https://<hr-host>/api/public/v3`;
- disable the old PeopleForce key in `sunc_v4`.
