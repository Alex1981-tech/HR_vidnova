# Відсутності / Leave - робочий контекст

Останнє оновлення: 2026-07-01.

Це головна точка входу для функціоналу відсутностей: типи відсутностей,
політики, призначення політик людям, нарахування балансу, заявки,
ledger-історія і сторінка профілю співробітника.

## Швидкий старт для наступної сесії

1. Прочитати цей файл.
2. Прочитати журнал останньої сесії:
   `docs/leave/sessions/2026-07-01-absence-and-policy-ui.md`.
3. Якщо потрібно зрозуміти дизайн-рішення з початку реалізації, прочитати
   `docs/leave/implementation-plan.md`.
4. Перед правками перевірити live state:
   - `git status --short`;
   - `python3 manage.py check`;
   - для leave-логіки: `DB_ENGINE=sqlite python3 manage.py test apps.leave -v 1`;
   - для frontend: `cd frontend && npm run build`.

На початок релізу `1.0.39` production був оновлений до commit `9139507`
`Fix leave ledger accrual sync`. Локальний frontend WIP по leave UI,
налаштуваннях політик і оргструктурі закритий у changelog `1.0.39` перед
наступним push/deploy.

## Документи в цьому розділі

- `implementation-plan.md` - початковий архітектурний план і acceptance
  criteria. Частина вже реалізована, частина лишається планом.
- `sessions/2026-06-30-leave-policies.md` - перша велика сесія по реальних
  політиках, ledger і lifecycle заявок.
- `sessions/2026-07-01-absence-and-policy-ui.md` - поточний журнал:
  UI, правила, prod deploy, hotfix ledger.

## Основні файли коду

Backend:

- `apps/leave/models.py` - доменні моделі.
- `apps/leave/services.py` - розрахунок балансу, ledger, заявки.
- `apps/leave/serializers.py` - API-контракти.
- `apps/leave/views.py` - DRF endpoint-и.
- `apps/leave/tests.py` - regression tests.
- `apps/leave/migrations/0006_*` - базові політики/ledger/assignments.
- `apps/leave/migrations/0007_*` - backfill з legacy balances.
- `apps/leave/migrations/0008_*` - baseline-дати legacy opening.
- `apps/leave/migrations/0009_*` - detail rules політики.
- `apps/leave/migrations/0010_*` - seniority bonus levels.

Frontend:

- `frontend/src/App.tsx` - профіль співробітника, вкладка `Відсутності`.
- `frontend/src/views/settings/SettingsLeaveTypesView.tsx` - налаштування
  типів відсутностей і політик.
- `frontend/src/api/client.ts` - leave API methods.
- `frontend/src/types/api.ts` - leave API types.
- `frontend/src/styles/index.css` - layout/styling.
- `frontend/src/lib/leaveIcons.tsx` - іконки типів відсутностей.

## Поточна модель даних

### LeaveType

Візуальна і категорійна оболонка: `Відпустка`, `Лікарняний`,
`За власний рахунок`.

Ключові поля:

- `unit`: `days` або `hours`;
- `icon`, `color`, `order`;
- `is_active`;
- `legacy_peopleforce_id`, `legacy_payload`.

### LeavePolicy

Правила для конкретного типу відсутності.

Ключові поля:

- `policy_type`: `accrual`, `manual`, `external`;
- `activity_type`: `not_working_paid`, `not_working_unpaid`, `working_paid`;
- `counted_as`: `working_days`, `calendar_days`;
- `visibility`;
- detail rules: holidays, on-demand absence, overlap, probation,
  manual breakdown, direct reports, notice limits, min/max amounts,
  negative balance;
- approval settings: `approval_enabled`, `approver_steps`,
  `skip_unassigned_approvers`, `allow_substitute_approvers`;
- display/settings fields: rounding, withdraw, comments, attachments,
  notifications.

Важливо: `counted_as` не означає "з нарахуванням". Це тільки спосіб рахувати
дні. Нарахування визначається через `policy_type`.

### LeavePolicyAccrualRule

Формула для `policy_type=accrual`.

Ключові поля:

- `enabled`;
- `start_delay_amount`, `start_delay_unit`;
- `start_balance`;
- `annual_allowance`;
- `period_amount`;
- `frequency`: `monthly`, `yearly`, `weekly`, `none`;
- `accrual_timing`: `period_start`, `period_end`;
- `first_accrual`: `proportional`, `full`, `none`;
- `max_balance`;
- carryover fields;
- `seniority_bonus_enabled`, `seniority_bonus_levels`.

На 2026-07-01 carryover поля зберігаються, але повна логіка перенесення і
списання ще не реалізована.

### EmployeeLeavePolicyAssignment

Призначення політики співробітнику з дати.

Ключові поля:

- `employee`;
- `leave_type`;
- `policy`;
- `effective_on`;
- `ends_on`;
- `initial_balance`;
- `is_active`.

При призначенні нової політики для того самого співробітника і leave type
поточне активне призначення закривається через `ends_on` і `is_active=False`.

### LeaveLedgerEntry

Канонічне джерело історії і балансу.

Типи:

- `opening_balance`;
- `accrual`;
- `request`;
- `adjustment`;
- `carryover`;
- `expiration`;
- `import`.

Ledger entries мають `idempotency_key`. Баланс не треба змінювати напряму
без ledger-запису.

### LeaveBalance

Поточний кеш/срез для швидкого UI.

Не є джерелом істини. Значення оновлюється через `update_balance_cache()` після
sync, призначення політики або lifecycle заявки.

### LeaveRequest

Заявка на відсутність. На 2026-07-01 модель зберігає один `amount`, а не
поденну розбивку. Approval lifecycle вже пише ledger-записи, але повний
workflow багатокрокового погодження ще відкритий.

## Як працює нарахування

Головний сервіс: `sync_assignment_balance(assignment, through_date=None)`.

Поточний алгоритм:

1. Бере assignment під `select_for_update`.
2. Визначає `through_date` як `timezone.localdate()`, якщо не передано.
3. Рахує opening:
   - `assignment.initial_balance`;
   - плюс `rule.start_balance`, якщо політика `accrual` і rule enabled.
4. Якщо opening ще не створений, створює `opening_balance`.
5. Для `policy_type=accrual` і enabled rule:
   - бере `period_amount`;
   - якщо `period_amount=0`, виводить з `annual_allowance`:
     monthly = /12, weekly = /52, yearly = whole annual;
   - застосовує start delay;
   - генерує due dates за `frequency` і `accrual_timing`;
   - пропускає due dates `<= opening_date` для legacy baseline;
   - не виходить за `assignment.ends_on`;
   - застосовує `max_balance`, якщо заданий;
   - створює `accrual` ledger entry з ключем
     `leave-assignment:{assignment.id}:accrual:{YYYY-MM-DD}`.
6. Якщо увімкнено `seniority_bonus_levels`, окремо створює додаткові accrual
   entries з ключем `...:seniority:{level_id}:{YYYY-MM-DD}`.
7. Оновлює `LeaveBalance` кеш для assignment.

Важлива prod-правка 2026-07-01:

- `GET /api/leave/balances/?employee=...` синхронізує active assignments перед
  відповіддю.
- `GET /api/leave/ledger/?employee=...` тепер теж синхронізує active
  assignments перед відповіддю. Це прибрало race, коли картка показувала
  новий баланс, а історія ще не показувала новий accrual.

## Як працює заявка

Основні функції:

- `active_assignment_for_request()`;
- `leave_request_amount()`;
- `validate_leave_request_policy()`;
- `transition_leave_request_status()`.

Розрахунок кількості:

- якщо `amount` переданий і політика не забороняє ручну розбивку, він
  використовується;
- інакше рахується автоматично:
  - `working_days` = понеділок-п'ятниця;
  - `calendar_days` = всі календарні дати;
  - неробочі свята з clinic holiday policy виключаються, якщо політика не
    вимагає списувати їх з балансу.

Валідації:

- перетин з іншими заявками;
- випробувальний термін;
- direct reports only;
- mandatory comment;
- заборона ручної розбивки;
- min/max total amount;
- min daily amount;
- on-demand limit;
- min/max notice days;
- negative balance rules.

Lifecycle:

- `approve`:
  - перевіряє policy rules;
  - рахує amount;
  - створює `LeaveLedgerEntry(kind=request)` з idempotency key
    `leave-request:{id}:approved`;
  - оновлює `LeaveBalance`.
- `cancel` або `reject` після `approved`:
  - створює reversal `LeaveLedgerEntry(kind=adjustment)`;
  - оновлює `LeaveBalance`.
- повторний `approve` не дублює списання.

Поточна реалізація `request_balance_delta()`:

- `not_working_paid` списує баланс (`-amount`);
- `working_paid` не змінює баланс (`0`);
- `not_working_unpaid` зараз повертає `+amount`.

Семантику `not_working_unpaid` треба бізнесово підтвердити: для карток типу
`За власний рахунок` UI часто показує "Використано", а не "Доступно".

## API, які використовуються

Основні endpoint-и:

- `GET/POST /api/leave/types/`
- `GET /api/leave/types/with-policies/`
- `GET/POST/PATCH/DELETE /api/leave/policies/`
- `POST /api/leave/policies/{id}/copy/`
- `POST /api/leave/policies/{id}/recalculate/`
- `GET/POST/PATCH/DELETE /api/leave/policy-assignments/`
- `POST /api/leave/policy-assignments/bulk-assign/`
- `POST /api/leave/policy-assignments/bulk-remove/`
- `POST /api/leave/policy-assignments/{id}/recalculate/`
- `GET /api/leave/ledger/`
- `GET /api/leave/balances/`
- `GET/POST/PATCH/DELETE /api/leave/requests/`
- `POST /api/leave/requests/{id}/approve/`
- `POST /api/leave/requests/{id}/reject/`
- `POST /api/leave/requests/{id}/cancel/`

RBAC на 2026-07-01 частково підключений для видалення заявок:
`leave.delete_requests`. Інші leave endpoint-и ще не повністю переведені на
fine-grained RBAC.

## Як зараз призначається політика людині

Системна модель: active `EmployeeLeavePolicyAssignment`.

Джерела призначень:

- backfill з legacy PeopleForce balances;
- UI bulk assignment на сторінці налаштувань типів відсутностей;
- прямий API `bulk-assign`.

Правило:

- для одного employee + leave type має бути одне актуальне активне призначення;
- нове призначення через сервіс закриває попереднє;
- кількість співробітників у policy row рахується через active assignments;
- бокова панель `Призначення`/`Переглянути людей` показує людей, у яких ця
  політика активна.

Ще не реалізовано:

- автоматичне призначення за правилами аудиторії department/location/position;
- dry-run bulk assignment;
- audit UI для масового перепризначення.

## Production state на 2026-07-01

Останні leave-related deploy-и:

- `3e6f3fe` - `Leave: PF-like absences and policy rules`;
- `9139507` - `Fix leave ledger accrual sync`.

Prod host:

- `172.16.33.14`;
- compose dir: `/root/hr_vidnova`;
- compose file: `docker-compose.prod.ghcr.yml`.

Після hotfix перевірено:

- GitHub Actions run `28512728687` succeeded;
- prod `manage.py check` passed;
- `https://hr.vidnova.app/changelog` returned 200;
- `/api/auth/status/` returned 200;
- employee `58`, vacation ledger top row:
  `2026-07-01 accrual +2.00 balance 9.00`.

## Відкриті питання

1. Carryover: поля є, але повний year-boundary carryover/expiration engine ще
   не реалізований.
2. Scheduled accrual: зараз sync відбувається через API/service calls. Потрібен
   явний management command/Celery schedule для регулярного нарахування.
3. Approval engine: UI зберігає `approver_steps`, є тестовий preview, але
   submission-time snapshot approval chain і реальна перевірка approver-а при
   approve ще не завершені.
4. `not_working_unpaid` delta semantics треба підтвердити бізнесово.
5. Daily request entries: поки немає окремої `LeaveRequestEntry` моделі з
   поденною розбивкою.
6. Working patterns: `working_days` зараз базово Mon-Fri; повна інтеграція з
   індивідуальними графіками роботи ще відкрита.
7. External balance policies: потрібно зафіксувати, хто є джерелом істини і чи
   дозволені локальні заявки/коригування.
8. Fine-grained RBAC для всіх leave endpoint-ів ще не завершений.
9. PeopleForce import: public API не дає повну формулу нарахувань; accrual
   policy formulas потрібно конфігурувати вручну або отримати окремим export.
10. UI WIP з 2026-07-01 треба окремо дорев'ювити, зібрати і закоммітити.
