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
