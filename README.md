# HR Vidnova

Внутренняя HR-система для клиники Vidnova.

Планируемый домен: `hr.vidnova.app`  
Рабочая папка: `/home/serv/hr_vidnova`

## Цель

Сделать простое рабочее приложение для учета сотрудников, рабочего времени,
заявок на отпуск, базы знаний и наглядного графа подчинения.

Первый принцип: не строить тяжелую HRM/ERP. Система должна быстро открываться
на телефоне и сенсорном экране, быть понятной сотруднику и удобной для
руководителя клиники.

## Стартовая документация

- [Концепция и план реализации](docs/concept-and-implementation-plan.md)
- [UI-структура по референсным скриншотам](docs/ui-reference-structure.md)
- [Роли и импорт legacy-данных PeopleForce](docs/roles-and-legacy-data-import.md)
- [PeopleForce data model, import and compatibility API](docs/peopleforce-data-import-plan.md)
- [План интеграции СКУД на базе sunc_v4](docs/skud-sunc-v4-integration-plan.md)
- [Локальная разработка](docs/development.md)

## Предварительный стек

- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Background jobs: Celery + Redis
- Frontend: React + Vite + TypeScript
- UI: touch-first интерфейс в стиле FotoPacients, но с HR-ориентированной
  плотностью и спокойной визуальной системой
- Интеграции: FotoPacients для списка сотрудников и специализаций врачей, БАФ
  для учетных уточнений, СКУД для событий прохода

## Не решено

- production-доступ к read-only базе FotoPacients и финальная политика merge;
- формат и API интеграции со СКУД;
- правила округления рабочего времени, опозданий и переработок;
- маршрут согласования отпусков;
- способ авторизации сотрудников.

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

Backend API: `http://localhost:8050/api/`  
Frontend dev server: `http://localhost:5178`

После установки Python-зависимостей нужно сгенерировать первые миграции:

```bash
python manage.py makemigrations employees skud leave knowledge
python manage.py migrate
```
