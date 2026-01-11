"""
Streamlit веб-приложение для поиска новостей и написания блог-постов через CrewAI.
Использует OpenAI API в качестве провайдера LLM.

БЕЗОПАСНОСТЬ:
- API ключи никогда не хранятся в коде
- Ключи берутся из st.secrets (Streamlit Cloud) или os.environ (локально)
- Ключи никогда не выводятся в интерфейс или логи
- Файлы с секретами (.env, .streamlit/secrets.toml) должны быть в .gitignore
"""
import os
import json
import traceback
from datetime import datetime

# #region agent log
try:
    with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"id":"log_import_start","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:13","message":"Starting imports","data":{"step":"import_os_requests"},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
except: pass
# #endregion

import requests
import streamlit as st

# #region agent log
try:
    with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"id":"log_import_streamlit","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:17","message":"Streamlit imported","data":{"step":"import_streamlit"},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
except: pass
# #endregion

from dotenv import load_dotenv

# #region agent log
try:
    with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"id":"log_before_load_dotenv","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:22","message":"Before load_dotenv","data":{"step":"before_load_dotenv"},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
except: pass
# #endregion

# Загружаем переменные окружения из .env файла (для локального запуска)
# ВНИМАНИЕ: .env файл должен быть в .gitignore и НЕ попадать в репозиторий!
try:
    load_dotenv(override=True)
    # #region agent log
    try:
        with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"id":"log_after_load_dotenv","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:27","message":"After load_dotenv","data":{"step":"load_dotenv_success"},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
    except: pass
    # #endregion
except Exception as e:
    # #region agent log
    try:
        with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"id":"log_load_dotenv_error","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:30","message":"load_dotenv error","data":{"error":str(e),"traceback":traceback.format_exc()},"sessionId":"debug-session","runId":"run1","hypothesisId":"D"}) + "\n")
    except: pass
    # #endregion
    raise

# #region agent log
try:
    with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"id":"log_before_crewai_import","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:34","message":"Before CrewAI import","data":{"step":"before_crewai"},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
except: pass
# #endregion

from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_openai import ChatOpenAI

# #region agent log
try:
    with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
        f.write(json.dumps({"id":"log_after_all_imports","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:40","message":"All imports completed","data":{"step":"imports_complete"},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
except: pass
# #endregion


def get_api_key(key_name: str) -> str | None:
    """
    Безопасно получает API ключ из st.secrets или os.environ.
    Сначала проверяет st.secrets (для Streamlit Cloud), затем os.environ (для локального запуска).
    
    ВАЖНО: Эта функция НИКОГДА не должна выводить ключи в логи или на экран!
    
    Args:
        key_name: Имя ключа (например, 'OPENAI_API_KEY', 'SERPER_API_KEY')
    
    Returns:
        Значение ключа или None, если не найден
    """
    # Сначала пробуем получить из st.secrets (для Streamlit Cloud)
    try:
        if hasattr(st, 'secrets') and st.secrets is not None:
            # Пробуем получить через словарную нотацию (st.secrets['OPENAI_API_KEY'])
            # st.secrets работает как словарь в Streamlit
            if key_name in st.secrets:
                value = st.secrets[key_name]
                if value and str(value).strip():
                    return str(value).strip()
            # Также пробуем получить через точечную нотацию (st.secrets.OPENAI_API_KEY)
            # для совместимости с разными версиями Streamlit
            if hasattr(st.secrets, key_name):
                value = getattr(st.secrets, key_name)
                if value and str(value).strip():
                    return str(value).strip()
    except (AttributeError, KeyError, TypeError):
        pass
    
    # Если не нашли в st.secrets, пробуем из os.environ (для локального запуска)
    value = os.getenv(key_name)
    if value:
        return value.strip()
    return None

# Создаем кастомный инструмент для поиска через Serper API
@tool("Поиск в интернете")
def serper_search(query: str) -> str:
    """Поиск актуальных новостей и информации в интернете через Serper API. 
    Используй для поиска последних новостей по указанной теме."""
    api_key = get_api_key('SERPER_API_KEY')
    if not api_key:
        return "Ошибка: API ключ Serper не найден. Проверьте st.secrets или файл .env"
    
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
    # Создаем агента-исследователя с универсальным backstory
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
    
    # Создаем агента-писателя с универсальным backstory
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
    
    # Создаем задачу для исследования с динамической темой
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
    
    # Создаем задачу для написания поста с динамической темой
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
        context=[research_task],  # Используем результаты исследования как контекст
        expected_output=f'Полноценный блог-пост на русском языке объемом 300-500 слов про {topic} с заголовком и структурированным содержанием'
    )
    
    # Создаем crew (команду)
    crew = Crew(
        agents=[researcher, writer],
        tasks=[research_task, writing_task],
        process=Process.sequential,  # Задачи выполняются последовательно
        verbose=True
    )
    
    return crew


def check_api_keys():
    """
    Безопасно проверяет наличие необходимых API ключей.
    Сначала проверяет st.secrets, затем os.environ.
    
    ВАЖНО: Эта функция НЕ выводит ключи, только проверяет их наличие и формат.
    
    Returns:
        tuple: (bool, list) - (все_ключи_найдены, список_отсутствующих_ключей)
    """
    missing_keys = []
    
    # Проверяем OPENAI_API_KEY
    openai_key = get_api_key('OPENAI_API_KEY')
    if not openai_key:
        missing_keys.append('OPENAI_API_KEY')
    else:
        # Проверяем формат ключа OpenAI (без вывода самого ключа)
        if not openai_key.startswith('sk-'):
            return False, ['OPENAI_API_KEY (неверный формат)']
    
    # Проверяем SERPER_API_KEY
    serper_key = get_api_key('SERPER_API_KEY')
    if not serper_key:
        missing_keys.append('SERPER_API_KEY')
    
    return len(missing_keys) == 0, missing_keys


def get_blog_posts(api_url: str, limit: int = 50):
    """
    Получает список блог-постов через GET /webhook/results эндпоинт.
    
    Args:
        api_url: Базовый URL API сервера (например, https://your-app.railway.app)
        limit: Количество результатов для получения (по умолчанию 50)
    
    Returns:
        list: Список словарей с данными блог-постов или None в случае ошибки
    """
    if not api_url or not api_url.strip():
        return None
    
    try:
        # Убираем завершающий слеш, если есть
        api_url = api_url.strip().rstrip('/')
        url = f"{api_url}/webhook/results?limit={limit}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('results', [])
        else:
            return None
    except Exception as e:
        return None


def main():
    """Основная функция Streamlit приложения."""
    # #region agent log
    try:
        with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"id":"log_main_start","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:206","message":"main() called","data":{"step":"main_entry"},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
    except: pass
    # #endregion
    
    # #region agent log
    try:
        with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"id":"log_before_set_page_config","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:210","message":"Before set_page_config","data":{"step":"before_page_config"},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
    except: pass
    # #endregion
    
    try:
        st.set_page_config(
            page_title="CrewAI - Поиск новостей и создание блог-постов",
            page_icon="🚀",
            layout="wide"
        )
        # #region agent log
        try:
            with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"id":"log_after_set_page_config","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:220","message":"After set_page_config","data":{"step":"page_config_success"},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
        except: pass
        # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"id":"log_set_page_config_error","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:223","message":"set_page_config error","data":{"error":str(e),"traceback":traceback.format_exc()},"sessionId":"debug-session","runId":"run1","hypothesisId":"C"}) + "\n")
        except: pass
        # #endregion
        st.error(f"Ошибка настройки страницы: {str(e)}")
        return
    
    # Инициализируем session_state для хранения результата
    if 'result' not in st.session_state:
        st.session_state.result = None
    if 'last_topic' not in st.session_state:
        st.session_state.last_topic = None
    
    # Sidebar с настройками (webhook URL и API URL)
    with st.sidebar:
        st.header("⚙️ Настройки")
        webhook_url = st.text_input(
            "n8n Webhook URL",
            placeholder="https://your-n8n-instance.com/webhook/...",
            help="Введите URL webhook для отправки результата в Telegram через n8n"
        )
        api_url = st.text_input(
            "API Server URL",
            value=get_api_key('API_URL') or "",
            placeholder="https://your-app.railway.app",
            help="URL API сервера для просмотра результатов (например, Railway app URL)"
        )
    
    # #region agent log
    try:
        with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"id":"log_before_title","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:235","message":"Before st.title","data":{"step":"before_title"},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
    except: pass
    # #endregion
    
    # ЗАГОЛОВОК - показывается ПЕРВЫМ при открытии сайта
    st.title("🚀 CrewAI - Поиск новостей и создание блог-постов")
    
    # Вкладки для разделения функционала
    tab1, tab2 = st.tabs(["📝 Создать блог-пост", "📊 История результатов"])
    
    with tab1:
        st.markdown("---")
        
        # #region agent log
        try:
            with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"id":"log_after_title","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:240","message":"After st.title","data":{"step":"title_displayed"},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
        except: pass
        # #endregion
        
        # ПОЛЕ ВВОДА ТЕМЫ - показывается сразу после заголовка
        st.subheader("Введите тему для исследования")
        topic = st.text_input(
            "Тема новостей",
            placeholder="Например: AI Agents, машинное обучение, блокчейн, квантовые компьютеры...",
            help="Введите тему, по которой вы хотите найти новости и создать блог-пост"
        )
        
        # Кнопка запуска
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            run_button = st.button("🔍 Запустить исследование", type="primary", use_container_width=True)
        
        # Обработка нажатия кнопки - ВСЕ ПРОВЕРКИ И ЗАПУСК АГЕНТОВ ТОЛЬКО ЗДЕСЬ
        if run_button:
            # Проверяем, что тема введена
            if not topic or topic.strip() == "":
                st.warning("⚠️ Пожалуйста, введите тему для исследования")
                st.stop()
            
            # БЕЗОПАСНО получаем API ключи (сначала из st.secrets, затем из os.environ)
            # ВАЖНО: Никогда не выводите ключи через st.write(), print() или в логи!
            openai_api_key = get_api_key('OPENAI_API_KEY')
            serper_api_key = get_api_key('SERPER_API_KEY')
            
            # Безопасно проверяем API ключи
            keys_ok, missing_keys = check_api_keys()
            
            if not keys_ok:
                st.error("⚠️ Проблема с API ключами")
                st.write("Не найдены следующие API ключи:")
                for key in missing_keys:
                    st.write(f"- **{key}**")
                
                st.write("\n**Где указать ключи:**")
                st.markdown("""
                **Для Streamlit Cloud:**
                - Перейдите в настройки приложения → Secrets
                - Добавьте ключи в формате:
                ```toml
                OPENAI_API_KEY = "ваш_ключ_openai"
                SERPER_API_KEY = "ваш_ключ_serper"
                ```
                
                **Для локального запуска:**
                - Создайте файл `.streamlit/secrets.toml` (для Streamlit) или используйте `.env` (для dotenv)
                - Добавьте ключи в `.streamlit/secrets.toml`:
                ```toml
                OPENAI_API_KEY = "ваш_ключ_openai"
                SERPER_API_KEY = "ваш_ключ_serper"
                ```
                или в `.env`:
                ```
                OPENAI_API_KEY=ваш_ключ_openai
                SERPER_API_KEY=ваш_ключ_serper
                ```
                """)
                
                if 'OPENAI_API_KEY' in missing_keys or 'OPENAI_API_KEY (неверный формат)' in str(missing_keys):
                    st.info("💡 Ключ OpenAI должен начинаться с `sk-`")
                st.stop()
            
            # Проверяем, что ключ не является примером
            if openai_api_key and ('your' in openai_api_key.lower() or 'example' in openai_api_key.lower()):
                st.error("⚠️ Похоже, что вы используете пример ключа вместо реального!")
                st.write("Пожалуйста, замените ключ на ваш реальный ключ от OpenAI в `st.secrets` или `.env` файле")
                st.stop()
            
            # Устанавливаем ключи в переменные окружения для ChatOpenAI, если они найдены
            # Это необходимо для работы langchain_openai, но ключи остаются в памяти процесса
            if openai_api_key:
                os.environ['OPENAI_API_KEY'] = openai_api_key
            
            # Создаем LLM для OpenAI (нужно создавать после получения ключей)
            openai_llm = ChatOpenAI(
                model='gpt-4o-mini',  # Используем gpt-4o-mini - быструю и недорогую модель OpenAI
                temperature=0.7
            )
            
            # Создаем crew и запускаем агентов ТОЛЬКО внутри условия if st.button
            try:
                with st.spinner('⏳ Агенты работают...'):
                    crew = create_research_crew(topic, openai_llm)
                    result = crew.kickoff()
                    
                    # Сохраняем результат в session_state
                    st.session_state.result = str(result)
                    st.session_state.last_topic = topic
                    
                    # Сохраняем результат в файл
                    with open('blog_post.txt', 'w', encoding='utf-8') as f:
                        f.write(str(result))
                
                # Показываем сообщение об успешном завершении после spinner
                st.success("✅ Исследование завершено! Результат отображается ниже.")
            except Exception as e:
                st.error(f"❌ Произошла ошибка при выполнении исследования: {str(e)}")
                st.exception(e)
                st.stop()
        
        # Отображение результата (показывается после запуска агентов)
        if st.session_state.result:
            st.markdown("---")
            st.subheader(f"📝 Результат исследования: {st.session_state.last_topic}")
            
            # Отображаем результат в Markdown формате
            st.markdown(st.session_state.result)
            
            # Кнопка для скачивания результата
            st.download_button(
                label="📥 Скачать блог-пост",
                data=st.session_state.result,
                file_name=f"blog_post_{st.session_state.last_topic.replace(' ', '_') if st.session_state.last_topic else 'result'}.txt",
                mime="text/plain"
            )
            
            # Кнопка отправки в Telegram через webhook
            if st.button("📤 Отправить в Telegram"):
                if not webhook_url or webhook_url.strip() == "":
                    st.warning("⚠️ Пожалуйста, введите URL webhook в боковой панели")
                else:
                    try:
                        # Используем тему из session_state, если доступна, иначе из поля ввода
                        topic_to_send = st.session_state.last_topic if st.session_state.last_topic else (topic if topic else "Не указано")
                        response = requests.post(
                            webhook_url.strip(),
                            json={
                                "topic": topic_to_send,
                                "content": str(st.session_state.result)
                            },
                            timeout=10
                        )
                        if response.status_code == 200:
                            st.success("✅ Отправлено!")
                        else:
                            st.error(f"❌ Ошибка: статус {response.status_code}")
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ Ошибка отправки: {str(e)}")
        
            # Footer с инструкциями
            st.markdown("---")
            with st.expander("ℹ️ Инструкции"):
                st.markdown("""
                ### Как использовать:
                1. Введите тему для исследования в поле выше
                2. Нажмите кнопку "Запустить исследование"
                3. Дождитесь завершения (процесс может занять несколько минут)
                4. Результат отобразится на странице и будет сохранен в файл `blog_post.txt`
                
                ### Что делает приложение:
                - **Исследователь** ищет последние новости (1-2 недели) по заданной теме через Serper API
                - **Писатель** создает информативный блог-пост на русском языке на основе найденных новостей
                - Результат отображается в Markdown формате
                """)
    
    with tab2:
        st.markdown("---")
        st.subheader("📊 История созданных блог-постов")
        
        if not api_url or not api_url.strip():
            st.info("ℹ️ Для просмотра истории результатов укажите URL API сервера в боковой панели (Настройки → API Server URL)")
        else:
            # Кнопка обновления
            col1, col2 = st.columns([1, 4])
            with col1:
                refresh_button = st.button("🔄 Обновить", use_container_width=True)
            
            # Получаем данные
            if refresh_button or 'blog_posts_data' not in st.session_state:
                with st.spinner('⏳ Загрузка данных...'):
                    posts = get_blog_posts(api_url)
                    st.session_state.blog_posts_data = posts
            
            posts = st.session_state.get('blog_posts_data', [])
            
            if posts is None:
                st.error("❌ Ошибка при загрузке данных. Проверьте URL API сервера в настройках.")
            elif len(posts) == 0:
                st.info("📭 Пока нет созданных блог-постов. Создайте первый блог-пост во вкладке 'Создать блог-пост'.")
            else:
                st.success(f"✅ Найдено результатов: {len(posts)}")
                
                # Фильтр по теме
                filter_topic = st.text_input(
                    "🔍 Фильтр по теме",
                    placeholder="Введите тему для поиска...",
                    help="Отфильтровать результаты по теме"
                )
                
                # Фильтруем данные
                if filter_topic:
                    filtered_posts = [p for p in posts if filter_topic.lower() in p.get('topic', '').lower()]
                else:
                    filtered_posts = posts
                
                if len(filtered_posts) == 0:
                    st.info(f"🔍 По запросу '{filter_topic}' ничего не найдено.")
                else:
                    # Подготовка данных для таблицы
                    table_data = []
                    for post in filtered_posts:
                        table_data.append({
                            'ID': post.get('id', ''),
                            'Тема': post.get('topic', ''),
                            'Автор': post.get('author', 'Не указан'),
                            'Дата': post.get('date', 'Не указана'),
                            'Создано': post.get('created_at', '')[:19] if post.get('created_at') else '',
                            'Статус': post.get('status', '')
                        })
                    
                    # Отображаем таблицу
                    st.dataframe(
                        table_data,
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Детальный просмотр
                    st.markdown("---")
                    st.subheader("📄 Детальный просмотр")
                    
                    post_ids = [f"ID: {p['ID']} - {p['Тема']}" for p in table_data]
                    selected_post_str = st.selectbox(
                        "Выберите блог-пост для просмотра:",
                        post_ids
                    )
                    
                    if selected_post_str:
                        selected_post_id = int(selected_post_str.split(' - ')[0].replace('ID: ', ''))
                        selected_post = next((p for p in filtered_posts if p.get('id') == selected_post_id), None)
                        
                        if selected_post:
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Тема:** {selected_post.get('topic', '')}")
                                st.markdown(f"**Автор:** {selected_post.get('author', 'Не указан')}")
                            with col2:
                                st.markdown(f"**Дата:** {selected_post.get('date', 'Не указана')}")
                                st.markdown(f"**Создано:** {selected_post.get('created_at', '')[:19] if selected_post.get('created_at') else ''}")
                            
                            st.markdown("---")
                            st.markdown("**Содержание:**")
                            st.markdown(selected_post.get('content', ''))
                            
                            # Кнопка скачивания
                            st.download_button(
                                label="📥 Скачать блог-пост",
                                data=selected_post.get('content', ''),
                                file_name=f"blog_post_{selected_post.get('topic', 'post').replace(' ', '_')}_{selected_post.get('id', '')}.txt",
                                mime="text/plain"
                            )

if __name__ == '__main__':
    # #region agent log
    try:
        with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
            f.write(json.dumps({"id":"log_script_start","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:361","message":"Script started, calling main()","data":{"step":"script_entry"},"sessionId":"debug-session","runId":"run1","hypothesisId":"A"}) + "\n")
    except: pass
    # #endregion
    
    try:
        main()
        # #region agent log
        try:
            with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"id":"log_main_complete","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:367","message":"main() completed","data":{"step":"main_complete"},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
        except: pass
        # #endregion
    except Exception as e:
        # #region agent log
        try:
            with open('/Users/pavelkokora/crewai_agent/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"id":"log_main_exception","timestamp":int(datetime.now().timestamp()*1000),"location":"app.py:370","message":"Exception in main()","data":{"error":str(e),"traceback":traceback.format_exc()},"sessionId":"debug-session","runId":"run1","hypothesisId":"B"}) + "\n")
        except: pass
        # #endregion
        st.error(f"Критическая ошибка: {str(e)}")
        st.exception(e)
