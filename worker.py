"""
Worker процесс для выполнения длительных задач генерации блог-постов.
Периодически проверяет БД на наличие задач со статусом 'pending' и выполняет их.
"""
import os
import time
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
import requests
import psycopg2

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем переменные окружения
load_dotenv(override=True)

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


def get_pending_task():
    """Получает первую задачу со статусом 'pending' из Supabase."""
    try:
        logger.debug("🔍 Подключение к БД для поиска задач...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Сначала проверим количество задач со статусом 'pending'
        cursor.execute('''
            SELECT COUNT(*) FROM blog_posts WHERE status = 'pending'
        ''')
        pending_count = cursor.fetchone()[0]
        logger.info(f"📊 Найдено задач со статусом 'pending': {pending_count}")
        
        # Получаем первую задачу
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
            logger.info(f"✅ Задача найдена в БД: ID={row[0]}, тема='{row[1]}'")
            return {
                'id': row[0],
                'topic': row[1],
                'author': row[2],
                'date': row[3],
                'created_at': row[4]
            }
        logger.info("ℹ️  Задач со статусом 'pending' не найдено")
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


def process_task(task):
    """Обрабатывает одну задачу: выполняет генерацию и сохраняет результат."""
    task_id = task['id']
    topic = task['topic']
    author = task.get('author')
    date = task.get('date')
    
    try:
        logger.info(f"🚀 Начало обработки задачи {task_id}: тема '{topic}'")
        
        # Обновляем статус на 'processing'
        update_task_status(task_id, 'processing')
        
        # Создаем crew и выполняем генерацию
        crew = create_research_crew(topic, openai_llm)
        result = crew.kickoff()
        
        # Сохраняем результат и обновляем статус на 'completed'
        update_task_result(task_id, str(result), 'completed')
        
        logger.info(f"✅ Задача {task_id} успешно обработана. Тема: '{topic}'")
        logger.info(f"Результат (первые 200 символов): {str(result)[:200]}...")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке задачи {task_id}: {str(e)}", exc_info=True)
        # Обновляем статус на 'failed'
        try:
            update_task_status(task_id, 'failed')
        except Exception as update_error:
            logger.error(f"❌ Ошибка при обновлении статуса на 'failed': {str(update_error)}", exc_info=True)


def main():
    """Основная функция worker процесса."""
    logger.info("🚀 Запуск Worker процесса для обработки задач генерации блог-постов")
    logger.info("⏱️  Интервал проверки новых задач: 10 секунд")
    
    # Проверяем наличие необходимых переменных окружения
    database_url = os.getenv('DATABASE_URL')
    openai_key = os.getenv('OPENAI_API_KEY')
    serper_key = os.getenv('SERPER_API_KEY')
    
    if not database_url:
        logger.error("❌ DATABASE_URL не найден в переменных окружения")
        return
    
    if not openai_key:
        logger.error("❌ OPENAI_API_KEY не найден в переменных окружения")
        return
    
    if not serper_key:
        logger.error("❌ SERPER_API_KEY не найден в переменных окружения")
        return
    
    logger.info("✅ Все необходимые переменные окружения найдены")
    
    # Основной цикл обработки задач
    iteration = 0
    while True:
        try:
            iteration += 1
            logger.info(f"🔄 Итерация {iteration}: Проверка наличия задач со статусом 'pending'...")
            
            # Получаем задачу со статусом 'pending'
            task = get_pending_task()
            
            if task:
                logger.info(f"📋 Найдена задача для обработки: ID={task['id']}, тема='{task['topic']}', создана: {task['created_at']}")
                process_task(task)
            else:
                # Если задач нет, просто ждем
                logger.info("⏳ Задач для обработки нет, ожидание 10 секунд...")
            
            # Ждем 10 секунд перед следующей проверкой
            logger.info("⏱️  Ожидание 10 секунд перед следующей проверкой...")
            time.sleep(10)
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки, завершение работы...")
            break
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка в основном цикле: {str(e)}", exc_info=True)
            # Продолжаем работу после ошибки, чтобы worker не останавливался
            time.sleep(10)


if __name__ == '__main__':
    main()
