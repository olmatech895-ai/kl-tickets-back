# Tickets System Backend API

Backend API для системы управления тикетами, построенный на FastAPI с использованием принципов чистой архитектуры.

## Архитектура

Проект следует принципам чистой архитектуры (Clean Architecture) и разделен на слои:

### 1. Domain Layer (`app/domain/`)
- **Сущности (entities)**: Бизнес-сущности (User, Ticket, InventoryItem)
- **Репозитории (repositories)**: Интерфейсы репозиториев

### 2. Application Layer (`app/application/`)
- **Use Cases**: Бизнес-логика приложения
- **DTOs**: Объекты передачи данных

### 3. Infrastructure Layer (`app/infrastructure/`)
- **База данных**: Конфигурация и подключение к БД
- **Репозитории**: Реализация интерфейсов репозиториев
- **Конфигурация**: Настройки приложения

### 4. Presentation Layer (`app/presentation/`)
- **API Endpoints**: REST API маршруты
- **Schemas**: Pydantic схемы для валидации

## Быстрый старт

### 1. Установка зависимостей

```bash
cd backend
python setup.py
```

Или вручную:

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Настройка окружения

Создайте файл `.env` в папке `backend/` на основе `.env.example`:

```bash
cp .env.example .env
```

Или скопируйте содержимое `.env.example` в новый файл `.env` и при необходимости измените настройки.

### 3. Запуск сервера

```bash
# Вариант 1: Используя run.py
python run.py

# Вариант 2: Используя uvicorn напрямую
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Windows
run.bat

# Linux/Mac
chmod +x run.sh
./run.sh
```

Сервер будет доступен по адресу: http://localhost:8000

## API Документация

После запуска приложения доступна интерактивная документация:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Структура проекта

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # Точка входа FastAPI
│   ├── domain/                    # Domain Layer
│   │   ├── entities/              # Доменные сущности
│   │   │   ├── user.py
│   │   │   ├── ticket.py
│   │   │   └── inventory.py
│   │   └── repositories/          # Интерфейсы репозиториев
│   │       ├── user_repository.py
│   │       ├── ticket_repository.py
│   │       └── inventory_repository.py
│   ├── application/               # Application Layer
│   │   ├── use_cases/             # Use cases
│   │   │   └── user_use_cases.py
│   │   └── dto/                   # Data Transfer Objects
│   │       ├── user_dto.py
│   │       ├── ticket_dto.py
│   │       └── inventory_dto.py
│   ├── infrastructure/            # Infrastructure Layer
│   │   ├── database/              # База данных
│   │   │   └── base.py
│   │   ├── repositories/          # Реализация репозиториев
│   │   │   └── user_repository_impl.py
│   │   └── config/                # Конфигурация
│   │       └── settings.py
│   └── presentation/              # Presentation Layer
│       ├── api/
│       │   └── v1/
│       │       ├── routers/       # API маршруты
│       │       │   └── users.py
│       │       └── dependencies.py
│       └── schemas/               # API схемы
├── requirements.txt
├── .env.example
├── run.py                         # Скрипт запуска
├── setup.py                       # Скрипт установки
└── README.md
```

## Основные endpoints

### Authentication (Public)
- `POST /api/v1/auth/register` - Регистрация нового пользователя (возвращает JWT токен)
- `POST /api/v1/auth/login` - Вход в систему (возвращает JWT токен)
- `GET /api/v1/auth/me` - Получить информацию о текущем пользователе (требует токен)

### Users (Protected)
- `POST /api/v1/users/` - Создать пользователя (только admin, требует токен)
- `GET /api/v1/users/` - Получить всех пользователей (требует токен)
- `GET /api/v1/users/{user_id}` - Получить пользователя по ID (требует токен)
- `PUT /api/v1/users/{user_id}` - Обновить пользователя (только admin, требует токен)
- `DELETE /api/v1/users/{user_id}` - Удалить пользователя (только admin, требует токен)

## Аутентификация

API использует JWT токены для аутентификации. Токены выдаются на **24 часа**.

### Регистрация

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john.doe@kostalegal.com",
    "password": "SecurePass123",
    "role": "user"
  }'
```

**Валидация:**
- Email должен быть с доменом `@kostalegal.com`
- Пароль: минимум 8 символов, должна быть хотя бы одна буква и одна цифра
- Логин: минимум 3 символа

### Вход

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123"
  }'
```

### Использование токена

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

Подробная документация по аутентификации: [API_AUTH.md](API_AUTH.md)

## Примеры использования

### Создание пользователя

```bash
curl -X POST "http://localhost:8000/api/v1/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123",
    "role": "user"
  }'
```

### Аутентификация

```bash
curl -X POST "http://localhost:8000/api/v1/users/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

### Получение всех пользователей

```bash
curl -X GET "http://localhost:8000/api/v1/users/"
```

## Разработка

### Добавление новой функциональности

1. **Определите сущность** в `domain/entities/`
2. **Создайте интерфейс репозитория** в `domain/repositories/`
3. **Реализуйте репозиторий** в `infrastructure/repositories/`
4. **Создайте DTOs** в `application/dto/`
5. **Реализуйте use cases** в `application/use_cases/`
6. **Создайте API endpoints** в `presentation/api/v1/routers/`

## Тестирование

```bash
# Запуск тестов (когда будут добавлены)
pytest
```

## Примечания

- В текущей реализации используется in-memory хранилище для упрощения
- Для продакшена необходимо настроить реальную БД (PostgreSQL, MySQL)
- Не забудьте изменить SECRET_KEY в `.env` для продакшена
- Пароли хешируются с использованием bcrypt

## Требования

- Python 3.9+
- pip

## Лицензия

MIT
