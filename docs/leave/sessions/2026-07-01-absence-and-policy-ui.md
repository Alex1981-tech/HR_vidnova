# Сесія 2026-07-01 - відсутності, політики, UI і ledger hotfix

## Контекст

Працювали над PeopleForce-like функціоналом відсутностей:

- `http://localhost:5178/settings/leave-types`
- `http://localhost:5178/people/employees/58/absence`
- production: `https://hr.vidnova.app/people/employees/58/absence`

Референси були в `docs/фото/`:

- employee absence page;
- request modal;
- policy card menus;
- forecast balance drawer;
- policy edit modal;
- approvals UI;
- accrual/carryover UI;
- assignment drawer.

Основна ціль: привести сторінки відсутностей до поведінки PeopleForce, але не
лишати це тільки UI. Налаштування політик мають реально впливати на
розрахунок балансу, заявки і історію.

## Що зроблено протягом дня

### 1. Сторінка співробітника `Відсутності`

Файли:

- `frontend/src/App.tsx`
- `frontend/src/styles/index.css`

Реалізовано/дороблено:

- картки балансів по активних policy assignments;
- компактніші картки з кнопками:
  - `Створити запит`;
  - forecast/calendar button;
  - menu `...`;
- request modal `Запит на відсутність`;
- вибір типу відсутності в modal, default = тип картки, з якої відкрили;
- таблиця `Запити` в компактному стилі PeopleForce;
- меню рядка заявки `... -> Видалити`;
- confirm modal для видалення заявки;
- permission hook для видалення заявок через `leave.delete_requests`;
- таблиця `Історія` з колонками:
  - дата;
  - опис;
  - використано;
  - нараховано;
  - баланс;
- фільтр історії за роком і типом відсутності;
- forecast balance drawer.

Важливо: частина frontend-файлів після backend hotfix залишалась локально
незакомміченою. Перед наступним commit треба ще раз перевірити diff.

### 2. UI налаштування типів і політик відсутностей

Файли:

- `frontend/src/views/settings/SettingsLeaveTypesView.tsx`
- `frontend/src/styles/index.css`

Реалізовано/дороблено:

- compact PeopleForce-like layout для policy wizard;
- detail step:
  - `policy_type`: `З нарахуванням`, `Без нарахування`, `Зовнішній баланс`;
  - `counted_as`: `Робочі дні`, `Календарні дні`;
  - activity type;
  - instructions;
  - restrictions;
  - negative balance options;
  - min/max request limits;
- accrual/carryover step:
  - start delay;
  - start balance;
  - period accrual amount/frequency/timing;
  - max balance;
  - carryover date fields;
  - first accrual;
  - seniority bonus levels;
  - add/remove level;
- якщо `policy_type=manual` або `external`, accrual step не має показуватись як
  робочий блок налаштувань;
- approvals step:
  - approver rows;
  - `Додати схвалювача`;
  - вибір типу approver-а;
  - specific employee picker;
  - substitute approver settings;
  - preview/test block: вибрати співробітника і побачити, хто буде
    погоджувати його відпустку для цього типу відсутності;
- policy people drawer:
  - без pagination;
  - search по людях;
  - scroll list;
  - відкривається як з menu `Переглянути людей`, так і з клікабельної кількості
    співробітників у policy row;
- UI density:
  - зменшені відступи;
  - уніфіковані шрифти;
  - компактніші controls;
  - акцентні кольори мають братися із системних змінних, не hardcoded purple.

### 3. Backend detail rules і request validation

Файли:

- `apps/leave/models.py`
- `apps/leave/services.py`
- `apps/leave/serializers.py`
- `apps/leave/views.py`
- `apps/leave/tests.py`
- migrations `leave.0009`, `leave.0010`

Реалізовано раніше в цій leave-серії і перевірено сьогодні:

- detail fields у `LeavePolicy`:
  - `deduct_non_working_holidays`;
  - `allow_on_demand_absence`;
  - `on_demand_limit`;
  - overlap/probation/breakdown/direct-reports restrictions;
  - min/max amount;
  - min/max notice;
  - negative balance limit;
- seniority bonus levels у `LeavePolicyAccrualRule`;
- request validation використовує policy settings;
- request approval/cancel пише ledger entries.

### 4. Production deploy основного leave release

Commit:

- `3e6f3fe` - `Leave: PF-like absences and policy rules`

Що було в release:

- leave policy detail rules;
- accrual and seniority bonus settings;
- PeopleForce-like employee absence page;
- policy settings UI updates;
- request lifecycle/ledger integration;
- migrations `leave.0009` і `leave.0010`.

Prod:

- host `172.16.33.14`;
- compose dir `/root/hr_vidnova`;
- compose file `docker-compose.prod.ghcr.yml`;
- services recreated: `web`, `celery`, `celery-beat`, `frontend`.

Перевірки:

- GitHub Actions run `28506373940` success;
- prod `manage.py check` passed;
- migrations `leave.0009` і `leave.0010` applied;
- `/changelog` 200;
- `/api/auth/status/` 200.

### 5. Bug: баланс нарахований, а історія не показує accrual

Симптом:

- на prod у employee 58 картка `Відпустка` показувала `9.0`;
- таблиця історії спершу не показувала `01.07.2026 +2.0`;
- на dev та після refresh рядок був видимий.

Root cause:

- frontend у `EmployeeAbsenceTabView.loadAbsence()` завантажує паралельно:
  - `leaveBalances`;
  - `leaveLedger`;
  - `leaveRequests`;
  - `leaveTypes`;
  - assignments.
- `GET /api/leave/balances/?employee=...` синхронізував active assignments і
  створював due accrual перед відповіддю.
- `GET /api/leave/ledger/?employee=...` до hotfix просто читав ledger.
- Якщо ledger response приходив раніше, історія була stale, а картка вже
  показувала новий баланс.

Fix:

- `LeaveLedgerEntryViewSet.list()` тепер викликає `_sync_employee_ledger()`;
- `_sync_employee_ledger()` синхронізує active assignments для:
  - `employee`;
  - optional `assignment`;
  - optional `leave_type`;
  - optional `policy`;
- після sync endpoint повертає актуальний ledger.

Regression test:

- `test_employee_ledger_endpoint_syncs_due_accruals_before_returning`
- сценарій:
  - legacy opening `7.00` на `2026-06-29`;
  - monthly accrual `+2.00`;
  - `timezone.localdate()` patched to `2026-07-01`;
  - перший запит до `/api/leave/ledger/?employee=...` повертає accrual
    `2026-07-01`, `amount=2.00`, `balance_after=9.00`.

Commit:

- `9139507` - `Fix leave ledger accrual sync`

Prod deploy hotfix:

- GitHub Actions run `28512728687` success;
- prod services recreated:
  - `web`;
  - `celery`;
  - `celery-beat`;
  - `frontend`;
- migrations не потрібні.

Prod verification:

- `docker compose ps` - services up;
- prod `python manage.py check` - ok;
- `https://hr.vidnova.app/changelog` - 200;
- `/api/auth/status/` - 200;
- inside prod Django shell:
  - `LeaveLedgerEntryViewSet` має `_sync_employee_ledger`;
  - employee `58`, leave type `1` top ledger row:
    `2026-07-01 accrual 2.00 balance 9.00`.

## Як зараз працює логіка

### Баланс

Джерело істини: `LeaveLedgerEntry`.

`LeaveBalance` - кеш для UI. Він оновлюється після:

- assignment sync;
- policy assignment;
- request approval/cancel/reject reversal;
- balances endpoint;
- ledger endpoint після hotfix.

### Нарахування

Викликається через `sync_assignment_balance()`.

Ключові правила:

- opening balance створюється один раз;
- legacy opening date є baseline, і due accruals `<= opening_date` не
  створюються;
- due dates залежать від `frequency` і `accrual_timing`;
- `period_amount` береться явно або виводиться з `annual_allowance`;
- `max_balance` обрізає accrual;
- seniority levels створюють окремі accrual entries;
- idempotency key не дає дублювати записи.

### Заявки

На `approve`:

- знаходиться active assignment;
- валідяться policy rules;
- amount рахується або береться з request;
- створюється `LeaveLedgerEntry(kind=request)`;
- кеш балансу оновлюється.

На `cancel` або `reject` після `approved`:

- створюється `LeaveLedgerEntry(kind=adjustment)` як reversal;
- кеш балансу оновлюється.

## Поточний стан робочого дерева після hotfix

Після commit/push/deploy `9139507` backend-файли чисті.

Локально лишалися незакоммічені frontend WIP:

- `frontend/src/App.tsx`;
- `frontend/src/styles/index.css`;
- `frontend/src/views/settings/SettingsLeaveTypesView.tsx`.

Це потрібно врахувати наступній сесії:

- перед commit зробити `git diff`;
- перевірити, що WIP відповідає очікуваному UI;
- запустити `npm run build`;
- бажано перевірити сторінки вручну в браузері.

## Перевірки, виконані сьогодні

Backend:

```bash
DB_ENGINE=sqlite python3 manage.py test apps.leave.tests.LeavePolicyAccrualTests -v 2
DB_ENGINE=sqlite python3 manage.py test apps.leave -v 1
python3 manage.py check
git diff --check
```

Результат:

- `LeavePolicyAccrualTests`: 13/13 OK;
- `apps.leave`: 36/36 OK;
- `manage.py check`: ok;
- `git diff --check`: ok.

Frontend для основного leave release:

```bash
cd frontend && npm run build
```

Результат: build passed, Vite warning по chunk size не блокував deploy.

Prod:

```bash
gh run view 28512728687 --repo Alex1981-tech/HR_vidnova
ssh root@172.16.33.14 'cd /root/hr_vidnova && docker compose -f docker-compose.prod.ghcr.yml ps'
ssh root@172.16.33.14 'cd /root/hr_vidnova && docker compose -f docker-compose.prod.ghcr.yml exec -T web python manage.py check'
curl -k -s -I https://hr.vidnova.app/changelog
curl -k -s https://hr.vidnova.app/api/auth/status/
```

## Відкриті питання і наступні кроки

### Найважливіше

1. ✅ Локальний frontend WIP по leave UI / policy settings / org graph
   підготовлений до релізу `1.0.39`.
2. Повністю пройти вручну:
   - `/settings/leave-types`;
   - `/people/employees/58/absence`;
   - create request modal;
   - delete request confirmation;
   - policy people drawer;
   - approval preview block.
3. ✅ Changelog оновлено записом `1.0.39`.

### Backend/domain

1. Реальна approval chain:
   - snapshot approver steps при створенні/submit заявки;
   - перевірка, що поточний user є потрібним approver-ом;
   - skip unassigned approvers;
   - substitute approvers.
2. Carryover/expiration:
   - зараз fields є, але year-boundary engine ще не готовий.
3. Scheduled accrual:
   - потрібен management command або Celery beat task;
   - зараз endpoint-и можуть lazy-sync баланс, але це не заміна планового job-а.
4. Daily request entries:
   - немає `LeaveRequestEntry` з поденною розбивкою;
   - modal UI показує поденно, але backend поки зберігає aggregate amount.
5. Робочі графіки:
   - `working_days` зараз фактично Mon-Fri;
   - потрібно зв'язати з реальними working patterns, якщо бізнес очікує
     індивідуальні графіки.
6. `not_working_unpaid` semantics:
   - поточний delta = `+amount`;
   - треба підтвердити, чи для `За власний рахунок` ми показуємо used counter,
     separate ledger metric або balance.
7. Full leave RBAC:
   - delete request вже має `leave.delete_requests`;
   - решту actions треба перевести на fine-grained permissions.

### Import/PeopleForce

1. PeopleForce public API не дає повну формулу accrual settings.
2. Для реальних політик потрібно:
   - ручне налаштування в HR Vidnova;
   - або окремий export з PeopleForce;
   - або reconstruction з history з ручним review.
3. Legacy balances мають залишатися baseline, щоб не задвоїти старі
   нарахування.

## Rollback notes

Для hotfix `9139507` rollback простий:

- повернути prod image/branch до `3e6f3fe`;
- redeploy `web`, `celery`, `celery-beat`, `frontend`.

Міграцій у hotfix не було.

Для release `3e6f3fe` rollback складніший, бо там застосовані migrations
`leave.0009` і `leave.0010`. Перед rollback цього release потрібен окремий
план по даних.
