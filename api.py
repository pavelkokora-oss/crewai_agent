"""
API сервер для обработки webhook-запросов от Google Таблиц.
Принимает запросы с темой, запускает агентов асинхронно и возвращает статус.
"""
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_openai import ChatOpenAI
import requests
import psycopg2

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения из .env файла
load_dotenv(override=True)

# Создаем Flask приложение
app = Flask(__name__)

# Создаем LLM для OpenAI
openai_llm = ChatOpenAI(
    model='gpt-4o-mini',
    temperature=0.7
)


def get_db_connection():
    """Получает подключение к Supabase PostgreSQL."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment variables")
    return psycopg2.connect(database_url)


def save_to_db(topic: str, content: str, author: str = None, date: str = None):
    """Сохраняет результат генерации в Supabase."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO blog_posts (topic, author, date, content, status)
            VALUES (%s, %s, %s, %s, 'completed')
            RETURNING id
        ''', (topic, author, date, str(content)))
        post_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"✅ Результат сохранен в Supabase с ID: {post_id}")
        return post_id
    except Exception as e:
        logger.error(f"❌ Ошибка при сохранении в БД: {str(e)}", exc_info=True)
        raise


def create_task_in_db(topic: str, author: str = None, date: str = None):
    """Создает задачу со статусом 'pending' в Supabase."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO blog_posts (topic, author, date, content, status)
            VALUES (%s, %s, %s, '', 'pending')
            RETURNING id
        ''', (topic, author, date))
        task_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"✅ Задача создана в Supabase с ID: {task_id}, тема: '{topic}'")
        return task_id
    except Exception as e:
        logger.error(f"❌ Ошибка при создании задачи в БД: {str(e)}", exc_info=True)
        raise


def get_pending_task():
    """Получает первую задачу со статусом 'pending' из Supabase."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, topic, author, date, created_at
            FROM blog_posts
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
        ''')
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'topic': row[1],
                'author': row[2],
                'date': row[3],
                'created_at': row[4]
            }
        return None
    except Exception as e:
        logger.error(f"❌ Ошибка при получении задачи из БД: {str(e)}", exc_info=True)
        return None


def update_task_status(task_id: int, status: str):
    """Обновляет статус задачи в Supabase."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE blog_posts
            SET status = %s
            WHERE id = %s
        ''', (status, task_id))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"✅ Статус задачи {task_id} обновлен на '{status}'")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении статуса задачи {task_id}: {str(e)}", exc_info=True)
        raise


def update_task_result(task_id: int, content: str, status: str = 'completed'):
    """Обновляет content и status задачи в Supabase."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE blog_posts
            SET content = %s, status = %s
            WHERE id = %s
        ''', (str(content), status, task_id))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"✅ Результат задачи {task_id} обновлен, статус: '{status}'")
    except Exception as e:
        logger.error(f"❌ Ошибка при обновлении результата задачи {task_id}: {str(e)}", exc_info=True)
        raise


@tool("Поиск в интернете")
def serper_search(query: str) -> str:
    """Поиск актуальных новостей и информации в интернете через Serper API."""
    api_key = os.getenv('SERPER_API_KEY')
    if not api_key:
        return "Ошибка: API ключ Serper не найден. Проверьте файл .env"
    
    url = "https://google.serper.dev/search"
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    payload = {
        'q': query,
        'num': 10
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Форматируем результаты
        results = []
        if 'organic' in data:
            for item in data['organic'][:5]:  # Берем первые 5 результатов
                title = item.get('title', 'Без названия')
                link = item.get('link', '')
                snippet = item.get('snippet', '')
                results.append(f"Название: {title}\nСсылка: {link}\nОписание: {snippet}\n")
        
        return "\n".join(results) if results else "Результаты поиска не найдены"
    except Exception as e:
        return f"Ошибка при поиске: {str(e)}"


def create_research_crew(topic: str, llm):
    """
    Создает Crew для исследования заданной темы и написания блог-поста.
    
    Args:
        topic: Тема для поиска новостей и написания блог-поста
        llm: LLM объект для использования агентами
    
    Returns:
        Crew объект готовый к выполнению
    """
    # Создаем агента-исследователя
    researcher = Agent(
        role='Исследователь новостей',
        goal=f'Найти актуальные и релевантные новости про {topic} в интернете',
        backstory=f'''Ты опытный исследователь, специализирующийся на поиске и анализе 
        информации в интернете. Ты умеешь находить самые свежие и важные новости 
        по теме "{topic}", анализировать их и предоставлять структурированную информацию.''',
        verbose=True,
        allow_delegation=False,
        tools=[serper_search],
        llm=llm
    )
    
    # Создаем агента-писателя
    writer = Agent(
        role='Блог-писатель',
        goal=f'Написать интересный и информативный пост для блога на русском языке о теме "{topic}" на основе найденных новостей',
        backstory='''Ты талантливый блог-писатель, который специализируется на 
        написании информативных статей. Ты умеешь структурировать информацию, 
        делать ее понятной для широкой аудитории и писать увлекательные тексты 
        на русском языке.''',
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
    
    # Создаем задачу для исследования
    research_task = Task(
        description=f'''Найди в интернете последние новости (за последние 1-2 недели) 
        про {topic}. Собери информацию о 3-5 самых интересных и важных новостях. 
        Включи в результат:
        - Название новости
        - Источник и дату публикации
        - Краткое описание содержания
        - Почему эта новость важна''',
        agent=researcher,
        expected_output=f'Структурированный список из 3-5 новостей про {topic} с названиями, источниками, датами и описаниями'
    )
    
    # Создаем задачу для написания поста
    writing_task = Task(
        description=f'''Используй результаты исследования новостей про {topic}, чтобы 
        написать короткий блог-пост на русском языке. Пост должен быть:
        - Информативным и интересным
        - Структурированным (с заголовком и несколькими абзацами)
        - Написанным для широкой аудитории
        - Объемом примерно 300-500 слов
        - Включать ключевые моменты из найденных новостей
        - Основанным на информации, которую собрал исследователь''',
        agent=writer,
        context=[research_task],
        expected_output=f'Полноценный блог-пост на русском языке объемом 300-500 слов про {topic} с заголовком и структурированным содержанием'
    )
    
    # Создаем crew (команду)
    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,
        verbose=True
    )
    
    return crew


def run_agents_async(topic: str, author: str = None, date: str = None):
    """
    Асинхронно запускает агентов для генерации блог-поста.
    
    Args:
        topic: Тема для исследования
        author: Автор (опционально, для логирования)
        date: Дата (опционально, для логирования)
    """
    try:
        logger.info(f"Запуск агентов для темы: {topic} (author: {author}, date: {date})")
        
        crew = create_research_crew(topic, openai_llm)
        result = crew.kickoff()
        
        # Сохраняем результат в Supabase
        post_id = save_to_db(topic, result, author, date)
        
        logger.info(f"✅ Генерация завершена для темы '{topic}'. Результат сохранен в Supabase с ID: {post_id}")
        logger.info(f"Результат (первые 200 символов): {str(result)[:200]}...")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при генерации блог-поста для темы '{topic}': {str(e)}", exc_info=True)


@app.route('/webhook/start-blogpost', methods=['POST'])
def start_blogpost():
    """
    POST эндпоинт для запуска генерации блог-поста.
    
    Ожидает JSON: {'topic': '...', 'author': '...', 'date': '...'}
    Возвращает: {'status': 'started'} со статусом 200
    """
    try:
        # Получаем JSON данные из запроса
        data = request.get_json()
        
        # Логируем входящий запрос
        logger.info(f"📥 Получен новый запрос: {data}")
        
        # Проверяем наличие обязательного поля topic
        if not data or 'topic' not in data:
            logger.warning("⚠️ Отсутствует обязательное поле 'topic' в запросе")
            return jsonify({'error': "Missing required field 'topic'"}), 400
        
        topic = data['topic']
        author = data.get('author', None)
        date = data.get('date', None)
        
        # Проверяем, что topic не пустой
        if not topic or not topic.strip():
            logger.warning("⚠️ Поле 'topic' пустое")
            return jsonify({'error': "Field 'topic' cannot be empty"}), 400
        
        logger.info(f"🚀 Создание задачи для темы: '{topic}'")
        if author:
            logger.info(f"   Автор: {author}")
        if date:
            logger.info(f"   Дата: {date}")
        
        # Создаем задачу в БД со статусом 'pending'
        task_id = create_task_in_db(topic.strip(), author, date)
        
        logger.info(f"✅ Задача создана с ID: {task_id} для темы: '{topic}'")
        
        # Сразу возвращаем успешный ответ
        return jsonify({'status': 'started', 'task_id': task_id}), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке запроса: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/results', methods=['GET'])
def get_results():
    """
    GET эндпоинт для получения всех результатов или с фильтрацией.
    
    Query параметры:
        - topic (опционально): фильтр по теме
        - limit (опционально, по умолчанию 50): количество результатов
        - offset (опционально, по умолчанию 0): смещение для пагинации
    
    Returns:
        JSON с массивом результатов и count
    """
    try:
        topic_filter = request.args.get('topic', None)
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Строим запрос в зависимости от наличия фильтра
        if topic_filter:
            cursor.execute('''
                SELECT id, topic, author, date, content, created_at, status
                FROM blog_posts
                WHERE topic ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', (f'%{topic_filter}%', limit, offset))
            
            # Получаем общее количество для подсчета
            cursor.execute('''
                SELECT COUNT(*) FROM blog_posts WHERE topic ILIKE %s
            ''', (f'%{topic_filter}%',))
        else:
            cursor.execute('''
                SELECT id, topic, author, date, content, created_at, status
                FROM blog_posts
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            ''', (limit, offset))
            
            # Получаем общее количество
            cursor.execute('SELECT COUNT(*) FROM blog_posts')
        
        total_count = cursor.fetchone()[0]
        
        # Получаем результаты
        rows = cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'topic': row[1],
                'author': row[2],
                'date': row[3],
                'content': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'status': row[6]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'results': results,
            'count': len(results),
            'total': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении результатов: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/results/<int:post_id>', methods=['GET'])
def get_result_by_id(post_id):
    """
    GET эндпоинт для получения результата по ID.
    
    Args:
        post_id: ID блог-поста
    
    Returns:
        JSON с результатом или 404 если не найден
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, topic, author, date, content, created_at, status
            FROM blog_posts
            WHERE id = %s
        ''', (post_id,))
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            return jsonify({'error': 'Blog post not found'}), 404
        
        result = {
            'id': row[0],
            'topic': row[1],
            'author': row[2],
            'date': row[3],
            'content': row[4],
            'created_at': row[5].isoformat() if row[5] else None,
            'status': row[6]
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении результата по ID {post_id}: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/results/latest', methods=['GET'])
def get_latest_results():
    """
    GET эндпоинт для получения последних N результатов.
    
    Query параметры:
        - limit (опционально, по умолчанию 10): количество последних результатов
    
    Returns:
        JSON с массивом последних результатов
    """
    try:
        limit = int(request.args.get('limit', 10))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, topic, author, date, content, created_at, status
            FROM blog_posts
            ORDER BY created_at DESC
            LIMIT %s
        ''', (limit,))
        
        rows = cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                'id': row[0],
                'topic': row[1],
                'author': row[2],
                'date': row[3],
                'content': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'status': row[6]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'results': results,
            'count': len(results),
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка при получении последних результатов: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check эндпоинт для проверки работоспособности сервера."""
    return jsonify({'status': 'ok'}), 200


if __name__ == '__main__':
    # Проверяем наличие необходимых API ключей
    openai_key = os.getenv('OPENAI_API_KEY')
    serper_key = os.getenv('SERPER_API_KEY')
    
    if not openai_key:
        logger.error("❌ OPENAI_API_KEY не найден в переменных окружения")
    if not serper_key:
        logger.error("❌ SERPER_API_KEY не найден в переменных окружения")
    
    if openai_key and serper_key:
        # Используем PORT из переменных окружения (Railway автоматически устанавливает его)
        port = int(os.getenv('PORT', 5000))
        logger.info("🚀 Запуск API сервера...")
        logger.info(f"📡 Порт: {port}")
        logger.info("📡 Эндпоинт: POST /webhook/start-blogpost")
        logger.info("💚 Health check: GET /health")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        logger.error("❌ Не удалось запустить сервер: отсутствуют необходимые API ключи")
