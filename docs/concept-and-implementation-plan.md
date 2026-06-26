# HR Vidnova: концепция и план реализации

Дата: 2026-06-24  
Домен: `hr.vidnova.app`  
Папка проекта: `/home/serv/hr_vidnova`  
Статус: черновик концепции перед разработкой

## 1. Суть продукта

HR Vidnova — простая внутренняя система для клиники:

- учет сотрудников и их структуры подчинения;
- отображение рабочего времени;
- заявки на отпуск от сотрудника своему руководителю;
- база знаний для документов, регламентов и инструкций;
- наглядный граф подчинения;
- импорт сотрудников из БАФ/Fotopacients;
- будущая интеграция со СКУД в клиниках.

Это не payroll, не бухгалтерия и не полный кадровый документооборот. В MVP важно
быстро закрыть ежедневные операционные вопросы: кто работает, кто отсутствует,
кто кому подчиняется, где найти документ, какие заявки ждут решения.

## 2. Основные роли

Подробная модель ролей, scope-aware доступ и правила legacy-импорта из
PeopleForce описаны в `docs/roles-and-legacy-data-import.md`. Важно: `Employee`
и Django `User` остаются разными сущностями; роль пользователя определяет доступ,
а подчинение/клиника/департамент ограничивают scope.

### Сотрудник

- видит свой профиль;
- видит свои рабочие дни/отметки;
- создает заявку на отпуск;
- видит статус своих заявок;
- читает базу знаний.

### Руководитель

- видит своих подчиненных;
- видит табель/исключения по команде;
- согласует или отклоняет заявки на отпуск;
- видит граф подчинения своего подразделения.

### HR / Администратор

- управляет сотрудниками, подразделениями, должностями;
- запускает и проверяет импорт из БАФ;
- настраивает руководителей и оргструктуру;
- корректирует рабочее время вручную;
- публикует документы базы знаний;
- видит аудит изменений.

### Директор / Owner

- видит всю структуру;
- видит сводки по клиникам/подразделениям;
- может быть финальным согласующим по отдельным типам отпусков.

## 3. MVP scope

### Включить в первую версию

1. Авторизация и роли.
2. Справочник сотрудников.
3. Профиль сотрудника.
4. Оргструктура и руководители.
5. Граф подчинения.
6. Табель рабочего времени в ручном/импортированном режиме.
7. Сырые события СКУД как будущий слой интеграции.
8. Заявки на отпуск: создать, согласовать, отклонить, отменить.
9. База знаний: категории, документы, поиск, вложения, права просмотра.
10. Админ-раздел импорта сотрудников из БАФ/Fotopacients.
11. Audit log для важных действий.

### Не включать в MVP

- расчет зарплаты;
- сложные графики сменности с payroll-правилами;
- электронную подпись документов;
- полноценный кадровый документооборот;
- интеграцию с внешними календарями;
- мобильное push-приложение.

## 4. UX-концепция

Интерфейс должен структурно опираться на референсные скриншоты из
`docs/фото/`: Vidnova/PeopleForce-like HR workspace, а не маркетинговую
страницу и не набор разрозненных карточек. Подробный UI-контракт вынесен в
`docs/ui-reference-structure.md`.

### App shell

На desktop всегда видна рабочая оболочка:

- фиксированный левый sidebar с логотипом, глобальным поиском, основными
  разделами и настройками снизу;
- верхняя action bar с быстрым добавлением, уведомлениями и профилем;
- основной экран без декоративной внешней карточки;
- табы, фильтры и переключатели вида внутри конкретного раздела.

Основные разделы sidebar:

- Домашняя страница;
- Сповіщення;
- Люди;
- Календарь;
- Присутності;
- Запити;
- Документи;
- База знань;
- Звіти.

### Первый экран после входа

Не landing page. Сразу домашняя рабочая страница:

- брендированный баннер Vidnova;
- приветствие сотрудника;
- быстрые действия: запрос выходного/отпуска, учет времени, объявление/опрос;
- центральная колонка: задачи и лента объявлений;
- правая колонка: остаток отпусков, события недели, кто отсутствует, ссылки.

### Рабочие паттерны

- `Люди`: табы `Люди / Команди / Організаційна структура`, плотная таблица,
  поиск на всю ширину, фильтры, pagination, hover/detail карточка сотрудника.
- `Календарь`: матрица сотрудников по строкам и дней месяца по колонкам,
  отпуск/отсутствие как горизонтальная полоса внутри строки.
- `Присутності`: профильный календарь сотрудника с KPI за месяц и day cells
  план/факт/дельта.
- `База знань`: дополнительный левый sidebar категорий, поиск и grid
  категорий/документов со счетчиками.
- `Організаційна структура`: большой canvas на всю рабочую область, карточки
  сотрудников в дереве, zoom/fit/fullscreen controls.

### Mobile/touch

- sidebar скрывается;
- основные разделы доступны через нижнюю навигацию;
- touch targets минимум 44-48 px;
- таблицы заменяются карточными списками;
- календарь и оргграф получают горизонтальный scroll, zoom/pan или list fallback;
- фильтры открываются как компактная панель.

## 5. Предлагаемый стек

С учетом текущей инфраструктуры FotoPacients логично не усложнять:

- Backend: Django 4.2 + DRF.
- DB: PostgreSQL 16.
- Queue: Celery + Redis.
- Frontend: React + Vite + TypeScript.
- Styling: Tailwind CSS + CSS tokens, близко к FotoPacients.
- Icons: `lucide-react`.
- File storage для базы знаний: MinIO/S3-compatible или локальный volume на старте.
- Reverse proxy: Nginx/Caddy/Traefik на `hr.vidnova.app`.

Trade-off: можно было бы сделать проще на чистом Django templates, но touch-first
UI, граф подчинения и интерактивный табель удобнее и быстрее развивать на React.

## 6. Высокоуровневая архитектура

```text
Browser / touch device
        |
        | HTTPS hr.vidnova.app
        v
Reverse proxy
        |
        +--> Frontend static files
        |
        +--> /api/*  Django DRF
                    |
                    +--> PostgreSQL
                    +--> Redis
                    +--> Celery workers
                    +--> File storage
                    |
                    +--> BAF/Fotopacients import adapter
                    +--> SKUD adapter
```

### Принцип интеграций

Ядро HR-системы не должно зависеть от конкретного формата БАФ или СКУД. Для
каждого источника нужен adapter, который приводит внешние данные к внутренним
моделям:

- `EmployeeSourceRecord` для сотрудников;
- `AccessEvent` для СКУД;
- `ImportRun` и `ImportError` для диагностики.

FotoPacients используется как read-only runtime source для текущего списка
сотрудников из `accounts_user`: это весь staff, не только врачи. Для врачей
дополнительно подтягиваются медицинские специализации из
`patients_doctor.specialties` и fallback-поля `accounts_user.specialty`.

PeopleForce используется как legacy source для первичного read-only импорта
базы знаний, должностей, департаментов, подчинения и недостающих employee fields.
После cutover PeopleForce не должен быть обязательной runtime-зависимостью.

## 7. Основные доменные модели

### Организация

- `Clinic`: клиника/локация.
- `Department`: подразделение.
- `Position`: должность.
- `MedicalSpecialty`: медицинская специализация врача из FotoPacients.
- `Employee`: сотрудник.
- `Employment`: состояние занятости сотрудника, дата приема/увольнения.
- `ManagerAssignment`: кто кому подчиняется, с датами действия.
- `OrgUnitMembership`: сотрудник в подразделении/клинике.

### БАФ/Fotopacients import

- FotoPacients staff sync:
  - source table: `accounts_user`;
  - department source: `accounts_user_departments`;
  - doctor specialty source: `patients_doctor_specialties`;
  - command: `python manage.py sync_fotopacients_employees --dry-run`.
- `ExternalEmployeeLink`:
  - `source`: `baf`, `fotopacients`, позже другие;
  - `external_id`;
  - `employee`;
  - `last_seen_at`;
  - `raw_hash`.
- `EmployeeImportRun`:
  - source, status, started_at, finished_at, counters.
- `EmployeeImportIssue`:
  - run, severity, external_id, message, raw_fragment.

Правило: внешняя система обновляет базовые поля, HR Vidnova хранит локальные
настройки поверх них: руководитель, права, график, доступ к базе знаний.

### Рабочее время

- `WorkSchedule`: плановый график сотрудника.
- `WorkCalendarDay`: рабочий/выходной/праздник.
- `AccessDevice`: устройство СКУД.
- `AccessEvent`: сырое событие вход/выход, immutable.
- `WorkDaySummary`: рассчитанный день сотрудника.
- `TimeAdjustment`: ручная корректировка HR/руководителем.
- `AttendanceException`: опоздание, ранний уход, отсутствие, нет выхода.

Принцип: сырые события СКУД не редактировать. Все исправления делать отдельными
корректировками с audit log.

### Отпуска

- `LeaveType`: отпуск, больничный, за свой счет, обучение, другое.
- `LeaveRequest`:
  - employee, type, date_from, date_to, reason;
  - status: draft, submitted, approved, rejected, cancelled;
  - current_step.
- `LeaveApprovalStep`:
  - approver, role, order, status, decided_at, comment.
- `LeaveBalance` можно добавить позже, если нужны остатки дней.

Для MVP достаточно маршрута: сотрудник -> прямой руководитель -> HR optional.

### База знаний

- `KnowledgeCategory`;
- `KnowledgeDocument`;
- `KnowledgeDocumentVersion`;
- `KnowledgeAttachment`;
- `KnowledgeReadEvent` optional;
- `KnowledgePermission` по роли/клинике/подразделению.

Документы: PDF, DOCX, XLSX, изображения. В MVP лучше хранить файл, название,
описание, теги, версию, автора, дату публикации.

### Аудит и уведомления

- `AuditLog`: кто, что, когда, old/new summary.
- `Notification`: заявка на отпуск, решение, ошибка импорта, исключение рабочего
  времени.

## 8. API outline

### Auth

- `GET /api/auth/status/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/me/`

### Employees

- `GET /api/employees/`
- `POST /api/employees/`
- `GET /api/employees/{id}/`
- `PATCH /api/employees/{id}/`
- `GET /api/employees/{id}/subordinates/`
- `GET /api/org-chart/`

### Time

- `GET /api/time/my/?from=&to=`
- `GET /api/time/team/?from=&to=&department=&clinic=`
- `GET /api/time/exceptions/`
- `POST /api/time/adjustments/`
- `GET /api/skud/events/`
- `POST /api/skud/import-runs/`

### Leave

- `GET /api/leave/requests/`
- `POST /api/leave/requests/`
- `GET /api/leave/requests/{id}/`
- `POST /api/leave/requests/{id}/submit/`
- `POST /api/leave/requests/{id}/approve/`
- `POST /api/leave/requests/{id}/reject/`
- `POST /api/leave/requests/{id}/cancel/`

### Knowledge

- `GET /api/knowledge/categories/`
- `GET /api/knowledge/documents/`
- `POST /api/knowledge/documents/`
- `GET /api/knowledge/documents/{id}/`
- `POST /api/knowledge/documents/{id}/versions/`
- `GET /api/knowledge/search/?q=`

### Integrations

- `POST /api/integrations/baf/import/`
- `GET /api/integrations/baf/import-runs/`
- `GET /api/integrations/baf/import-runs/{id}/`
- `POST /api/integrations/skud/import/`

## 9. Экранная структура

Маршруты могут быть реализованы через client-side routing позже. В MVP UI уже
должен повторять структуру этих экранов даже при переключении state внутри
одной React entrypoint.

### `/`

Домашняя страница:

- branded banner;
- приветствие и быстрые действия;
- задачи и объявления в центральной колонке;
- справа отпуск, события недели, отсутствующие, ссылки компании.

### `/people`

Люди:

- внутренние табы `Люди`, `Команди`, `Організаційна структура`;
- поиск по ФИО/email/телефону;
- фильтры и переключатель вида;
- таблица сотрудников с колонками: ФИО, должность, департамент, локация,
  менеджер, дата начала;
- hover/detail карточка сотрудника;
- действие `Новий найм`.

### `/people/:id`

Профиль сотрудника для HR/admin:

- брендированный баннер Vidnova;
- фото, ФИО, должность, локация;
- навигация предыдущий/следующий сотрудник;
- меню `Дії`;
- вкладки: `Особисте`, `Робота`, `Компенсація`, `Відсутності`, `Time`,
  `Документи`, `Більше`;
- слева редактируемые секции;
- справа summary карточка с email, телефоном, датой начала, типом работы,
  должностью, департаментом, подразделением, локацией, стажем и менеджером;
- пустые поля остаются пустыми до импорта, без demo-значений.

### `/calendar`

Календарь компании:

- переключатель `Компания / Мой`;
- табы `Графік / Календар`;
- month toolbar и фильтр;
- матрица сотрудников x дни месяца;
- отпуск и отсутствие как горизонтальные полосы;
- праздники/важные дни как компактные иконки.

### `/attendance`

Присутствие компании:

- переключатель `Компанія / Мої`;
- вкладки `Головна / Понаднормово`;
- поиск по имени и фильтр;
- month toolbar;
- действия: управление проектами, экспорт, отправка напоминаний;
- таблица summary по сотрудникам: ожидаемо, отработано, переработка, перерыв,
  оплачиваемые/неоплачиваемые отсутствия, total absence, difference;
- drill-down из строки открывает календарь/детализацию конкретного сотрудника и
  raw СКУД events.

### `/requests`

Запросы:

- мои заявки;
- заявки на согласование;
- создать отпуск/выходной/коррекцию времени;
- статусы и история решений.

### `/knowledge`

База знаний:

- sidebar категорий;
- поиск;
- grid категорий/документов со счетчиками;
- управление категориями для HR/admin;
- просмотр документа, версий и вложений.

### `/org`

Организационная структура:

- доступна как вкладка внутри `Люди` и как прямой экран;
- canvas с деревом подчинения;
- карточки сотрудников с badge подчиненных;
- фильтр человека/департамента;
- controls fit/fullscreen/zoom/display mode;
- list fallback для телефона.

### `/settings`

Администрирование:

- роли;
- клиники/отделы/должности;
- импорт БАФ/Fotopacients;
- настройки СКУД;
- audit log.

## 10. Реализация по фазам

### Фаза 0: старт проекта

- Создать git repo в `/home/serv/hr_vidnova`.
- Зафиксировать Docker/dev окружение.
- Поднять Django/DRF + React/Vite skeleton.
- Подготовить `.env.example`, `docker-compose.yml`, базовый reverse proxy config.
- Описать deploy target `hr.vidnova.app`.

### Фаза 1: auth + сотрудники

- Пользователи и роли.
- Employee/Clinic/Department/Position.
- Список и профиль сотрудника.
- Начальный импорт сотрудников из БАФ/Fotopacients.
- Audit log для изменений сотрудника.

### Фаза 2: оргструктура

- ManagerAssignment.
- Org chart API.
- UI графа подчинения.
- Mobile fallback как список дерева.

### Фаза 3: отпуска

- LeaveType, LeaveRequest, ApprovalStep.
- Создание заявки сотрудником.
- Согласование руководителем.
- HR/admin override.
- Уведомления внутри приложения.

### Фаза 4: рабочее время

- WorkSchedule и WorkDaySummary.
- Ручной табель без СКУД, чтобы UI уже работал.
- Модель сырых `AccessEvent`.
- Adapter interface для СКУД.
- После уточнения СКУД: конкретный importer.

### Фаза 5: база знаний

- Категории и документы.
- Вложения и версии.
- Поиск.
- Права видимости.

### Фаза 6: production hardening

- Backup/restore procedure.
- Мониторинг web/db/redis/celery.
- Slow logs для тяжелых endpoints.
- Playwright smoke tests.
- Role/permission security review.

## 11. Технические решения, которые лучше принять сразу

### Отдельное приложение, не модуль FotoPacients

HR имеет другую модель безопасности, другой домен и другой lifecycle. Лучше
держать отдельный проект и интегрироваться через явный import/API, а не лезть в
таблицы FotoPacients напрямую.

### Сотрудник != пользователь

Не каждый сотрудник обязан иметь login. Модель `Employee` должна жить отдельно
от `User`. Если сотрудник заходит в систему, `User` связывается с `Employee`.

### СКУД как immutable raw events

События прохода нельзя править. Исправления — только через `TimeAdjustment`.
Так проще разбирать спорные случаи и строить аудит.

### Правила рабочего времени отдельно от событий

СКУД говорит "кто прошел и когда". HR-система решает "это опоздание, отсутствие
или норма" через правила графика.

### Все списки сразу делать paginated

Даже если сейчас сотрудников немного, таблицы отпусков, событий СКУД и audit log
быстро растут.

## 12. Минимальные индексы

Предварительно:

- `Employee(last_name, first_name)`;
- `Employee(clinic, department, is_active)`;
- `ExternalEmployeeLink(source, external_id)` unique;
- `ManagerAssignment(manager, valid_from, valid_to)`;
- `ManagerAssignment(employee, valid_from, valid_to)`;
- `AccessEvent(employee, occurred_at)`;
- `AccessEvent(device, occurred_at)`;
- `WorkDaySummary(employee, date)` unique;
- `LeaveRequest(employee, date_from, date_to)`;
- `LeaveRequest(status, created_at)`;
- `KnowledgeDocument(category, status, updated_at)`;
- trigram/search index для employee/document search после подтверждения PostgreSQL extension policy.

## 13. Безопасность

- HTTPS only на `hr.vidnova.app`.
- Secure cookies, CSRF trusted origin.
- RBAC на каждый endpoint.
- Сотрудник видит себя; руководитель видит подчиненных; HR видит всех.
- Audit log для отпусков, корректировок времени, изменения руководителя, прав.
- Вложения базы знаний проверять по MIME/extension/размеру.
- Не хранить секреты в repo.
- Backup БД и файлов.

## 14. Производительность

Ожидаемый масштаб небольшой, но надо не повторять типовые ошибки:

- pagination везде;
- не отдавать весь org graph без фильтра, если сотрудников станет много;
- для графа подчинения использовать compact API;
- СКУД events хранить отдельно от daily summaries;
- пересчет `WorkDaySummary` делать фоновыми задачами;
- frontend lazy-load для тяжелых экранов: org chart, knowledge viewer, settings.

## 15. Тестирование

### Backend

- model tests для отпусков и approval flow;
- permission tests по ролям;
- import tests для БАФ;
- SKUD adapter tests после появления формата;
- query-count tests для списков сотрудников, табеля, org chart.

### Frontend

- Playwright smoke:
  - login;
  - открыть dashboard;
  - найти сотрудника;
  - создать заявку на отпуск;
  - руководитель согласует заявку;
  - открыть табель;
  - открыть документ базы знаний;
  - открыть org chart на mobile viewport.

## 16. Вопросы, которые нужно уточнить

1. Где именно источник сотрудников: БАФ напрямую или через Fotopacients?
2. Какие поля доступны из БАФ: ФИО, телефон, должность, отдел, клиника, табельный
   номер, руководитель, статус активности?
3. Нужно ли сотрудникам самим логиниться или MVP только для руководителей/HR?
4. Какой точный workflow отпусков: только прямой руководитель или еще HR/директор?
5. Нужны ли остатки дней отпуска в MVP?
6. Какие клиники/локации входят в первую версию?
7. СКУД: производитель, способ доступа, формат событий, timezone, online/offline?
8. Как трактовать рабочее время: фиксированный график, смены, индивидуальные
   графики, округление опозданий?
9. Какие документы будут в базе знаний и нужны ли права по категориям?
10. Нужно ли уведомлять в Telegram/email или достаточно внутреннего inbox?

## 17. Ближайший практический шаг

Перед кодом нужно принять короткий набор решений:

- авторизация: локальные пользователи или связка с существующими учетками;
- источник сотрудников: API/DB/export из БАФ/Fotopacients;
- MVP workflow отпусков;
- базовая модель графика рабочего времени;
- storage для документов базы знаний.

После этого можно за 1 итерацию поднять skeleton проекта и первый рабочий flow:

`login -> dashboard -> employee list -> employee profile -> org manager relation -> leave request`.
