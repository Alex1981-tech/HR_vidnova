# Session state — HR Vidnova hardening + RBAC

> Живой документ для быстрого восстановления контекста, если сессия оборвётся.
> Обновлять по ходу работы. Последнее сверху в журнале.

Дата старта: 2026-06-30
Правило: **не пушить без явной команды** Alex — коммитим локально, накапливаем.
Не коммитить secrets/.env/PII. Не откатывать параллельную работу Alex (он
активно правит `frontend/src/App.tsx` — календарь).

---

## Где мы сейчас

Идёт **RBAC-эпик** по плану `docs/роли/hr-roles-implementation-plan.md` (9 этапов).
- ✅ **Этап 1 — permission registry**: `apps/access/permissions_registry.py` (35 прав
  + field-code хелперы) + 12 тестов.
- ✅ **Этап 2 — RBAC модели + constraints + seed пустых ролей**:
  4 модели (migration `access/0002`), invariants (last-admin), admin,
  idempotent `seed_access_roles` (11 пустых system-ролей). 12 тестов.
- ✅ **Этап 3 — permission service + scope engine** (`apps/access/rbac.py`):
  `get_effective_roles/permissions`, `has_perm(user,code,level,employee)`,
  `employee_scope_queryset`, `field_access`. Computed-роли (self/all_people/
  manager/team_lead/admin) считаются по графу (ManagerAssignment BFS с защитой
  от циклов, Team/TeamMembership). Request-level cache. 14 тестов.
  Полный suite: 185 OK, 12 xfail.
- ✅ **Этап 0 — матрица УТВЕРЖДЕНА** (Alex, все 5 решений). Закодирована в
  `apps/access/role_matrix.py`, применяется `seed_access_role_permissions`
  (idempotent, 71 grant; засеяно в dev). Добавлены registry-коды self-fill
  (education/certificates/skills/dependents/emergency_contacts/notes).
- ✅ **Этап 4 (часть 1) — DRF enforcement, flag-gated**: `apps/access/drf.py`
  (`HasRBACPermission`, `RBACScopedViewSetMixin`, `assert_employee_in_scope`).
  Флаг `settings.RBAC_ENFORCE` (default **OFF = shadow**, поведение API не меняется;
  ON = deny + scoping). Подключено: employees child-ресурсы (documents/notes/
  emergency/dependents/education/certificates/skills — scope по employee_id),
  EmployeeViewSet (people.directory, каталог не ломается), skud (time.attendance +
  scope-guard на attendance APIViews). 7 enforcement-тестов (override RBAC_ENFORCE=True).
  Прод пуст -> shadow-период не нужен, флаг можно включить когда готовы.
- ✅ **Этап 6 — RBAC management API** (`/api/access/`): `apps/access/rbac_views.py`
  + `rbac_serializers.py` + `rbac_urls.py`. Эндпоинты: `roles/` (CRUD, system
  нельзя удалить, set-permissions action + audit), `assignments/` (CRUD +
  last-admin guard + audit), `audit/` (read-only), `permissions/` (каталог из
  registry), `effective-preview/` (превью людей по scope). Гейт `RolesAPIPermission`
  (всегда требует roles.view/manage — НЕ shadow-gated). 12 тестов.
- ✅ **Этап 5 (backend) — AuthStatus.access**: `/api/auth/status/` теперь отдаёт
  `access: {is_admin, roles, permissions, enforced}` для frontend-gating (не источник
  enforcement). 2 теста.
- **Дальше — Этап 7**: фронтенд `/settings/roles` (RolesSettingsView) + helper
  `can(code)` поверх AuthStatus.access. ⚠️ Frontend в активной работе Alex
  (App.tsx/client.ts/types/api.ts uncommitted) — координировать, чтобы не конфликтовать.
- **Отложено**: Этап 4 ч.2 — field-level serializer (компенсация — Alex: «полей
  компенсации пока нет, распишем потом»); enforcement leave/knowledge (leave —
  активная работа Alex).

> ⚠️ Тесты `apps.leave.tests.LeavePolicyAccrualTests` падают — это **WIP Alex** в
> `apps/leave/services.py` (`select_for_update()` на nullable outer join, Postgres
> «FOR UPDATE cannot be applied to the nullable side of an outer join»). НЕ связано
> с RBAC; apps/leave не трогался.

Перед этим закрыт первый спринт hardening (P0/P2/P11/P4) и сделан P1 step-1
(negative authz-тесты).

---

## Сделано (коммиты локальные, НЕ запушено)

| Тема | Что | Коммиты |
| --- | --- | --- |
| **P0** Production safety gate | Hard-fail при небезопасном prod-конфиге (`DEBUG`/fallback `SECRET_KEY`/`HR_PUBLIC_*`); `.env.example` размечен; runbook; 10 тестов | `38eaca1`, `ffb7e1b` |
| **P2** Private media | `/media/` за авторизацией через nginx X-Accel-Redirect (закрыт PII-leak; dev=FileResponse); 4 теста | `39de4ee` |
| **P11** CI gates | `ci.yml` (тесты на Postgres) + тест-гейт деплоя в `build.yml`; `test_filter_q` skip вне Postgres | `f895fd6` |
| **P4** HTML-санитайзер | nh3 allowlist на serializer-boundary (announcements/notes/knowledge); сохраняет галереи/`<video>`/YouTube-embed, режет script/on*/iframe/js:; 11 тестов; opt-in backfill-команда | `6991009` |
| **P1 step-1** Negative authz | `apps/employees/tests_authz.py`: 12 `@expectedFailure` тестов (профиль/документы/заметки/контакты/иждивенцы/leave/attendance) | `87fa087` |
| **RBAC Этап 1** Permission registry | `apps/access/permissions_registry.py` (35 прав, namespaces people/leave/time/knowledge/reports/settings/roles/integrations + field-code хелперы) + 12 тестов | `47e63d6` |
| **RBAC Этап 2** Модели + seed | `apps/access/models.py` (AccessRole/Permission/Assignment/Audit), `rbac_invariants.py`, `role_seeds.py`, `seed_access_roles`, admin, migration `access/0002` + 12 тестов | `b3a0ba5` |
| **RBAC Этап 3** Scope engine | `apps/access/rbac.py` (roles/permissions/has_perm/employee_scope_queryset/field_access; ManagerAssignment BFS, Team) + 14 тестов | (этот коммит) |
| docs | Отметки done в плане refactoring; session-state.md | `7df0350`, `929f3d7` |

Полный тест-сьют на Postgres: **148 OK, 12 expected failures**. CI зелёный.

---

## Ключевые файлы (новые/изменённые этой сессией)

- `config/safety.py` — `production_safety_problems()` (P0).
- `config/settings.py` — `ENVIRONMENT`/`IS_PRODUCTION`, fail-closed defaults, `HR_MEDIA_X_ACCEL`, hard guard в конце.
- `config/media.py` — `protected_media` view (auth-gate + X-Accel/FileResponse) (P2).
- `config/sanitize.py` — `sanitize_rich_html()` на nh3 (P4).
- `config/permissions.py` — `ConfiguredReadOnlyOrAuthenticated` (существующий coarse permission; будет заменён в RBAC Этап 4).
- `config/tests.py` — тесты P0/P2/P4 (safety gate, protected media, sanitizer).
- `apps/{announcements,employees,knowledge}/serializers.py` — `validate_body_html` → sanitizer.
- `apps/employees/management/commands/sanitize_stored_html.py` — backfill (`--dry-run`).
- `apps/employees/tests_authz.py` — negative PII authz (P1 step-1).
- `frontend/nginx.conf` — `/media/` → proxy на `web` + internal `/protected-media/`.
- `requirements.txt` — `nh3==0.3.6`.

---

## Документы (ссылки)

**RBAC (текущее направление):**
- `docs/роли/README.md` — обзор материалов по ролям.
- `docs/роли/hr-roles-implementation-plan.md` — **главный план RBAC, 9 этапов** с чеклистами и executor-промптами.
- `docs/роли/peopleforce-roles-research.md` — модель ролей PF, namespaces, scope types, 5 open questions.
- `docs/роли/agent-review-notes.md` — независимый review backend scope + security.
- `docs/роли/скриншоты/` — скриншоты PF (00–20).

**Hardening:**
- `docs/analysis/refactoring-and-structure-improvement-plan-2026-06-30.md` — план P0–P13 (P0/P2/P11/P4 = ✅).
- `docs/analysis/performance-security-code-quality-review-2026-06-30.md` — исходный review.
- `docs/production-deploy-runbook.md` — обязательные prod env + активация safety gate.

---

## Открытые решения / блокеры (нужен Alex)

**Draft матрицы готов:** `docs/роли/role-matrix-approved-draft.md` — рекомендованные
права по ролям + 5 спорных пунктов вынесены на решение Alex. Также там **registry-gap**:
нужно добавить коды для self-fill ресурсов (образование/сертификаты/навыки/иждивенцы/
экстренные контакты) до Этапа 4.

5 бизнес-вопросов из `peopleforce-roles-research.md` (Этап 0), гейтят Этап 4
(enforcement) — подробно в draft матрицы:
1. Менеджер видит attendance только подчинённых или всю компанию? (рекоменд.: только scope)
2. Кто утверждает системных admin/HR admin?
3. Кастомные роли на старте или только seed + редактирование permissions?
4. Импортировать текущих PF-admins вручную в первый релиз?
5. Какие поля компенсации есть/будут и кто видит по умолчанию?

---

## Pending деплой-действия (по команде Alex, после деплоя нового кода)

1. Активировать gate на проде: `ENVIRONMENT=production` в prod `.env` (прод уже
   безопасен: `DEBUG=False`, `HR_PUBLIC_*=False` — guard пройдёт).
2. Backfill HTML: `python manage.py sanitize_stored_html` (dry-run: 33 knowledge-дока
   изменятся; на Announcement/EmployeeNote — 0). Это изменение данных.
3. P4 frontend defense-in-depth (render-санитайзер заметок/объявлений) — не делался,
   backend boundary авторитетен; делать осторожно (Alex в App.tsx).

---

## Рабочее окружение (dev)

- Backend НЕ bind-mounted: правка → `docker cp <file> hr_vidnova-backend-1:/app/<file>` → при нужде restart.
- Тесты: `docker exec [-e DB_ENGINE=sqlite] hr_vidnova-backend-1 python manage.py test ...`
  (на sqlite `test_filter_q` skip; кириллический icontains case-insensitive только на Postgres).
- Полный прогон prod-like: без `DB_ENGINE` (→ Postgres `db`).
- sudo pass: 258456.

---

## Журнал

- 2026-06-30: P0/P2/P11/P4 + P1 negative tests сделаны и закоммичены локально.
  Alex подтвердил направление RBAC (`docs/роли/...`), выбрал старт с Этапа 1.
- 2026-06-30: RBAC **Этап 1 (permission registry) готов** — registry + 12 тестов,
  apps.access 43 OK. Правило: периодически обновлять этот файл (просьба Alex).
- 2026-06-30: RBAC **Этап 2 (модели + constraints + seed пустых ролей) готов** —
  4 модели + migration 0002, last-admin инвариант, idempotent seed (11 ролей),
  admin, 12 тестов.
- 2026-06-30: RBAC **Этап 3 (permission service + scope engine) готов** —
  apps/access/rbac.py + 14 тестов. Полный suite 185 OK, 12 xfail.
- 2026-06-30: добавлен **admin-bypass** (`rbac.is_admin`, суперроль = полный
  доступ). **Alex (Employee 76 «Кузьменко Олександр», user id=2) назначен admin
  в DEV** (AccessRoleAssignment, scope all_company; user также is_superuser).
  На ПРОДЕ RBAC ещё нет — там назначить отдельно после деплоя (Этап 8).
- 2026-06-30: оформлен **draft матрицы ролей**; Alex утвердил все 5 решений.
- 2026-06-30: **матрица засеяна** (role_matrix.py + seed_access_role_permissions,
  71 grant) + добавлены self-fill registry-коды.
- 2026-06-30: **Этап 4 часть 1 (DRF enforcement, flag-gated/shadow) готов** —
  apps/access/drf.py + подключение employees/skud + 7 enforcement-тестов.
  RBAC_ENFORCE default OFF. Alex: прод ещё не обслуживает людей -> не усложняем.
- 2026-06-30: **Этап 6 (RBAC management API) готов** — /api/access/ (roles/
  assignments/audit/permissions/effective-preview) + 12 тестов. Дальше Этап 7
  (фронт /settings/roles). Падения leave-тестов (3) — WIP Alex (не RBAC).
