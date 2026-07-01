# HR Vidnova — журнал сесій

> Короткий лог робочих сесій з Claude. Найновіше — зверху. Читати на старті.

## Орієнтація по проєкту (постійна шпаргалка)

- **Що це:** внутрішня HR-система клініки Vidnova. Не payroll/ERP — touch-first, MVP операційні задачі (хто працює, хто відсутній, хто кому підпорядкований, де документ, які заявки чекають).
- **Домен (план):** `hr.vidnova.app`. Папка: `/home/serv/hr_vidnova`.
- **Стек:** Django + DRF, PostgreSQL, Celery + Redis, React 19 + Vite + TS.
- **Git:** репо ініціалізовано, але **0 комітів** (branch `main`, untracked). safe.directory не налаштований.
- **Запуск:** усе піднято через `docker compose` (працює зараз):
  - backend `127.0.0.1:8050`, frontend dev `127.0.0.1:5178`, postgres `5444`, redis `6394`, + celery.
- **БД:** реальні дані в **Postgres**, а не в `db.sqlite3` (той у репо — порожній артефакт, 0 рядків).

### Apps (backend)
- `employees` — найбільший: 17 міграцій, моделі Employee/Department/Clinic/Position/ManagerAssignment/Team/JobLevel/EmploymentType тощо, avatar_import, management-команди.
- `skud` — СКУД (uprox/zkteco), services.py, TimeCorrectionRequest. Подій поки 0.
- `leave` — заявки на відпустку, LeaveBalance/LeaveRequest.
- `knowledge` — база знань, категорії/документи/вкладення (імпорт з PeopleForce).
- `integrations` — PeopleForce-compat API (`/api/public/v3/`, `/api/peopleforce-compatible/v3/`).
- `dashboard`, `selfservice` (`/api/me/`).

### Frontend
- Фактично **моноліт `frontend/src/App.tsx` ~11.6k рядків** + `api/client.ts` (673), `types/api.ts` (464), `i18n/locales.ts` (1275).
- Залежності: react-router-dom 7, lucide-react, `@gravity-ui/graph` (граф підпорядкування).

### Дані зараз (Postgres)
employees 167 · departments 26 · clinics 7 · positions 80 · leave_req 218 · knowledge_doc 148 · skud_events 0.

### Відкриті питання (з README/concept)
- prod read-only доступ до БД FotoPacients + політика merge;
- формат/API інтеграції зі СКУД;
- правила округлення робочого часу/запізнень/переробок;
- маршрут узгодження відпусток;
- спосіб авторизації співробітників.

### Ключова документація
`docs/concept-and-implementation-plan.md`, `docs/ui-reference-structure.md`,
`docs/roles-and-legacy-data-import.md`, `docs/peopleforce-data-import-plan.md`,
`docs/skud-sunc-v4-integration-plan.md`, `docs/development.md`.

---

## Сесії

### 2026-06-30 (пізно) — PF-редактор ролей (Фази 1–3) + склад Адміністратори + прод-деплой
**Запушено й задеплоєно на прод** (`a2fda51`→`7116579`, реліз ~1.0.37). Детально:
[docs/сессии/2026-06-30-roles-ui-people-and-pf-plan.md](сессии/2026-06-30-roles-ui-people-and-pf-plan.md).
- **Адміністратори**: people-picker → **таблиця складу** (аватари, Посада/Департамент/
  Локація, сортування) + «+ Додати» (модалка) + kebab (Деактивувати/Видалити). Backend
  `members`/`member-action` з guard останнього адміна.
- **Редактор ролі = повна копія PeopleForce**: вкладки **Компанія** (категорії→секції→
  чекбокси/градуйовані/мультиселекти «Звіти компанії»/«Розділи налаштувань») і **Люди**
  (field-level: ліва навігація вкладок профілю → акордеони груп → поля/таблиці з
  Немає·Перегляд·Редагування). Реєстр прав розширено до PF 1:1 (~25 кодів). Sticky-футер,
  dirty-guard. «Люди стосовно себе» = лише вкладка «Люди». Коміти `f5f909c`/`d5019ad`/`d9adc17`.
- **Лічильники членства** виправлені (computed-ролі): Усі люди/self = всі активні (159),
  Менеджери=28, Лідери=5. **Число «Люди» клікабельне** → дровер списку людей ролі
  (пошук, аватари, пагінація). Описи ролей приведені до формулювань PF. 104 тести OK.
- **Прод (172.16.33.14)**: оновлено через `docker-compose.prod.ghcr.yml`, засіяно RBAC
  (5 ролей + 22 grants), **імпортовано 6 адмінів** (Кузьменко/Штанько/Гузенко/Турчененко/
  Нагорний/Бондарець), `RBAC_ENFORCE=False`. ⚠️ Інцидент: помилковий дефолтний
  `docker compose up` зніс GHCR-frontend:8096 → сайт 502 ~15хв; відновлено. Урок →
  memory `hr-prod-deploy-ghcr-compose`.

### 2026-06-30 — Security hardening + RBAC backend
- Hardening: P0 safety gate, P2 приватна media (X-Accel), P11 CI-гейти, P4 nh3-санітайзер, P1 negative authz-тести.
- **Весь backend RBAC (Этапи 0–6)**: permission registry, моделі ролей/прав/призначень/audit (`access/0002`), scope engine (`rbac.py`), DRF enforcement flag-gated (`RBAC_ENFORCE` default OFF=shadow), management API `/api/access/`, AuthStatus.access. Матриця прав узгоджена Alex (5 рішень), засіяна (71 grant). **Alex (user 2) — admin у dev.**
- Усе локально, **не запушено**. Повний suite зелений (падають лише leave-тести — WIP Alex).
- Далі: фронт `/settings/roles` (Этап 7). Детальний запис: [docs/сессии/2026-06-30-rbac-and-hardening.md](сессии/2026-06-30-rbac-and-hardening.md).

### 2026-06-30 — Реальні політики відпусток
- Замінили заглушку `/settings/leave-types` на основу реальної моделі політик: `LeavePolicy`, `LeavePolicyAccrualRule`, `EmployeeLeavePolicyAssignment`, `LeaveLedgerEntry`.
- Додали API політик/призначень/ledger, backfill з PeopleForce балансів, baseline-захист від подвійного нарахування, UI-крок `Нарахування та перенесення`, а також lifecycle заявок: approve списує баланс, cancel/reject повертає через ledger-корекцію.
- Детальний запис рішень, перевірок і наступних кроків: [docs/leave/sessions/2026-06-30-leave-policies.md](leave/sessions/2026-06-30-leave-policies.md).

### 2026-06-26 (пізно) — Звіти + «Дані про людей»
- **Звіти** (на проді 1.0.08): головна `/reports` (групи Основні/CoreHR, компактні картки) + 3 аналітичні сторінки `headcount`/`turnover`/`tenure` на **recharts**. Backend `/api/reports/*` рахує з Employee. Переви­користовувані чарти у `frontend/src/views/reports/shared.tsx`. Цифри на барах/лінії (`LabelList`).
- **«Дані про людей»** `/settings/people-data` (закомічено, **НЕ запушено/деплоєно**): backend моделі `EmployeeFieldGroup`/`EmployeeField`/`EmployeeFieldTable` + `Employee.custom_fields` (міграції 0019/0020 seed). API `field-groups`/`fields`/`field-tables`. Сторінка `views/settings/PeopleDataSettingsView.tsx` (вкладки, перемикачі видимості, add/delete кастомних полів, drag-reorder груп, summary-chips). **Профіль** `EmployeeAdminProfileView` тепер рендерить панелі з конфігу (увімкнені поля, порядок груп) + custom_fields у серіалізаторі.
- **Лишилось завтра (фаза 2):** введення/редагування **значень** кастомних полів на профілі (зараз `-`), редагування кастом-поля (олівець-заглушка), таблиці (+Таблиця), summary-edit, кнопки шапки Нове поле/Нова таблиця. + відкладений **робочий фільтр headcount** (date-range + Рівень/Департамент/Локація). Push+deploy people-data — коли скажеш.

### 2026-06-26 — Оргграф `/people/org` (PeopleForce-стиль)
Усе у `frontend/src/App.tsx` (`OrgView` / `OrgGraphCanvasView` / `composeOrgRows`) + `styles/index.css`. Граф на `@gravity-ui/graph`.
- **Гібридний вертикальний layout**: листкові групи підлеглих стекуються вертикальною колонкою (`composeOrgColumn`), хребет керівників — горизонтально. Правило перемикання — **частка листків ≥ 0.8** (`leafShare`), щоб «майже-все-листя» (напр. Квакуша з 1 під-керівником) теж було вертикальним, а CEO/Нагорний лишались горизонтальними. `parentX` у `OrgRowsLayout`.
- **Центрування**: `centerOnBlock` центрує саме той вузол, що розгортаєш/згортаєш (через `pendingFocusRef`), а не рефітить весь граф. `fitOrgRect` переписаний на ручний масштаб + центрування всього контенту + захист від нульових розмірів канви (fullscreen/mount більше не показують пусто).
- **Сітка**: дотси gravity зроблені прозорими → видно статичний CSS-фон `.org-canvas` (прив'язаний до країв).
- **Дропдаун «Людина ▾»**: пошук + список співробітників (аватар+посада) + «Показати всю структуру»; вибір ре-рутить граф на піддерево (`focusPersonId`).
- **Панель «Переглянути налаштування»**: Поля картки (Фото/Посада/Департамент/Локація) + Компактний вигляд + Ієрархія (Менеджер). `cardFields` прокинуто в `OrgGraphBlockCard`.
- **Експорт → PDF**: `exportOrgPdf` серіалізує поточний layout (`buildPeopleOrgGraph`) у HTML+SVG (картки з фото/бейджами + полілінії конекторів) і друкує (Зберегти як PDF). CSV прибрано.
- **«Розгорнути все»** (Maximize2) — тепер реально розгортає всі вузли (`expandAllNodes` + `collectExpandablePersonIds`). **«Заповнити»** — фіт усього контенту.
- **Тулбар**: прибрано сіру «полосу» — старе правило `.org-toolbar` (рядок 3010, `background rgba(255,255,255,.42)` + full-bleed margins) перекрито чистим у org-правилі.
- `tsc -b` чисто. Візуально перевірено в браузері (крім друку PDF — не тригерив діалог print).
- **Не комічено** (git досі 0 комітів). Мертві хелпери лишились (`zoomToGraph`, `readableOrgRect`, `orgModeLabel` — без noUnusedLocals не заважають).

### 2026-06-26 — Перша орієнтація
- Провів огляд проєкту (структура, apps, frontend, runtime, дані). Підсумок — у шпаргалці вище.
- Створив цей файл журналу сесій (`docs/sessions.md`).
