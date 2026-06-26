# Roles and legacy PeopleForce import

Дата: 2026-06-24  
Статус: проектное решение для MVP

## Цель

HR Vidnova должна заменить PeopleForce как рабочий HR-интерфейс, но на старте
нужно забрать из PeopleForce данные, которых нет в BAF/Fotopacients:

- базу знаний: категории, документы, вложения, описания, счетчики, порядок;
- должности, команды, департаменты и другие справочники, если они отсутствуют в
  BAF;
- подчинение и историю менеджеров;
- дополнительные employee fields: рабочий email, телефон, дата начала,
  локация, фото, если их нет или они неполные в BAF;
- отпускные остатки и историю заявок только если они нужны для MVP;
- legacy identifiers для последующей сверки.

PeopleForce после миграции не должен оставаться обязательной runtime-зависимостью.
Он используется как legacy source для первичной миграции и, при необходимости,
короткого read-only reconciliation периода.

## Базовая модель доступа

Сотрудник (`Employee`) и пользователь системы (`User`) остаются разными сущностями.
Не каждый сотрудник обязан иметь login. Если сотрудник входит в систему, `User`
связывается с `Employee`.

Доступ строится из трех слоев:

1. Global role: системная роль пользователя.
2. Scope: какие сотрудники/клиники/департаменты доступны.
3. Object rules: дополнительные правила для конкретной заявки, документа,
   корректировки времени или import run.

Технически на backend:

- Django `User` + `Group` для coarse-grained ролей;
- отдельная модель `RoleAssignment` для scope-aware доступа;
- object-level проверки в service/view layer;
- audit log для изменения ролей и scope.

## Роли MVP

### Employee

Обычный сотрудник.

Может:

- видеть свой профиль;
- видеть свои отметки, рабочие дни и исключения;
- создавать заявки на отпуск/выходной;
- создавать запрос на корректировку времени;
- читать доступные документы базы знаний.

Не может:

- видеть чужие персональные данные;
- менять raw события СКУД;
- видеть служебные import errors, audit log и настройки.

### Manager

Руководитель команды, отдела или клиники.

Scope:

- прямые и непрямые подчиненные по `ManagerAssignment`;
- опционально вся клиника/департамент, если это задано в `RoleAssignment`.

Может:

- видеть профили подчиненных;
- видеть присутствие и исключения по команде;
- согласовывать отпуска и корректировки времени подчиненных;
- видеть оргструктуру своего scope;
- читать manager-only документы базы знаний.

Не может:

- менять должности, департаменты и глобальные роли;
- редактировать базу знаний, если нет отдельной роли.

### HR Specialist

Операционная HR-роль.

Может:

- управлять сотрудниками и локальными HR-полями;
- создавать и исправлять manager assignments;
- проверять импорт сотрудников;
- обрабатывать заявки и исключения времени;
- публиковать документы, если дополнительно есть `Knowledge Editor`;
- видеть audit log по HR-операциям.

Не может:

- менять технические настройки интеграций и секреты;
- назначать `System Admin`.

### HR Admin

Главная HR-роль.

Может:

- все действия `HR Specialist`;
- управлять ролями HR/manager/knowledge/timekeeper;
- управлять справочниками: клиники, департаменты, должности;
- запускать read-only legacy import и подтверждать merge conflicts;
- делать HR override по отпуску/времени.

Не должен:

- иметь доступ к техническим секретам интеграций без роли `System Admin`.

### Director / Owner

Руководитель компании.

Может:

- видеть всю оргструктуру;
- видеть агрегированные отчеты;
- видеть отпуска/присутствие по всей компании;
- быть финальным согласующим в отдельных workflow;
- читать директорские документы базы знаний.

Обычно не редактирует справочники и raw imports.

### Knowledge Editor

Редактор базы знаний.

Может:

- создавать категории;
- создавать и обновлять документы;
- загружать вложения;
- публиковать версии;
- настраивать видимость документа по роли/клинике/департаменту.

Не получает автоматически доступ к персональным данным сотрудников.

### Timekeeper / SKUD Operator

Роль для контроля присутствия и СКУД.

Может:

- видеть raw события СКУД;
- видеть ошибки импорта;
- пересчитывать `WorkDaySummary`;
- рассматривать запросы на корректировку времени.

Не может:

- редактировать raw события;
- управлять отпусками и ролями.

### System Admin

Технический администратор.

Может:

- управлять настройками интеграций;
- смотреть import runs и технические ошибки;
- управлять deployment/runtime настройками;
- назначать системные роли.

Доступ к HR-персональным данным должен быть минимальным и явно назначенным, не
автоматическим.

## Permission matrix

| Действие | Employee | Manager | HR Specialist | HR Admin | Director | Knowledge Editor | Timekeeper | System Admin |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Свой профиль | R | R | R | R | R | - | - | - |
| Профили подчиненных | - | R | RW | RW | R | - | - | - |
| Все сотрудники | - | scope | RW | RW | R | - | - | optional |
| Должности/департаменты | - | R | R | RW | R | - | - | - |
| Подчинение | - | R scope | RW | RW | R | - | - | - |
| Своя присутність | R | R | R | R | R | - | - | - |
| Присутність команды | - | R | RW | RW | R | - | RW | - |
| Raw СКУД events | - | - | R | R | - | - | R | R |
| Коррекция времени | C own | approve scope | RW | RW | R | - | RW | - |
| Заявка на отпуск | C own | approve scope | RW | RW | approve optional | - | - | - |
| База знаний read | R scoped | R scoped | R scoped | R all | R scoped | R scoped | R scoped | - |
| База знаний write | - | - | optional | RW | - | RW | - | - |
| Импорт BAF/Fotopacients | - | - | R | RW | R | - | - | R |
| Импорт PeopleForce | - | - | R | RW | R | - | - | R |
| Роли и доступ | - | - | - | RW HR roles | R | - | - | RW |

`R` - read, `C` - create, `RW` - read/write. `scope` означает доступ только в
пределах назначенной клиники/департамента/подчинения.

## Source of truth

### FotoPacients

Основной источник текущего списка сотрудников для MVP. Важно: HR импортирует
не только врачей, а всех сотрудников из `accounts_user`:

- активность сотрудника;
- ФИО, email, телефоны;
- роль FotoPacients (`admin`, `senior_doctor`, `doctor`, `assistant`, `staff`);
- клиника и департаменты через `clinic` / `departments`;
- связь с BAF/медицинским контуром через `baf_id`;
- медицинские специализации врачей через `patients_doctor.specialties`;
- fallback-специализация из `accounts_user.specialty`, если M2M еще не заполнен.

Импорт должен использовать read-only подключение к базе FotoPacients через
отдельный Django database alias `fotopacients`. HR Vidnova не импортирует
Django-модели FotoPacients напрямую, чтобы не связывать две кодовые базы.

### BAF

Источник уточнения для полей, которые ведутся в учетной системе:

- табельный/внутренний номер;
- официальная занятость и увольнение;
- должность/подразделение, если эти поля подтверждены как более точные;
- базовые контакты, если они ведутся в BAF.

### PeopleForce legacy

Источник начального enrichment:

- база знаний и вложения;
- должности, если в BAF их нет или они неполные;
- департаменты/команды, если в BAF нет структуры;
- manager assignments и оргструктура;
- employee photo, email, phone, start date, если BAF неполный;
- исторические заявки/остатки отпусков только по отдельному решению.

### HR Vidnova local

Локальный слой поверх внешних источников:

- роли и доступ;
- подтвержденный руководитель;
- локальные настройки видимости базы знаний;
- ручные корректировки времени;
- HR decisions по conflict resolution;
- audit log.

## Precedence rules

1. Существование сотрудника для MVP: FotoPacients `accounts_user`.
2. Активный статус: FotoPacients, позже сверка с BAF при наличии поля.
3. Медицинские специализации: FotoPacients `patients_doctor.specialties` и
   `accounts_user.specialty`.
4. Должность/департамент: BAF, если поле есть и подтверждено; иначе
   PeopleForce legacy; после миграции HR Vidnova.
5. Подчинение: PeopleForce legacy для initial import; после миграции HR Vidnova.
6. База знаний: PeopleForce legacy initial import; после миграции HR Vidnova.
7. Email/phone/photo/start date: FotoPacients/BAF, если есть; иначе PeopleForce; конфликт
   уходит в manual review.
8. Raw СКУД: только СКУД adapters, не PeopleForce.

## FotoPacients employee sync

Команда:

```bash
python manage.py sync_fotopacients_employees --dry-run --limit 20
python manage.py sync_fotopacients_employees
```

Конфигурация через `.env`:

- `FOTOPACIENTS_DB_ENABLED=1`;
- `FOTOPACIENTS_DB_HOST`, `FOTOPACIENTS_DB_PORT`;
- `FOTOPACIENTS_DB_NAME`, `FOTOPACIENTS_DB_USER`, `FOTOPACIENTS_DB_PASSWORD`.

Mapping:

- `accounts_user.id` -> `Employee.external_fotopacients_id` и
  `ExternalEmployeeLink(source=fotopacients)`;
- `accounts_user.baf_id` -> `Employee.external_baf_id`;
- `accounts_user.role` -> `Position`;
- `accounts_user.clinic` -> `Clinic`;
- первый `accounts_user.departments` -> основной `Department`;
- все найденные специальности врача -> `MedicalSpecialty`.

Для отбора работающих сейчас используется строгий фильтр:

- `accounts_user.is_active = true`;
- `accounts_user.is_deleted = false`;
- для врачей, связанных с BAF через `baf_id`, дополнительно
  `patients_doctor.is_deleted_in_baf = false`.

Если у сотрудника несколько департаментов, HR записывает первый как основной и
создает `EmployeeImportIssue` для ручной проверки. Автоматический merge по
одному email, телефону или ФИО не делается на первом этапе.

## Matching employees

Порядок matching:

1. `ExternalEmployeeLink(source=fotopacients, external_id=accounts_user.id)`;
2. `Employee.external_fotopacients_id`;
3. `Employee.external_baf_id`, если `accounts_user.baf_id` заполнен;
4. exact PeopleForce id через `ExternalEmployeeLink`, если он уже известен;
5. normalized email/phone только после ручного подтверждения политики merge;
6. normalized full name + location/department только через manual review.

Запрещено автоматически merge по одному ФИО без дополнительного признака.

## PeopleForce migration entities

Минимальные модели для импорта:

- `LegacyImportRun`: source, status, started_at, finished_at, counters, actor;
- `LegacyImportIssue`: run, severity, entity_type, external_id, message,
  raw_fragment;
- `ExternalEmployeeLink`: source=`peopleforce`, external_id, employee,
  last_seen_at, raw_hash;
- `LegacyKnowledgeLink`: peopleforce category/document/file id -> HR object id;
- `LegacyOrgLink`: peopleforce team/position/department id -> HR object id.

## Import flow

### 1. Inventory

- получить список PeopleForce endpoints/exports;
- выгрузить counts по сотрудникам, должностям, департаментам, документам,
  вложениям, manager relations;
- не сохранять токены и секреты в repo/logs/memory.

### 2. Dry run

- импортировать в staging или локальную БД;
- построить match report;
- посчитать conflicts, duplicates, missing files, orphan managers;
- ничего не менять в production HR Vidnova.

### 3. Mapping review

HR подтверждает:

- unmatched employees;
- спорные должности/департаменты;
- отсутствующих руководителей;
- какие категории базы знаний переносить;
- кто будет владельцем legacy документов.

### 4. Production import

- read-only pull из PeopleForce;
- write в HR Vidnova через import services;
- каждая запись получает external link и raw hash;
- вложения сохраняются с checksum;
- все проблемы пишутся в `LegacyImportIssue`.

### 5. Cutover

- PeopleForce больше не source of truth;
- новые изменения должностей, подчинения и базы знаний делаются в HR Vidnova;
- повторный PeopleForce import разрешен только в режиме reconciliation и только
  для legacy полей, которые еще не были локально изменены.

## Knowledge base import rules

- сохранить дерево категорий;
- сохранить название, описание, body/summary, теги, порядок;
- сохранить вложения с original filename, MIME, size, checksum;
- если есть версии, перенести как `KnowledgeDocumentVersion`;
- автора документа match по сотруднику, иначе `Legacy import`;
- права видимости импортировать осторожно: если PeopleForce roles не мапятся,
  документ получает статус `draft_review`;
- публикацию делать только после проверки HR/Knowledge Editor.

## Open questions

1. Есть ли PeopleForce API token с read-only доступом к knowledge base?
2. Можно ли экспортировать вложения базы знаний напрямую или нужен browser/export
   flow?
3. Какие поля точно отсутствуют в BAF: должность, департамент, руководитель,
   дата начала, email, телефон, фото?
4. Нужны ли исторические отпуска и остатки дней в MVP?
5. Кто подтверждает конфликтные employee matches?
6. Сколько времени держим reconciliation период с PeopleForce после cutover?
