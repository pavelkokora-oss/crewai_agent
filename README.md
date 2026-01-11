# CrewAI Agent - Поиск новостей и написание блог-поста

Веб-приложение на Streamlit для поиска последних новостей по любой теме и создания блог-поста на русском языке с использованием CrewAI.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` и добавьте ваши API ключи:
```bash
OPENAI_API_KEY=ваш_ключ_openai
SERPER_API_KEY=ваш_ключ_serper
DATABASE_URL=postgresql://postgres:password@host:port/database  # Только для API сервера (api.py)
```

**⚠️ ВАЖНО для безопасности:**
- Файл `.env` автоматически игнорируется Git (в `.gitignore`)
- **НИКОГДА** не коммитьте файл `.env` с реальными ключами в репозиторий
- Для Streamlit Cloud используйте встроенный Secrets Manager вместо `.env` файла

## Использование

### Веб-приложение (Streamlit) - Рекомендуется

Запустите Streamlit приложение:
```bash
streamlit run app.py
```

Приложение откроется в браузере. Вы сможете:
- Ввести любую тему для исследования (например: "AI Agents", "машинное обучение", "блокчейн")
- Нажать кнопку "Запустить исследование"
- Увидеть результат в Markdown формате на странице
- Скачать результат в виде файла

### CLI запуск (main.py)

Для запуска через командную строку:
```bash
python main.py
```

Это выполнит поиск новостей про AI Agents (тема жестко задана) и сохранит результат в `blog_post.txt`.

## Что делает приложение

1. **Исследователь** ищет последние новости (1-2 недели) по заданной теме через Serper API
2. **Писатель** создает информативный блог-пост на русском языке на основе найденных новостей
3. Результат отображается в Markdown формате (в Streamlit) или сохраняется в Supabase (через API)

## Структура проекта

- `app.py` - Streamlit веб-приложение с интерактивным интерфейсом
- `api.py` - Flask API сервер для обработки webhook-запросов и хранения результатов в Supabase
- `main.py` - CLI версия агента CrewAI (тема "AI Agents" жестко задана)
- `requirements.txt` - зависимости проекта
- `.env` - файл с переменными окружения (создайте его самостоятельно, **НЕ коммитьте в Git!**)
- `env.example` - пример файла с переменными окружения (без реальных ключей)
- `Procfile` - конфигурация для деплоя на Railway.app
- `runtime.txt` - версия Python для деплоя

## API Сервер (api.py)

Flask API сервер предоставляет следующие эндпоинты:

### POST /webhook/start-blogpost
Запускает генерацию блог-поста асинхронно.

**Тело запроса (JSON):**
```json
{
  "topic": "AI Agents",
  "author": "Иван Иванов",
  "date": "2024-01-15"
}
```

**Ответ:**
```json
{
  "status": "started"
}
```

### GET /webhook/results
Получить все результаты с опциональной фильтрацией.

**Query параметры:**
- `topic` (опционально) - фильтр по теме (ILIKE поиск)
- `limit` (опционально, по умолчанию 50) - количество результатов
- `offset` (опционально, по умолчанию 0) - смещение для пагинации

**Пример:**
```
GET /webhook/results?topic=AI&limit=10&offset=0
```

### GET /webhook/results/<id>
Получить результат по ID.

**Пример:**
```
GET /webhook/results/1
```

### GET /webhook/results/latest
Получить последние N результатов.

**Query параметры:**
- `limit` (опционально, по умолчанию 10) - количество последних результатов

**Пример:**
```
GET /webhook/results/latest?limit=5
```

### GET /health
Health check эндпоинт для проверки работоспособности сервера.

**Запуск API сервера:**
```bash
python api.py
```

Или для production (Railway):
```bash
gunicorn api:app
```

## База данных (Supabase)

Результаты генерации блог-постов сохраняются в PostgreSQL базе данных Supabase.

### Создание таблицы

Выполните следующий SQL в Supabase SQL Editor:

```sql
CREATE TABLE blog_posts (
    id SERIAL PRIMARY KEY,
    topic TEXT NOT NULL,
    author TEXT,
    date TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'completed'
);

CREATE INDEX idx_blog_posts_topic ON blog_posts(topic);
CREATE INDEX idx_blog_posts_created_at ON blog_posts(created_at DESC);
```

### Получение Connection String

1. Откройте Supabase Dashboard → ваш проект
2. Перейдите в Settings → Database
3. Скопируйте Connection string (URI)
4. **ВАЖНО:** Если в пароле есть специальные символы (например, `@`), их нужно URL-кодировать:
   - `@` → `%40`
   - `#` → `%23`
   - и т.д.

**Пример:**
```
postgresql://postgres:QJjfN2%40kfIqW1@db.xxx.supabase.co:5432/postgres
```

## Публикация в Streamlit Cloud

### Безопасная настройка API ключей

1. **НЕ загружайте файл `.env`** в репозиторий
2. В Streamlit Cloud:
   - Откройте настройки приложения → **Secrets**
   - Добавьте ключи в формате TOML:
   ```toml
   OPENAI_API_KEY = "ваш_реальный_ключ_openai"
   SERPER_API_KEY = "ваш_реальный_ключ_serper"
   ```
3. Приложение автоматически использует `st.secrets` из Streamlit Cloud

### Проверка безопасности перед публикацией

```bash
# Убедитесь, что .env файл игнорируется Git
git check-ignore .env

# Проверьте, что нет файлов с секретами в репозитории
git ls-files | grep -E '\.env|secrets\.toml'
```

Если команды показывают, что файлы игнорируются — всё в порядке! ✅
