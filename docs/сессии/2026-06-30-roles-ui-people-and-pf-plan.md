# 2026-06-30 — Roles UI: склад ролі Адміністратори + план PF-редактора

Исполнитель: Claude (Opus). Продолжение RBAC-эпика (после backend Этапов 0–6 и
Этапа 7 — страницы `/settings/roles`). Правило: коммиты локальные, push — по команде.

## Сделано (коммиты локальные)

| Тема | Что | Коммит |
|---|---|---|
| People-picker → таблица | Роль «Адміністратори»: вместо дропдауна — **таблиця складу** с аватарами; «+ Додати» открывает модалку с поиском; **kebab-меню рядка** (Деактивувати / Видалити). Унификация «Назад»/шапок настроек. | `8292b6e` (+ ранее `ea89cdf`) |
| Backend members API | `members` GET → `[{employee_id,is_active}]`; POST `{add:[…]}` additive; экшен **`member-action`** (remove/deactivate/activate) с guard последнего активного админа. Тесты 16 OK. | `8292b6e` |
| Фикс счётчика | `_members_payload` отдаёт авторитетный **`people_count`** (`rbac.role_people_count`, users+employees union); фронт берёт серверный count вместо локального employee-подсчёта. | `56904d4` |
| Фиксы верстки | Центрованная колонка тела редактора (`roles-editor-body`); фон модалки (`var(--card-hi)` = box-shadow, не цвет → `var(--panel)`) + тень; модалка **сверху с отступом** как типовые в системе; kebab **без рамки/фона** — только три точки. | `8292b6e` |

> Live-фикс по ходу: 404 на `roles/<id>/members/` — backend НЕ bind-mounted, процесс
> стартовал до `docker cp`. Лечится **restart backend** (тесты видят свежий код,
> live-процесс был стейл).

## План (PF-редактор ролей) — согласован, СТАРТ Фазы 1

Alex дал референс PF `/settings/roles/54297/edit` (роль «Усі люди»). Решения:
1. Реестр прав расширяем **до PF 1:1**.
2. Начинаем с вкладки **«Компанія»**; вкладка **«Люди»** (field-level) — отд. фаза.

Документы (gitignored, локально в `docs/роли/`):
- **`all-people-role-editor-plan.md`** — полный план (фазы 1–3, мапинг ~25 новых
  кодов, изменение API каталога на `categories→sections→permissions`).
- **`peopleforce-company-permissions-reference.md`** — снятая таксономия PF
  (6 категорий × секции × права, + структура вкладки «Люди»).

### Этапы Фазы 1 (чеклист) — ✅ ГОТОВО (коммит `f5f909c`)
- [x] B1. `section` в `Permission`/`_p`; разложены существующие + ~20 новых кодов PF.
- [x] B2. `PermissionCatalogView` → `categories→sections→permissions` (+`kind`/`on_level`).
- [x] F1. `api/access.ts` типы каталога + `permissionCatalog()`.
- [x] F2. Новый RoleEditor: вкладки Компанія|Люди, левая навигация категорий,
      секции, чекбоксы+описания, градуированные (Команди/Активи), sticky-футер.
- [x] F3. Вкладка «Люди» — плейсхолдер «у розробці».
- [x] M. `role_matrix.py` дефолты «Усі люди» по PF; re-seed (+4/-2).
- [x] V. tsc чисто; `apps.access` 102 OK; визуально сверено с PF (Загальні+HR);
      changelog 1.0.34.

> Тонкость реализации: `is_graded` теперь = «есть EDIT» (для UI kind); валидация
> уровня (models.clean / serializer) — по `perm.levels` (view-only хранит `view`).

### Фаза 2 — вкладка «Люди» (field-level) — ✅ ГОТОВО (коммит `d5019ad`)
- Backend: `roles/<id>/field-access/` (GET tabs→groups→fields/tables з рівнями;
  POST upsert/delete). Грант поля = `people.field.<tab>.field_<id>`/`table_<id>`
  через `AccessRolePermission` (`models.clean` пропускає динамічні field-коди).
  `rbac.field_access` — per-field грант пріоритетніший за tab-level. +1 тест (103 OK).
- Frontend: `PeopleFieldsTab` (ліва навігація вкладок профілю, акордеони
  `EmployeeFieldGroup`, поля/таблиці з сегментом). Спільний футер зберігає обидві
  вкладки. Візуально звірено з PF (Особисте розкрито — поля з Немає·Перегляд·Редагування,
  збереження «Збережено ✓» + reload).

### Фаза 3 — спец-контроли + dirty-guard — ✅ ГОТОВО (коммит `d9adc17`)
- «Звіти компанії» → мультиселект `reports.company.{headcount,turnover,tenure}`;
  «Розділи налаштувань» → `settings.section.{people_data,documents,forms,leave_types}`
  (atomic). `MULTISELECTS` + `company_catalog` віддає `sections[].multiselects`
  (опції — окремі коди, рендеряться одним дропдауном). `CompanyMultiselect` (фронт).
- Dirty-guard: `window.confirm` при Назад/Скасувати з незбереженими змінами
  (сигнатури grants+fieldLevels, скидаються після save). 103 тести OK, tsc чисто,
  візуально звірено з PF (Звіти/Налаштування дропдауни).

## Состояние

- Прод не трогали. RBAC дремлет (`RBAC_ENFORCE` off). Локально ~16 коммитов впереди
  `origin/main`.
- **Фазы 1–3 закрыты** — редактор ролі повністю повторює PeopleForce (вкладки
  Компанія+Люди, мультиселекти, dirty-guard).
- Открытое: enforcement (когда включать `RBAC_ENFORCE`), деплой на прод (seed ролей/
  прав + назначить admins), Этап 4ч2 field-level serializer-скрытие.
