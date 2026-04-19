# Flask + PostgreSQL + Redis + Nginx

Учебный Docker Compose проект для варианта 2 домашнего задания.
Шишмаков Михаил ФБМФ МФТИ

## Стек
- Nginx
- Flask
- Gunicorn
- PostgreSQL 15
- Redis 7
- Docker Compose

## Архитектура
Поток запросов: Browser -> Nginx -> Flask -> PostgreSQL + Redis

### Роли сервисов
- **nginx** — reverse proxy, принимает HTTP-запросы на `localhost:80`
- **app** — Flask-приложение с тремя эндпоинтами
- **postgres** — хранит постоянный счётчик посещений
- **redis** — кэширует ответ `/visits` на 10 секунд

## Структура проекта

```text
.
├── compose.yaml
├── .env.example
├── .gitignore
├── README.md
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
├── nginx/
│   └── nginx.conf
├── screenshots/
│   ├── main_page.png
│   ├── visits_fresh.png
│   ├── visits_cached.png
│   └── compose_ps.png
└── .github/
    └── workflows/
        └── validate.yml