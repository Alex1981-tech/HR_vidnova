# 2026-06-30 — Security hardening + RBAC backend

Исполнитель: Claude (Opus). Параллельно Alex вёл `apps/leave` + frontend (не трогал).
Правило: коммиты локальные, **без push** без команды. Живой контекст: `docs/session-state.md`.

## Итог

Закрыт первый спринт hardening (P0/P2/P11/P4 + P1 negative tests) и реализован
**весь backend RBAC** (Этапы 0–6 по `docs/роли/hr-roles-implementation-plan.md`,
кроме отложенного 4ч2 field-level). Полный suite зелёный (падают только leave-тесты
— WIP Alex). Ничего не запушено.

## Hardening (план `docs/analysis/refactoring-...-2026-06-30.md`)

| P | Что | Коммиты |
|---|---|---|
| P0 | Production safety gate (fail-closed + startup guard, `.env.example`, runbook) | `38eaca1`, `ffb7e1b` |
| P2 | Приватная media через nginx X-Accel-Redirect (закрыт анонимный доступ к `/media/`) | `39de4ee` |
| P11 | CI на Postgres + тест-гейт деплоя; skip Cyrillic-icontains теста на SQLite | `f895fd6` |
| P4 | nh3 HTML-санитайзер на serializer-boundary (announcements/notes/knowledge) | `6991009` |
| P1.1 | Negative authz-тесты (12 @expectedFailure) | `87fa087` |

## RBAC backend

| Этап | Что | Коммит |
|---|---|---|
| 0 | Матрица прав (5 решений Alex) + self-fill registry-коды | `e4e51af` |
| 1 | Permission registry (`permissions_registry.py`, 41 код) | `47e63d6` |
| 2 | Модели AccessRole/Permission/Assignment/Audit + constraints + seed (migration `access/0002`) | `b3a0ba5` |
| 3 | Scope engine (`rbac.py`: has_perm/employee_scope_queryset/field_access; ManagerAssignment BFS, Team) | `cd1218b` |
| admin | admin = full-access bypass; **Alex (user id=2) admin в dev** | `1d182e1` |
| 4ч1 | DRF enforcement flag-gated (`drf.py`, `RBAC_ENFORCE` default OFF=shadow); employees+skud | `c56cfa5` |
| 6 | Management API `/api/access/` (roles/assignments/audit/permissions/effective-preview) | `0720e50` |
| 5be | AuthStatus.access (roles/permissions/is_admin/enforced) | `8e845ab` |

### Утверждённая матрица (Alex)
1. Manager attendance — только scope подчинённых (не company-wide).
2. Admins назначают только admin'ы (`roles.manage` — admin-only через bypass).
3. На старте только 11 system-ролей + редактирование прав (кастомные позже).
4. Без авто-импорта PF-admins.
5. Компенсация: admin/hr_admin edit, hr_specialist view, остальные none
   (полей компенсации пока нет — распишем потом).

Матрица: `apps/access/role_matrix.py`, применяется `seed_access_role_permissions`
(idempotent, 71 grant; засеяно в dev).

## Ключевые решения / заметки
- Прод **ещё не обслуживает людей** → не строим shadow-машинерию Этапа 8; флаг
  `RBAC_ENFORCE` включаем по готовности. Default OFF — поведение API не меняется.
- RBAC management API (`/api/access/`) **всегда** требует roles.view/manage
  (не shadow-gated) — управление ролями не оставляем открытым.
- EmployeeViewSet гейтится на `people.directory` (каталог не ломается); field-level
  скрытие профиля (компенсация/PII) — отдельный шаг (4ч2), отложено.

## Открытые хвосты
- **Этап 7** — фронт `/settings/roles` (Alex стэшит frontend → строю чисто).
- Этап 4ч2 — field-level serializer (когда появятся поля компенсации).
- Enforcement leave/knowledge (leave — активная работа Alex).
- Перед `RBAC_ENFORCE=1`: помнить, что профиль ещё отдаёт все поля.
- Прод: RBAC не задеплоен; после деплоя — seed ролей/прав + назначить admins.
- **leave-тесты падают** — WIP Alex (`apps/leave/services.py`: `select_for_update()`
  на nullable outer join → Postgres «FOR UPDATE cannot be applied to the nullable
  side of an outer join»). Не RBAC.
