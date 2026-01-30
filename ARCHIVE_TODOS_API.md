# API для архивации задач (Todos)

## Описание

Архивация задач позволяет скрыть завершенные или ненужные задачи из основного списка, сохраняя их для истории. Архивированные задачи имеют статус `"archived"` и не отображаются в обычных списках задач.

## База данных

Архивация реализована через поле `status` в таблице `todos`:
- Статус `"archived"` означает, что задача архивирована
- Поле `status` имеет тип `VARCHAR(100)`, что позволяет использовать статус "archived"
- Миграция базы данных не требуется - статус "archived" уже поддерживается

## API Endpoints

### POST /api/v1/todos/{todo_id}/archive
Архивировать задачу

**Требует:** Авторизации (JWT токен)

**Параметры:**
- `todo_id` (path) - ID задачи для архивации

**Ответ:**
```json
{
  "id": "uuid",
  "title": "Название задачи",
  "status": "archived",
  ...
}
```

**Ошибки:**
- `404` - Задача не найдена
- `403` - Недостаточно прав (можно архивировать только свои задачи)
- `400` - Задача уже архивирована

**Пример:**
```bash
POST /api/v1/todos/123e4567-e89b-12d3-a456-426614174000/archive
Authorization: Bearer <token>
```

### POST /api/v1/todos/{todo_id}/restore
Восстановить задачу из архива

**Требует:** Авторизации (JWT токен)

**Параметры:**
- `todo_id` (path) - ID задачи для восстановления

**Ответ:**
```json
{
  "id": "uuid",
  "title": "Название задачи",
  "status": "todo",
  ...
}
```

**Ошибки:**
- `404` - Задача не найдена
- `403` - Недостаточно прав
- `400` - Задача не архивирована

**Пример:**
```bash
POST /api/v1/todos/123e4567-e89b-12d3-a456-426614174000/restore
Authorization: Bearer <token>
```

### GET /api/v1/todos/archived
Получить все архивированные задачи текущего пользователя

**Требует:** Авторизации (JWT токен)

**Ответ:**
```json
[
  {
    "id": "uuid",
    "title": "Название задачи",
    "status": "archived",
    ...
  },
  ...
]
```

**Пример:**
```bash
GET /api/v1/todos/archived
Authorization: Bearer <token>
```

## Поведение

### Фильтрация архивированных задач

- **GET /api/v1/todos** - возвращает только НЕ архивированные задачи (статус != "archived")
- **GET /api/v1/todos/archived** - возвращает только архивированные задачи (статус == "archived")
- **GET /api/v1/todos/status/{status}** - возвращает задачи с указанным статусом (включая "archived" если указан)

### Права доступа

- Пользователь может архивировать только свои задачи:
  - Задачи, созданные пользователем (`created_by`)
  - Задачи, где пользователь назначен (`assigned_to`)
- То же самое для восстановления из архива

### WebSocket события

При архивации отправляется событие:
```json
{
  "type": "todo_archived",
  "todo": { ... }
}
```

При восстановлении отправляется событие:
```json
{
  "type": "todo_restored",
  "todo": { ... }
}
```

## Примеры использования

### JavaScript/TypeScript

```javascript
// Архивировать задачу
const archiveTodo = async (todoId) => {
  const response = await fetch(`/api/v1/todos/${todoId}/archive`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};

// Восстановить задачу
const restoreTodo = async (todoId) => {
  const response = await fetch(`/api/v1/todos/${todoId}/restore`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};

// Получить архивированные задачи
const getArchivedTodos = async () => {
  const response = await fetch('/api/v1/todos/archived', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.json();
};
```

## Важные моменты

1. **Архивация не удаляет задачу** - она только меняет статус на "archived"
2. **Архивированные задачи скрыты из основного списка** - они не показываются в `GET /api/v1/todos`
3. **Восстановление меняет статус на "todo"** - задача снова появляется в основном списке
4. **Можно архивировать задачу в любом статусе** - не обязательно "done"
5. **Архивированные задачи доступны через отдельный endpoint** - `GET /api/v1/todos/archived`
