# План: сторінка співробітника `/people/employees/:id`

Референси: `docs/фото/image*.png` (PeopleForce). Мета — профіль співробітника з PF-like header, вкладками, editable people data, документами, відсутностями, time, assets і додатковими підсторінками.

Статус: ✅ зроблено · 🚧 частково · ⏳ todo · ⛔ свідомо заглушка

## Референси

- `image.png`, `image copy.png`, `image copy 2.png`, `image copy 33.png`, `image copy 34.png` — profile shell/header, `Особисте`, права summary-колонка.
- `image copy 3.png` — dropdown `Більше`.
- `image copy 4.png` — `Робота` + права `Хронологія`.
- `image copy 5.png`, `image copy 14.png`, `image copy 15.png` — compensation subtabs/table setup.
- `image copy 6.png` — `Відсутності`: balance cards, `Запити`, `Історія`.
- `image copy 7.png` — `Time` calendar/timesheet.
- `image copy 8.png`-`10.png`, `image copy 18.png`-`21.png` — documents profile/settings/upload.
- `image copy 11.png`-`13.png` — people-data table/column settings.
- `image copy 16.png`, `image copy 17.png` — leave types settings.
- `image copy 22.png`-`26.png` — `Більше`: emergency contacts, children, notes.
- `image copy 27.png`-`32.png` — per-block edit, validation, education/certificate/file modal.

## Поточний стан коду, який треба врахувати

- ✅ Профіль уже має header, banner/avatar, вкладки, `Більше`, config-driven `Особисте/Робота/Компенсація`, table panels і embed `EmployeeAttendanceDetailView`.
- ✅ `EmployeeFieldGroup`, `EmployeeField`, `EmployeeFieldTable` існують; settings `Дані про людей` уже має таблиці/колонки, а профіль зберігає рядки в `Employee.custom_fields['table_<id>']`.
- ✅ Сід `employees.0022_seed_work_compensation_tables` уже створює PF-like таблиці `Посади`, `Робота`, `Базова компенсація`, `Додаткові компенсації`.
- ✅ `LeaveType`, `LeaveRequest`, `LeaveBalance` уже існують і доступні через `/api/leave/types/`, `/api/leave/requests/`, `/api/leave/balances/`. Це не новий backend, а доробка існуючої схеми.
- ✅ `EmployeeDocumentFolder` і `EmployeeDocument` уже існують, але `local_file` read-only у serializer; multipart upload з профілю ще відсутній.
- 🚧 Assets API уже прокидує `responsible_ids` у CMMS, але це CMMS employee id, не HR employee id. Для профілю потрібен HR→CMMS bridge.
- ⏳ `EmergencyContact`, `Dependent`, `EmployeeNote` відсутні.
- ⏳ Немає role/object permission matrix для HR/manager/self/compensation/documents; більшість HR API зараз спирається на `ConfiguredReadOnlyOrAuthenticated` і dev flags.

## Архітектурні рішення

### 1. URL-driven вкладки

- `/people/employees/:id` лишається alias для `personal`.
- Нові deep links:
  - `/people/employees/:id/personal`
  - `/people/employees/:id/work`
  - `/people/employees/:id/compensation`
  - `/people/employees/:id/absence`
  - `/people/employees/:id/time?month=YYYY-MM`
  - `/people/employees/:id/documents`
  - `/people/employees/:id/tasks`
  - `/people/employees/:id/workflow`
  - `/people/employees/:id/assets`
  - `/people/employees/:id/emergency`
  - `/people/employees/:id/dependents`
  - `/people/employees/:id/notes`
- `activeTab` має синхронізуватися з pathname/search, щоб back/forward, reload і пряме посилання відновлювали вкладку.
- Для `Time` місяць живе в query профілю (`month=YYYY-MM`), а стрілки місяця не ведуть на `/attendance/...`.

### 2. Layout rules

- `Особисте`: main column + права summary-колонка `Головна` як у PF.
- `Робота`: main column + права `Хронологія` обов'язково для matching `image copy 4.png`.
- `Компенсація`, `Відсутності`, `Time`, `Документи`, `Більше/*`: full-width panel.
- Mobile/tablet: tabs horizontal scroll, права колонка переходить нижче main, таблиці та time calendar мають внутрішній horizontal scroll, модалки майже full-width зі sticky footer.

### 3. Permission/contract boundary

- Додати окремий permission/role matrix до реалізації редагування:
  - HR/admin: повний профіль, people-data settings, documents, leave setup.
  - Manager: перегляд підлеглих, обмежені поля, leave/team/time за scope.
  - Employee self: тільки self-visible поля, свої відсутності/time/documents за правилами.
  - Compensation: окремий privilege, не просто authenticated.
  - Documents: upload/download/delete окремо від перегляду.
- Per-block edit не повинен використовувати широкий `EmployeeSerializer` напряму. Потрібен restricted action/serializer з allowlist системних полів профілю.
- Dev flags `HR_PUBLIC_READ_API` / `HR_PUBLIC_WRITE_API` не вважати production-поведінкою.

## Backend/API roadmap

### A. People-data fields/tables 🚧

- [x] `EmployeeFieldGroup/EmployeeField/EmployeeFieldTable` і CRUD viewsets існують.
- [x] Settings UI має таблиці/колонки, boolean уже є на frontend і в compensation seed.
- [x] Додати backend validation для `EmployeeFieldTable.columns` (serializers.py `validate_columns`):
  - `key` stable slug, unique per table, не порожній;
  - `label` required;
  - `type` тільки allowlist;
  - `select.options` required/list;
  - `employee`/`boolean` не мають options;
  - `file` заборонений до появи attachment storage.
- [x] Додати `boolean` у `EmployeeField.FieldType` на backend (міграція 0027) + serializer validation (`validate`).
- [ ] `file` тип не додавати як generic field без backing model. Для сертифікатів/освіти потрібен row attachment design.
- [ ] Винести profile field-group loading у `frontend/src/api/client.ts` замість raw `fetch`.

### B. Atomic row API для таблиць ✅

Поточний PATCH усього `Employee.custom_fields['table_<id>']` працює, але має ризики full-JSON overwrite, немає row id, audit/concurrency і cleanup при зміні таблиці.

Рішення: залишити storage у `custom_fields` на MVP, але додати backend actions з row-level контрактом:

- [x] `GET /api/employees/employees/:id/table-rows/?table=:table_id`
- [x] `POST /api/employees/employees/:id/table-rows/`
- [x] `PATCH /api/employees/employees/:id/table-rows/:row_id/`
- [x] `DELETE /api/employees/employees/:id/table-rows/:row_id/`
- [x] Кожен row отримує `row_id`, `created_at`, `updated_at`; зміни в `transaction.atomic()` + `select_for_update()`.
- [x] Legacy-рядки без `row_id` ледаче backfill-яться на GET (міграція-на-читанні).
- [x] Frontend (`EmployeeTablePanel`) переведено з full-PATCH на row API (Фаза 1).
- Для rename/delete column не видаляти дані автоматично. Delete table у settings спочатку `is_enabled=false`; physical cleanup тільки окремою підтвердженою дією.

### C. Restricted profile update ⏳

- Додати action, наприклад `PATCH /api/employees/employees/:id/profile-block/`.
- Allowlist системних полів: `last_name`, `first_name`, `middle_name`, `email`, `personal_email`, `birth_date`, `gender`, `phone`, `phone2`, `telegram_id`, `facebook_url`, `instagram_url`.
- Read-only: `id`, `employee_number`, `legacy_peopleforce_id`, external ids, `peopleforce_fields`, `user`, імпортні технічні поля.
- `gender` не hardcoded `Жінка/Чоловік`: frontend вантажить `/api/employees/genders/`, зберігає `Gender.code` у `Employee.gender`.
- Custom values у тому ж block-save можна PATCHити як `{custom_fields_delta}`, але не замінювати весь JSON без merge/validation.

### D. Work domain sync ✅

`Робота` не може бути лише display у `custom_fields`, бо доменні моделі вже існують:

- `ManagerAssignment`
- `EmployeePositionHistory`
- `EmployeeEmploymentStatus`
- SKUD використовує employment/schedule доменну історію, не JSON-таблицю.

Реалізація (`apps/employees/work_sync.py`, тригер у `table_rows`/`table_row_detail`):

- [x] Таблиці `Посади`/`Робота` лишаються PF-like UI layer; маркер `EmployeeFieldTable.sync_target` (`positions`/`employment`) вмикає sync (міграції 0028/0029).
- [x] Save/PATCH/DELETE row у `Посади` дзеркалить КОЖЕН рядок у `EmployeePositionHistory` (keyed `hrtable:<row_id>`), а latest/current row → `Employee.position/department/division/clinic/job_level` + `ManagerAssignment`.
- [x] Save row у `Робота` → `Employee.employment_type` + `EmployeeEmploymentStatus` (working_pattern_name, comment).
- [x] Резолв select-колонок за **назвою** (опції = назви довідників, унікальні); `employee`-колонка зберігає id. Нерезолвлена назва НЕ обнуляє доменне поле (захист від втрати даних). Видалення рядка прибирає його історичний запис.
- ⏳ Майбутнє: перевести select-колонки на structured **IDs** замість назв (зараз name-resolution — функціонально коректний bridge).

### E. Leave ⏳

Не створювати `LeaveType` з нуля. Доробити існуючу модель:

- Поточні поля: `name`, `code`, `legacy_peopleforce_id`, `unit`, `color`, `requires_hr_approval`, `is_active`.
- [x] `unit` нормалізовано як канонічний tracking_unit `days|hours` (choices + serializer `validate_unit` мапить legacy-значення; importer `_normalize_leave_unit`; міграції 0004/0005). `icon`, `order` вже були.
- [x] Endpoint reorder для `/api/leave/types/` (вже існував).
- Profile tab вантажить:
  - `api.leaveTypes({page_size: 100})`
  - `api.leaveBalances({employee})`
  - `api.leaveRequests({employee})`
- `LeavePolicy`/accrual automation лишаються пізніше; у MVP показуємо наявні balances/history з `LeaveBalance.effective_on`.

### F. Documents ⏳

Використати існуючі `EmployeeDocumentFolder` / `EmployeeDocument`, але доробити:

- `EmployeeDocumentFolder.parent` self-FK + folder counts/search/soft-delete semantics.
- API client methods: folders, documents, upload, download/delete.
- Multipart upload action:
  - до 10 файлів;
  - max 200MB на файл;
  - allowlist типів (`pdf`, `doc`, `docx`, `png`, `jpeg`, `jpg`);
  - required `employee`, `folder`;
  - генерувати manual `legacy_peopleforce_id` (`manual:<uuid>`) для UniqueConstraint `(employee, legacy_peopleforce_id)`;
  - transactional create; per-file result/error для multi-upload.
- Download/delete semantics:
  - download local file через authenticated endpoint;
  - delete manual files дозволений за правами;
  - imported PeopleForce docs не видаляти фізично без окремої policy.

### G. Assets ⏳

- Не використовувати `responsible_ids=<HR employee id>` напряму.
- Додати bridge:
  - або `GET /api/assets/?hr_employee_id=:id`;
  - або backend resolves HR `Employee.external_*`/mapping у CMMS employee id і вже тоді прокидує `responsible_ids`.
- Тести мають mockати CMMS client і mapping.

### H. More models ⏳

- `EmergencyContact`: `employee`, `name`, `relationship`, `work_phone`, `home_phone`, `mobile_phone`, `address`, `order`.
- `Dependent`: `employee`, `name`, `birth_date`, `gender`, `description`.
- `EmployeeNote`: `employee`, `body_html`, `author`, `created_at`, `updated_at`.
- Для notes attachments потрібен окремий upload/attachment model і sanitization; knowledge media upload не переиспользовувати як є.

## Frontend/UX roadmap

### Фаза 0 — Profile shell і routing 🚧

- [x] Header/banner/avatar/name/role/location/actions/tabs уже є.
- [x] URL-driven active tab + active `Більше` state (`/people/employees/:id/:tab`, helpers `profileTabFromPathname`/`peopleEmployeeTabPath`; back/forward/reload/deep-link відновлюють вкладку; Time зберігає `?month`).
- [ ] Loading/not found/forbidden/error для direct URL `/people/employees/:id`, навіть якщо employee не в поточній сторінці списку.
- [ ] Top-level retry state.
- [ ] PF-like visual acceptance:
  - light gray page background;
  - compact cards;
  - 6-8px radius;
  - thin borders/subtle shadow;
  - small icon squares;
  - restrained purple active underline/buttons;
  - no nested cards.

### Фаза 1 — People-data settings/table infrastructure 🚧

- [x] Settings: tabs `Особисте/Робота/Компенсація`, groups, fields, tables, column modal.
- [x] Profile: table panels, add/edit/delete rows, boolean checkbox in table rows.
- [ ] Settings modal UX criteria from references:
  - reorder/drag affordance for columns;
  - bordered column list;
  - type menu with icons;
  - sticky footer;
  - empty/error states;
  - mobile internal scroll.
- [x] Switch profile table saves from full employee PATCH to atomic row API (`refreshTableRows` + `api.createTableRow/updateTableRow/deleteTableRow`).
- [ ] File column only after row attachment backend is ready.

### Фаза 2 — `Особисте` per-block edit ⏳

- [x] Config panels render by `tab=personal`.
- [ ] PF pattern: clicking `Редагувати` turns the current panel into a form, not a modal.
- [ ] Only one block edits at a time.
- [ ] Footer inside panel: `Скасувати` / `Зберегти`, sticky where needed.
- [ ] Inline validation, required markers, help text under field.
- [ ] Disabled save + spinner while saving.
- [ ] Error preserves draft values.
- [ ] System + custom fields save through restricted profile action.
- [ ] Field controls:
  - text/textarea/number/date/url;
  - clearable select;
  - employee picker;
  - boolean checkbox;
  - gender dictionary from `/api/employees/genders/`.
- [ ] Personal tables `Навички/Освіта/Ліцензії/Сертифікати` use table row API; certificate attachment waits for Documents/row attachment storage.

### Фаза 3 — `Робота` ⏳

- [x] Seeded tables `Посади` and `Робота` render on profile.
- [ ] Make PF display mandatory:
  - current/latest row as field grid;
  - add/edit row buttons;
  - right `Хронологія` with dated position rows;
  - history toggle/table for older rows.
- [ ] Use structured dictionary IDs, not static labels, for position/department/division/location/level/work type/schedule.
- [ ] Save rows through domain sync described in Backend D.
- [ ] Names to align with PF where relevant: `Посади`, `Статус роботи`, `Профілі посад`, `Цикл зайнятості`.

### Фаза 4 — `Компенсація` ⏳

- [x] Seeded tables `Базова компенсація` and `Додаткові компенсації` render.
- [ ] Subtabs are required for PF matching:
  - `Базова компенсація`
  - `Додаткова компенсація`
- [ ] One panel at a time with `+ Додати` / edit/delete row.
- [ ] Keep payroll/accrual calculation out of scope.
- [ ] Require compensation permission before showing/editing values.

### Фаза 5 — `Відсутності` ⏳

#### Settings `/settings/leave-types`

- [ ] Add route/rendering in settings.
- [ ] Use existing `/api/leave/types/`.
- [ ] Add `icon`, `order`, normalized `tracking_unit` migration.
- [ ] List with drag reorder, expand/collapse, `+`, `...` menu.
- [ ] Modal: name, unit days/hours, icon, color.
- [ ] Seed/defaults if DB is empty: Відпустка, Лікарняний, За власний рахунок, Віддалена робота, Особисті події, Декретна відпустка, Неробоча зміна.
- [ ] Buttons `Збори "Задонать відпустку"` and `Призначення` can be visible disabled/stub until policy work.

#### Profile tab

- [ ] Balance cards by leave type with `Створити запит`.
- [ ] `Запити`: filter/search/export controls, empty `Нічого не знайдено`.
- [ ] `Історія`: year/type controls, export, table from balances/history.
- [ ] Loading/empty/error per block.

### Фаза 6 — `Time` 🚧

- [x] `EmployeeAttendanceDetailView` exists and can be embedded.
- [ ] Embedded mode must remove duplicate page shell/header/back button.
- [ ] Month prev/next updates `/people/employees/:id/time?month=YYYY-MM`.
- [ ] Metrics/calendar/table skeletons.
- [ ] Calendar/table horizontal scroll on narrow screens.
- [ ] Permission/scope cases for manager/self/HR.

### Фаза 7 — `Документи` ⏳

#### Settings `/settings/documents`

- [ ] Add settings route.
- [ ] Tabs `Папки` / `Шаблони`; templates can stay hidden/stub.
- [ ] Folders table: name+description, document count, search, `+ Додати`, row actions.
- [ ] Modal: name, description, parent folder, disabled/hidden auto-assignment toggle until advanced work.
- [ ] CRUD folders + soft delete/active filtering.

#### Profile tab

- [ ] Folder/document table like `image copy 8.png`.
- [ ] Search by document/folder name.
- [ ] `Новий` dropdown contains only `Завантажити файл`.
- [ ] Upload modal:
  - folder select;
  - drag/drop and click picker;
  - selected files list;
  - drag-active state;
  - per-file progress/error;
  - disabled save without folder/files;
  - limits 10 files / 200MB.
- [ ] Document actions: download/delete by permission.

### Фаза 8 — `Більше` ⏳

Common subpage pattern:

- same profile header;
- active item in `Більше` dropdown and URL;
- one full-width panel;
- `+ Додати` action on real sections;
- empty state `Нічого не знайдено`;
- loading/error/retry.

Sections:

- `Завдання` ⛔ placeholder.
- `Воркфлоу` ⛔ placeholder.
- `Активи` ⏳ real cards from CMMS after HR→CMMS bridge.
- `Екстрені контакти` ⏳ list + add/edit modal from `image copy 22.png`, `image copy 23.png`.
- `Діти` ⏳ list + add/edit modal from `image copy 24.png`, `image copy 25.png`.
- `Примітки` ⏳ list + add modal from `image copy 26.png`; rich text + attachments require dedicated backend.

## Verification checklist

Backend:

- `python3 manage.py check`
- `python3 manage.py makemigrations --check --dry-run`
- focused tests:
  - employees: restricted profile patch, table column schema, row API concurrency/merge, document upload, More models;
  - leave: leave type CRUD/reorder/profile filters;
  - skud: embedded profile scope/permissions around attendance detail;
  - assets: CMMS mapping mocked.

Frontend:

- `npm run build`
- `npm run lint` if configured.
- Browser verification with desktop and mobile screenshots:
  - direct URLs for every profile tab;
  - back/forward tab switching;
  - per-block edit save/error;
  - documents upload states;
  - Time month navigation;
  - mobile tabs/tables/modal footer no overlap.

## Поза scope MVP

- Payroll/accrual calculation.
- Leave accrual automation/policies beyond displaying current imported balances/history.
- Document templates (`.docx`) and auto-assignment by employee fields.
- Real task/workflow engine.
- Replacing JSON table rows with normalized row tables. MVP uses atomic row actions over existing `custom_fields`, with a future migration path.
