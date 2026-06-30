# План рефакторинга и улучшения структуры

Дата: 2026-06-30  
Основание: `docs/analysis/performance-security-code-quality-review-2026-06-30.md`  
Цель: безопасно довести HR Vidnova до production-ready состояния для HR/PII данных и снизить стоимость дальнейшей разработки.

## Общие правила исполнения

- Работать маленькими PR/patch batches. Один пункт плана = отдельный scope, если явно не указано иначе.
- Перед изменениями всегда проверять `git status --short` и не откатывать чужие изменения.
- Не коммитить secrets, `.env`, cookies, tokens, реальные PII dumps.
- Для каждого пункта добавлять tests или явную проверку, соответствующую риску.
- Backend: сначала negative authorization/security tests, потом реализация.
- Frontend: сначала typed API boundary и error states, потом перенос компонентов.
- Production changes: без auto-deploy до зеленого CI и ручного подтверждения env.

## P0. Production Safety Gate

Priority: Critical  
Owner: backend/devops  
Impact: блокирует accidental public HR API и debug leaks.

Checklist:

- [ ] Ввести `ENVIRONMENT` или `DJANGO_ENV` с явным `production`.
- [ ] Сделать production defaults fail-closed: `DEBUG=False`, public API flags false, secure cookies true при HTTPS.
- [ ] Добавить Django system check/startup validation: production не стартует при fallback `SECRET_KEY`, `DEBUG=True`, `HR_PUBLIC_READ_API=True`, `HR_PUBLIC_WRITE_API=True`.
- [ ] Разделить `.env.example` на dev/prod template или явно пометить dev-only строки.
- [ ] Добавить smoke test: anonymous request к HR API получает 401/403 в production-like settings.
- [ ] Обновить deploy runbook: список обязательных env без значений secrets.

Acceptance criteria:

- [ ] `python3 manage.py check --deploy` не показывает critical deploy blockers для production profile.
- [ ] Production-like settings fail fast при небезопасном env.
- [ ] Anonymous write в `/api/employees/employees/` и `/api/knowledge/documents/` невозможен.
- [ ] `.env.example` больше не выглядит как production-ready файл с `DEBUG=1` и public write.

Executor prompt:

```text
Ты работаешь в /home/serv/hr_vidnova. Реализуй production safety gate для Django settings. Сначала прочитай config/settings.py, config/permissions.py, .env.example, docker-compose.prod*.yml и docs/development.md. Не трогай чужие изменения. Добавь production env marker, fail-closed defaults и system check/startup validation, который запрещает DEBUG, fallback SECRET_KEY и HR_PUBLIC_* в production. Обнови env examples/runbook без secrets. Добавь tests/smoke checks на anonymous 401/403. Проверь: python3 manage.py check, python3 manage.py check --deploy с production-like env, и релевантные backend tests.
```

## P1. RBAC и object-level permissions

Priority: Critical  
Owner: backend  
Impact: закрывает доступ обычных сотрудников к чужим HR/PII данным.

Checklist:

- [ ] Описать role matrix: HR admin, HR manager, manager, employee, compensation/documents roles.
- [ ] Добавить role source: Django groups/permissions или `apps.access` profile policy.
- [ ] Разделить admin HR endpoints и self-service endpoints.
- [ ] Для `EmployeeApiViewSet`, child records, documents, leave, SKUD добавить scoped querysets.
- [ ] Добавить object-level checks для documents/notes/emergency/dependents/attendance.
- [ ] Добавить negative API tests на каждую PII категорию.

Acceptance criteria:

- [ ] Employee может читать/редактировать только self-service разрешенные поля.
- [ ] Manager видит только подчиненных и только разрешенные поля.
- [ ] HR/admin endpoints требуют HR role.
- [ ] Tests покрывают forbidden для чужих documents, notes, emergency contacts, dependents, attendance, leave.
- [ ] Frontend получает 403 и показывает нормальное forbidden state.

Executor prompt:

```text
Ты реализуешь RBAC/object scoping в /home/serv/hr_vidnova. Начни с docs/employee-profile-plan.md, config/permissions.py, apps/access/services.py, apps/employees/views.py, apps/selfservice/views.py, apps/skud/views.py, apps/leave/views.py. Сначала добавь failing negative API tests: обычный employee не может читать/менять чужие документы/контакты/заметки/посещаемость. Затем введи permission classes и scoped queryset helpers. Не полагайся на скрытые кнопки frontend. Проверь sqlite tests для access/employees/skud/leave и python3 manage.py check.
```

## P2. Private Media Architecture

Priority: High  
Owner: backend/devops  
Impact: закрывает утечку HR documents через прямые `/media/` URL.

Checklist:

- [ ] Разделить public media и private document storage paths.
- [ ] Убрать direct `file_url` для private employee documents из serializers.
- [ ] Сделать authenticated download/preview endpoints с RBAC/object scope.
- [ ] В nginx добавить private/internal location или временно отдавать private files через Django stream.
- [ ] Добавить cache headers: private/no-store для PII documents.
- [ ] Добавить tests: anonymous direct URL не получает private doc, unauthorized employee получает 403.

Acceptance criteria:

- [ ] `/media/peopleforce_employee_documents/...` не отдает private документы публично.
- [ ] Документ доступен только через endpoint с auth и permission.
- [ ] Serializer не раскрывает raw private storage URL.
- [ ] Existing public assets/avatars продолжают работать.

Executor prompt:

```text
Реализуй private media для employee documents. Прочитай apps/employees/models.py, serializers.py, views.py, frontend/nginx.conf, docker-compose.prod.ghcr.yml. Сохрани public media для аватаров/баннеров, но employee documents переведи на private download/preview flow. Не ломай импортированные PeopleForce documents. Добавь tests для anonymous/unauthorized/authorized download. Проверь nginx config синтаксически, backend tests и ручной smoke через API.
```

## P3. Upload Policy и безопасный preview

Priority: High  
Owner: backend/frontend  
Impact: снижает malware/storage/active-content risk.

Checklist:

- [ ] Определить allowlist типов HR документов.
- [ ] Добавить extension + MIME + magic-byte validation.
- [ ] Уменьшить default upload limits, вынести большие файлы в отдельный async flow.
- [ ] Preview разрешить только safe formats; risky text/code отдавать download attachment.
- [ ] Для media upload knowledge/announcements проверить размеры и типы независимо от frontend.
- [ ] Добавить tests на запрещенные SVG/HTML/JS/PHP и oversized files.

Acceptance criteria:

- [ ] Нельзя загрузить `.html`, `.svg`, `.js`, `.php` как previewable HR document.
- [ ] Oversized batch не забивает request path.
- [ ] Preview не исполняет active content.
- [ ] Пользователь получает понятную ошибку upload validation.

Executor prompt:

```text
Ужесточи upload/preview policy. Начни с apps/employees/views.py, apps/knowledge/views.py, apps/announcements/views.py и frontend upload components. Добавь backend allowlist и tests до реализации. Для HR documents запрети active formats и inline preview небезопасных типов. Не меняй публичный UX больше необходимого: ошибки должны быть понятными. Проверь backend tests и npm build.
```

## P4. HTML Sanitization, URL Policy, CSP

Priority: High  
Owner: backend/frontend/devops  
Impact: закрывает stored XSS.

Checklist:

- [ ] Выбрать sanitizer: backend allowlist (`bleach` или другой поддерживаемый sanitizer) + frontend defense-in-depth.
- [ ] Централизовать sanitizer для `Announcement.body_html`, `EmployeeNote.body_html`, `KnowledgeDocument.body_html/body`.
- [ ] Добавить shared frontend `safeExternalUrl()` для links/images/video sources.
- [ ] Убрать scattered raw HTML transforms или пропустить их через sanitizer boundary.
- [ ] Добавить CSP headers в nginx/edge, сначала report-only если политика ломает текущий UI.
- [ ] Tests: script/event/style/SVG/iframe/javascript URLs stripped.

Acceptance criteria:

- [ ] Все `dangerouslySetInnerHTML` call sites имеют documented sanitized source.
- [ ] Backend stores sanitized HTML, not raw hostile HTML.
- [ ] `javascript:` and active data URLs render inert or are removed.
- [ ] CSP присутствует в response headers для SPA/API shell.

Executor prompt:

```text
Закрой stored-XSS boundary. Прочитай frontend/src/App.tsx sanitizer sections, RichTextEditor.tsx, CreateAnnouncementModal.tsx, apps/announcements/serializers.py, apps/employees/serializers.py, apps/knowledge/serializers.py, frontend/nginx.conf. Сначала добавь backend tests с вредными HTML payloads. Затем внедри общий sanitizer и URL allowlist. Не полагайся только на frontend. Добавь CSP headers осторожно, если нужно report-only. Проверь tests и npm build.
```

## P5. Integration Hardening: Webhook, Logs, Outbound Fetch

Priority: High  
Owner: backend  
Impact: снижает SSRF, credential leakage, PII-overlogging, webhook DoS.

Checklist:

- [ ] PeopleForce webhook в production fail-closed: secret required, invalid signature 401/403.
- [ ] Redact integration headers and payloads before persistence.
- [ ] Добавить retention cleanup для `PeopleForceCompatRequest`, webhook events, import issues raw payloads.
- [ ] Harden PeopleForce attachment downloads: exact host allowlist, credential only for allowed host, redirect policy, private IP block.
- [ ] Stream downloads with max bytes.
- [ ] Tests на malicious attachment URL, redirect, invalid webhook signature, redaction.

Acceptance criteria:

- [ ] Unsigned webhook in production не запускает sync.
- [ ] Logs не содержат auth-like headers и лишний PII payload.
- [ ] PeopleForce credentials не отправляются на чужой host.
- [ ] Old raw logs удаляются или агрегируются по retention policy.

Executor prompt:

```text
Ужесточи integrations. Изучи apps/integrations/webhook_views.py, peopleforce_compat.py, models.py, apps/knowledge/peopleforce_attachments.py, apps/integrations/peopleforce/importer.py. Реализуй fail-closed webhook для production, redaction, retention cleanup и outbound URL allowlist. Начни с tests: invalid signature, malicious rich_text attachment host, redirect на чужой/private host, headers redacted. Проверь backend tests и manage.py check.
```

## P6. Auth and Rate Limit Hardening

Priority: Medium/High  
Owner: backend/devops  
Impact: снижает brute-force и spoofing risks.

Checklist:

- [ ] Отключить global BasicAuthentication в production.
- [ ] Настроить trusted proxy parsing: не доверять user-supplied XFF.
- [ ] На nginx/edge strip inbound XFF и выставлять controlled headers.
- [ ] Добавить verify-code rate limit по phone, employee/user, real IP.
- [ ] Добавить audit tests, что spoofed XFF не меняет rate-limit identity.

Acceptance criteria:

- [ ] Production DRF не принимает BasicAuth глобально.
- [ ] Request-code и verify-code имеют Redis-backed throttling.
- [ ] Spoofed XFF не обходит лимит.
- [ ] Audit IP соответствует trusted proxy policy.

Executor prompt:

```text
Ужесточи auth/rate limit. Прочитай config/settings.py, config/urls.py, apps/access/views.py, frontend/nginx.conf. Отключи BasicAuthentication для production, исправь client IP extraction через trusted proxy policy, добавь verify-code throttling. Tests должны доказывать, что X-Forwarded-For от клиента не обходит limit. Проверь apps.access tests и manage.py check.
```

## P7. Attendance and Reports Performance Pass

Priority: Medium/High  
Owner: backend/database  
Impact: стабилизирует SKUD/reports под рост данных.

Checklist:

- [ ] Добавить validation/cap date ranges для company attendance и reports.
- [ ] Перенести headcount/turnover/tenure calculations в DB aggregates или materialized summaries.
- [ ] Заменить `started_at__date` filters на bounded datetime ranges.
- [ ] Добавить indexes: `AttendancePeriod(employee,date,start_at)`, `TimeEntry(employee,started_at)`, `TimeEntry(project,started_at)`.
- [ ] Добавить query-count/performance tests на типовые ranges.
- [ ] Снять EXPLAIN на production-like Postgres dataset.

Acceptance criteria:

- [ ] Requests с чрезмерным range получают 400 или capped range.
- [ ] Hot endpoints не грузят все employees/history без необходимости.
- [ ] EXPLAIN показывает index usage для ключевых filters.
- [ ] P95 latency target documented for company attendance/reports.

Executor prompt:

```text
Сделай performance pass для attendance/reports. Читай apps/skud/views.py, apps/skud/models.py, apps/dashboard/views.py, apps/projects/views.py, apps/projects/models.py. Сначала добавь bounds validation и tests. Затем оптимизируй aggregates и datetime filters, добавь migrations с indexes. Для Postgres сними EXPLAIN на representative queries. Проверь backend tests и миграции dry-run.
```

## P8. PeopleForce Import Batching and Resumability

Priority: Medium/High  
Owner: backend/integrations  
Impact: снижает long transaction risk и rollback amplification.

Checklist:

- [ ] Убрать global transaction вокруг full `_run`.
- [ ] Разделить fetch/cache, mapping, write batches.
- [ ] Добавить checkpoints per entity/date page.
- [ ] Downloads вынести в отдельные Celery jobs.
- [ ] Сделать retry/idempotency per batch.
- [ ] Добавить observability: counters, duration, failed batch metadata.

Acceptance criteria:

- [ ] Full import не держит одну DB transaction на весь sync.
- [ ] Failed batch не откатывает уже успешно записанные независимые batches.
- [ ] Import можно безопасно resume/retry.
- [ ] Timesheet/document import progress виден в `PeopleForceImportRun`.

Executor prompt:

```text
Рефактор PeopleForce import batching. Изучи apps/integrations/peopleforce/importer.py, tasks.py, models.py и management commands. Не меняй mapping semantics без tests. Убери global atomic, введи батчи и checkpoints, downloads вынеси отдельно. Добавь tests на idempotent retry и partial failure. Проверь manage.py check и релевантные integration tests.
```

## P9. Frontend API Client Consolidation and Mutation UX

Priority: Medium  
Owner: frontend  
Impact: единый CSRF/error/auth handling и честный UX.

Checklist:

- [ ] Экспортировать shared request/query/mutation helpers из `frontend/src/api/client.ts`.
- [ ] Убрать protected raw `fetch` из settings, reports, App field-groups.
- [ ] Добавить typed API functions для оставшихся endpoints.
- [ ] Исправить optimistic fallback: failed mutations не создают "submitted" локально.
- [ ] Добавить visible error states для leave/time correction/comment/reaction/vote.
- [ ] Добавить lightweight frontend tests или at least build + manual smoke checklist.

Acceptance criteria:

- [ ] `rg "fetch\\(" frontend/src` показывает только allowed locations.
- [ ] Все state-changing requests идут с CSRF через shared client.
- [ ] Пользователь не видит ложный успех при backend error.
- [ ] `npm run build` зеленый.

Executor prompt:

```text
Консолидируй frontend API client. Прочитай frontend/src/api/client.ts, PeopleDataSettingsView.tsx, reports/shared.tsx, App.tsx места с fetch. Переведи protected calls на shared client, добавь typed methods. Исправь mutation error UX: никаких локальных submitted records после catch. Не меняй дизайн шире scope. Проверь rg fetch, npm run build, и ручной smoke критичных форм.
```

## P10. Frontend Decomposition and Bundle Budget

Priority: Medium  
Owner: frontend  
Impact: ускоряет cold start и снижает regression risk.

Checklist:

- [ ] Разбить `App.tsx` на feature modules: people, knowledge, attendance, leave, announcements, settings, reports, projects.
- [ ] Вынести shared hooks/utils/components.
- [ ] Lazy-load heavy routes: TipTap editor, Recharts reports, org graph.
- [ ] Разбить `index.css` по feature/component CSS или CSS modules pattern, сохранив tokens.
- [ ] Добавить bundle budget check в CI.
- [ ] Удалить tracked backup CSS после подтверждения.

Acceptance criteria:

- [ ] Нет top-level feature файла > 2,000 LOC без отдельного обоснования.
- [ ] Main JS chunk существенно меньше текущих 2.0 MB minified; target зафиксировать в CI.
- [ ] Lazy routes не ломают routing/auth redirects.
- [ ] `npm run build` зеленый, visual smoke desktop/mobile пройден.

Executor prompt:

```text
Разбей frontend монолит без изменения поведения. Начни с инвентаризации frontend/src/App.tsx imports/routes/state и frontend/src/styles/index.css. Выделяй по одному domain route за PR, используй React.lazy для heavy modules. Не переписывай дизайн. После каждого шага npm run build и smoke routing. В конце добавь bundle budget check и документируй новые boundaries.
```

## P11. CI, Tests, Dependency Hygiene

Priority: High  
Owner: devops/backend/frontend  
Impact: блокирует broken builds и устаревшие dependencies.

Checklist:

- [ ] В GitHub Actions добавить backend job: install deps, `manage.py check`, `makemigrations --check --dry-run`, tests.
- [ ] В frontend job: `npm ci --legacy-peer-deps`, `npm run build`.
- [ ] Исправить текущий failing test `apps.projects.tests.ProjectApiTests.test_filter_q`.
- [ ] Добавить dependency audit scheduled/manual: `pip-audit`, `npm audit` или Dependabot/Renovate.
- [ ] Спланировать upgrade Django 4.2 -> supported LTS 5.2.
- [ ] Перестать auto-deploy только по `latest`; использовать SHA tag promotion.

Acceptance criteria:

- [ ] Failed backend/frontend checks не публикуют GHCR images.
- [ ] Migration drift ловится в CI.
- [ ] Tests зеленые.
- [ ] Django на поддерживаемой ветке или есть утвержденный upgrade PR/roadmap.
- [ ] Deploy использует immutable image tag.

Executor prompt:

```text
Укрепи CI/dependency hygiene. Прочитай .github/workflows/build.yml, requirements.txt, frontend/package.json, docker-compose.prod.ghcr.yml. Добавь quality gates перед publish, исправь failing ProjectApiTests.test_filter_q, добавь migration check. Затем подготовь отдельный plan/PR для Django 5.2 upgrade с compatibility fixes. Не меняй deployment без явного подтверждения. Проверь workflow локально насколько возможно.
```

## P12. Docs and Artifact Hygiene

Priority: Medium  
Owner: backend/frontend/docs  
Impact: снижает onboarding drift и accidental commits.

Checklist:

- [ ] Обновить README/development: migrations уже committed, quickstart должен использовать `migrate`.
- [ ] Создать sanitized tracked production runbook вне ignored PII docs.
- [ ] Удалить или объяснить tracked `frontend/src/styles/index.css.bak-2026-06-25`.
- [ ] Документировать module boundaries после frontend/backend split.
- [ ] Добавить "what not to commit" checklist.

Acceptance criteria:

- [ ] Новый разработчик поднимает проект по docs без `makemigrations`.
- [ ] Production rollback/deploy runbook версионируется без secrets/PII.
- [ ] `git ls-files` не содержит backup/build/cache artifacts без причины.

Executor prompt:

```text
Наведи порядок в docs/artifacts. Прочитай README.md, docs/development.md, .gitignore, docs/sessions.md и текущие ignored docs. Обнови quickstart под committed migrations, создай sanitized production runbook без secrets/PII, убери или документируй tracked backup CSS. Не трогай реальные PII материалы. Проверь, что git status содержит только ожидаемые doc/artifact изменения.
```

## Suggested Execution Order

1. P0 Production Safety Gate.
2. P11 CI/tests/dependency gates, включая failing test.
3. P1 RBAC/object permissions.
4. P2 Private media.
5. P4 HTML sanitization/CSP.
6. P5 Integration hardening.
7. P6 Auth/rate-limit.
8. P7 Performance.
9. P8 Import batching.
10. P9 API client/mutation UX.
11. P10 Frontend decomposition.
12. P12 Docs/artifact hygiene.

