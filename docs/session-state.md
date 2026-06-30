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
- **Дальше — Этап 4** (DRF enforcement: HasHRPermission/ScopedEmployeeQuerysetMixin/
  FieldLevelEmployeeSerializerMixin; заменить ConfiguredReadOnlyOrAuthenticated на
  чувствительных API). ⚠️ Зависит от матрицы (какие права у каких ролей) — Этап 0,
  5 open questions Alex (ниже). Без grants движок работает, но никто ничего не видит.

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

5 бизнес-вопросов из `peopleforce-roles-research.md` (Этап 0), гейтят Этап 2 (seed)
и Этап 4 (enforcement), но **не** Этап 1:
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
  apps/access/rbac.py + 14 тестов. Полный suite 185 OK, 12 xfail. Дальше Этап 4
  (DRF enforcement) — упирается в матрицу (Этап 0, 5 open questions Alex).
