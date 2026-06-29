# План впровадження фічі «Проєкти» (Time-tracking Projects) — HR Vidnova

> Статус: ⏳ чернетка плану · Дата: 2026-06-29 · Еталон: PeopleForce `/time/projects`

## Мета

Додати новий розділ «Проєкти» в межах модуля «Присутність» (`/attendance/projects`), за еталоном PeopleForce: список проєктів (активні/архівні), модалка створення, сторінка проєкту з учасниками-співробітниками та KPI-плейсхолдерами годин. Прив'язка реального часу/годин до проєкту (per-project time tracking) у MVP **не реалізується** — години чесно показуються як `0 / —`. Бекенд будуємо як окремий Django-app `apps.projects` за зразком `apps/leave/`, фронт — дві нові view-компоненти у моноліті `frontend/src/App.tsx` з дотриманням дизайн-системи.

## Архітектурні рішення

- **Окремий app `apps.projects`** (не розширення `apps.skud`): чиста доменна межа, проста міграція, відповідає патерну `apps/leave`. Префікс API `/api/projects/`.
- **M2M Employee без through-моделі** у MVP. Якщо в майбутньому знадобляться per-member метадані (дата призначення, ставка, роль) — додамо through-модель `ProjectMembership` окремою міграцією (див. «Майбутні кроки»).
- **`emoji` як `CharField`** (не FK на довідник): мінімум складності, відповідає еталону (select з кількох емодзі на фронті).
- **Маршрутизація фронта** через розширення наявного `attendanceRouteFromPathname` + дві гілки рендеру в `AttendanceView` (НЕ новий top-level `Section`), бо «Проєкти» концептуально живуть всередині «Присутності».
- **Переюз `EmployeeCompactSerializer`** (`apps/employees/serializers.py:516`) для блоку учасників — не плодимо дубль-серіалайзери.

---

## Фаза 1 — Бекенд (app `apps.projects`)

Створюється новий каталог `apps/projects/` за структурою `apps/leave/`.

### Кроки

- [ ] ⏳ **`apps/projects/__init__.py`** — порожній.
- [ ] ⏳ **`apps/projects/apps.py`** — `class ProjectsConfig(AppConfig)` з `default_auto_field = "django.db.models.BigAutoField"`, `name = "apps.projects"`.
- [ ] ⏳ **`apps/projects/models.py`**:
  - Локальний abstract `TimestampedModel` (created_at/updated_at), як у `apps/leave/models.py:7`.
  - Модель `Project(TimestampedModel)`:
    - `name = models.CharField(max_length=180)`
    - `emoji = models.CharField(max_length=16, default="📁", blank=True)`
    - `is_archived = models.BooleanField(default=False, db_index=True)`
    - `order = models.PositiveIntegerField(default=0, db_index=True)`
    - `members = models.ManyToManyField("employees.Employee", related_name="projects", blank=True)`
    - `Meta.ordering = ["order", "name"]`
    - `def __str__(self): return self.name`
    - `legacy_peopleforce_id = models.CharField(max_length=120, blank=True, db_index=True)` — узгоджено з конвенцією інших моделей; додати одразу, щоб не плодити міграції.
- [ ] ⏳ **`apps/projects/serializers.py`**:
  - `ProjectListSerializer(ModelSerializer)` — поля `("id", "name", "emoji", "is_archived", "order", "member_count")`; `member_count` через анотацію `Count("members")` у queryset (уникнути N+1).
  - `ProjectDetailSerializer` — список + `members = EmployeeCompactSerializer(many=True, read_only=True)` (імпорт з `apps.employees.serializers`). Fields: `(..., "members", "member_count", "created_at", "updated_at")`.
  - `ProjectWriteSerializer` (create/update) — поля `("id", "name", "emoji", "is_archived")`; `emoji` default `"📁"`; у `create` авто-`order = (last.order + 1)` за зразком `LeaveTypeSerializer.create`.
  - Рекомендація: один viewset із `get_serializer_class()` (list vs detail vs write), `to_representation` → detail після write.
- [ ] ⏳ **`apps/projects/views.py`**:
  - `class ProjectViewSet(viewsets.ModelViewSet)` з `permission_classes = [ConfiguredReadOnlyOrAuthenticated]`.
  - `get_queryset()`: `Project.objects.annotate(member_count=Count("members")).prefetch_related("members", "members__position")`; фільтр `?archived=` (true/false/1/0); відсутній параметр = всі; фільтр `?q=` → `name__icontains`.
  - `get_serializer_class()`: list→List, retrieve→Detail, create/update→Write; повертати detail-представлення після write.
  - `@action(detail=True, methods=["post"], url_path="add-members")` — `{"employee_ids": [..]}` → `members.add(*ids)` → detail.
  - `@action(detail=True, methods=["post"], url_path="remove-members")` — `members.remove(*ids)` → detail.
  - `@action(detail=True, methods=["post"], url_path="archive")` / `unarchive` — перемикають `is_archived`.
- [ ] ⏳ **`apps/projects/urls.py`** — `DefaultRouter`, `router.register("", ProjectViewSet, basename="project")` → `/api/projects/`. Якщо порожній префікс не реєструється — `register("items", ...)` і синхронно оновити `client.ts`.
- [ ] ⏳ **`apps/projects/admin.py`** — `list_display=("name","emoji","is_archived","order")`, `list_filter=("is_archived",)`, `search_fields=("name",)`, `filter_horizontal=("members",)`.
- [ ] ⏳ **`apps/projects/tests.py`** — `APITestCase` (зразок `apps/leave/tests.py`): create-defaults-emoji, list-member-count, filter-archived, filter-q, add/remove-members, archive/unarchive, requires-auth-for-write.
- [ ] ⏳ **`apps/projects/migrations/__init__.py`** — створиться `makemigrations`.

### Реєстрація app

- [ ] ⏳ **`config/settings.py`** — `"apps.projects",` у `INSTALLED_APPS` (після `"apps.announcements",`, ~48).
- [ ] ⏳ **`config/urls.py`** — `path("api/projects/", include("apps.projects.urls")),` (поряд з рядками 67-71).

### Міграції (Docker)

- [ ] ⏳ `docker compose exec backend python manage.py makemigrations projects`
- [ ] ⏳ `docker compose exec backend python manage.py migrate`
- [ ] ⏳ `docker compose exec backend python manage.py test apps.projects`
- [ ] ⏳ Ручна перевірка: `GET /api/projects/`, `POST` створення, actions.

**Файли Фази 1:** `apps/projects/{__init__,apps,models,serializers,views,urls,admin,tests}.py`, `apps/projects/migrations/`, `config/settings.py`, `config/urls.py`.

---

## Фаза 2 — Фронт: список проєктів + модалка створення

### Типи та API-клієнт

- [ ] ⏳ **`frontend/src/types/api.ts`**:
  ```ts
  export type ProjectMember = {
    id: number; full_name: string; position_name?: string;
    avatar_url?: string; avatar_local_url?: string;
  };
  export type Project = {
    id: number; name: string; emoji: string;
    is_archived: boolean; order: number; member_count: number;
    members?: ProjectMember[];
    created_at?: string; updated_at?: string;
  };
  export type ProjectPayload = { name: string; emoji?: string; is_archived?: boolean };
  ```
- [ ] ⏳ **`frontend/src/api/client.ts`** — методи за патерном `leaveTypes` (~849), `buildQuery`+`normalizeList`:
  ```ts
  projects: (params: { archived?: boolean; q?: string; page?: number; page_size?: number } = {}) =>
    request<...>(`/api/projects/${buildQuery(params)}`).then(normalizeList),
  project: (id) => request<Project>(`/api/projects/${id}/`),
  createProject, updateProject(PATCH), deleteProject(DELETE),
  archiveProject(POST .../archive/), unarchiveProject,
  addProjectMembers(id, employee_ids[]) POST .../add-members/,
  removeProjectMembers(id, employee_ids[]) POST .../remove-members/,
  ```
  > Єдина крапка узгодження з бекендом — фінальний URL колекції.

### Маршрутизація

- [ ] ⏳ Розширити `AttendanceRoute` (513) і `attendanceRouteFromPathname` (515): додати `{mode:'projects'}` і `{mode:'project'; id}`.
- [ ] ⏳ Хелпери: `attendanceProjectsPath()` → `/attendance/projects`, `attendanceProjectPath(id)`.
- [ ] ⏳ `AttendanceView` (8343-8354): рендер `ProjectsListView` / `ProjectDetailView` за `mode`.

### Кнопка-вхід

- [ ] ⏳ Кнопка «Управління проектами» (~8456) → `onClick={() => navigate(attendanceProjectsPath())}`.

### Компонент `ProjectsListView`

- [ ] ⏳ За зразком `CompanyAttendanceView` (8357): стан `tab`/`search`/`page`/`rows`/`total`/`loadState`; `useEffect` → `api.projects({archived: tab==='archived', q, page})`.
- [ ] ⏳ header `page-header compact`: «‹ Назад» → `/attendance`, `<h1>`«Проєкти», праворуч «...» + primary «+ Новий проект».
- [ ] ⏳ `SectionTabs`: «Активний»/«Архівні». Пошук `wide-search` + «Відображено N з M».
- [ ] ⏳ Таблиця: «Імʼя» (емодзі+назва) | «Співробітники» (`member_count`) | «...». Клік рядка → `attendanceProjectPath(id)`.
- [ ] ⏳ Стани loading/error/empty.

### Модалка «Новий проект»

- [ ] ⏳ `CreateProjectModal`: «Імʼя» (required) + «Емодзі» `<select>` (📁 📊 🚀 🎯 🛠️ 💼 📦 🧪…, дефолт 📁) + «Зберегти» → `createProject` → `navigate(attendanceProjectPath(created.id))`.

### i18n / CSS

- [ ] ⏳ `frontend/src/i18n/locales.ts` — блок `projects` (en/uk/pl): title/tabs/newProject/search/displayed/col*/modal*/save/back/empty*.
- [ ] ⏳ `frontend/src/styles/index.css` — класи `attendance-projects-*` ЛИШЕ через токени дизайн-системи (`docs/design-system.md`): заголовок 20px, body 13px, ваги 400/500/600, 4px-шкала, токени кольорів. Максимальний переюз `page-header`/`wide-search`/`segmented`/таблиць.

**Файли Фази 2:** `types/api.ts`, `api/client.ts`, `App.tsx`, `i18n/locales.ts`, `styles/index.css`.

---

## Фаза 3 — Фронт: сторінка проєкту + учасники

### Компонент `ProjectDetailView`

- [ ] ⏳ Props `{projectId, copy}`; стан `project`/`month`/`search`/`loadState`; `useEffect` → `api.project(id)`.
- [ ] ⏳ Header: «‹ Назад» → projects, «емодзі+назва», «...» (Перейменувати/Архівувати/Видалити), «+ Людина» (пікер).
- [ ] ⏳ Пошук (локальний фільтр учасників) + «Фільтр» (no-op у MVP).
- [ ] ⏳ Місячні контролі «Поточний місяць ‹ › <місяць, рік>» — переюз `monthQueryValue`/`getMonthRange`.
- [ ] ⏳ Графік-картка «Відстежено годин / днів» — placeholder «Немає даних».
- [ ] ⏳ KPI-картки: «Загальна кількість годин» = `0`, «Середнє по співробітниках» = `—` (чесні нулі).
- [ ] ⏳ Таблиця учасників: «Повне імʼя» (аватар+ім'я+посада) | «Відпрацьовано» `—` | «Перерва» `—` | «...» (прибрати → `removeProjectMembers`).
- [ ] ⏳ Empty-state: «Немає людей, призначених для проєкту» / «Призначте співробітника…» / «+ Люди».

### Пікер людей (`ProjectMembersPicker`)

- [ ] ⏳ Модалка з `api.employees({status:'active', q})` (метод уже є, 8382), мультивибір чекбоксами, виключення вже-членів, «Додати» → `addProjectMembers` → оновити з detail-відповіді.

### i18n / CSS

- [ ] ⏳ Доповнити `projects` ключами сторінки: addPerson/filter/currentMonth/chart*/kpi*/col*/noMembers*/addPeople/picker*/confirm*.
- [ ] ⏳ CSS KPI/графік/таблиці — токени, переюз наявних card/table класів.

**Файли Фази 3:** `App.tsx`, `api/client.ts`, `i18n/locales.ts`, `styles/index.css`.

---

## Послідовність і залежності

1. Фаза 1 (бекенд) — завершити й перевірити (`test` + ручний `curl`) ПЕРШОЮ.
2. Фаза 2 залежить від фінального URL роутера (єдина крапка узгодження).
3. Фаза 3 залежить від detail-серіалайзера з `members` і навігації з Фази 2.

## Ризики

- **URL роутера на порожньому префіксі** — перевірити; за потреби явний префікс + синхронний `client.ts`.
- **N+1 на `member_count`** — обов'язково `annotate(Count("members"))`.
- **Дизайн-система** — рев'ю CSS за `docs/design-system.md`, без raw-px/raw-hex/700+.
- **App.tsx ~20k рядків** — нові компоненти поряд з attendance-view (8357+); винесення в окремий файл — поза скоупом MVP.
- **Контракт `?archived=`** (відсутній = всі) узгодити фронт↔бекенд.

## Відкриті питання

1. Фінальний API-шлях колекції: `/api/projects/` чи `/api/projects/items/`? (Фаза 1).
2. Набір дій у «...» меню (Архівувати/Видалити/Перейменувати); підтвердження видалення проєкту з членами.
3. Drag-reorder у MVP чи лише алфавіт (поле `order` закладено, UI-reorder — майбутнє).
4. Набір емодзі в селекті — фіксований список чи повний picker.
5. Права: усі автентифіковані чи лише HR/admin (зараз `ConfiguredReadOnlyOrAuthenticated`).

## Майбутні кроки (поза MVP)

- [ ] Per-project облік годин: прив'язка attendance-періодів (`apps.skud`) до проєкту → реальні «Відпрацьовано/Перерва», KPI, графік.
- [ ] `ProjectMembership` through-модель (дата призначення, роль, ставка).
- [ ] Експорт, фільтри на сторінці проєкту.
- [ ] Drag-reorder проєктів (action `reorder` за зразком `apps/leave/views.py:20`).
- [ ] Імпорт з PeopleForce (`legacy_peopleforce_id` закладено).

---

## Журнал

- 2026-06-29 — план створено (Plan-агент), збережено. Бекенд-конвенції звірені (`apps/leave`, DRF router, `ConfiguredReadOnlyOrAuthenticated`, пагінація `{count,results}`→`{items,total}`). Початок реалізації — за командою.
