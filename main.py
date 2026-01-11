import cloudscraper # Заменили requests на cloudscraper
from bs4 import BeautifulSoup
import sqlite3
import logging
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. Загрузка окружения
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
tg_token = os.getenv("TELEGRAM_TOKEN")
tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")

# 2. Логирование
logging.basicConfig(
    filename='system_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 3. Функция Telegram
def send_telegram_msg(text):
    import requests # Оставляем для отправки в ТГ
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    params = {"chat_id": tg_chat_id, "text": text}
    try:
        requests.get(url, params=params)
    except Exception as e:
        logging.error(f"Ошибка Telegram: {e}")

# 4. Функция AI (LangChain + GPT-5 Mini)
def get_skills_with_langchain(job_title):
    llm = ChatOpenAI(model="gpt-5-mini", api_key=api_key)
    prompt = ChatPromptTemplate.from_template(
        "Ты — технический рекрутер. Выдели 3 навыка для: {job_title}. Ответ дай строго через запятую."
    )
    chain = prompt | llm | StrOutputParser()
    try:
        return chain.invoke({"job_title": job_title})
    except Exception as e:
        logging.error(f"Ошибка LangChain: {e}")
        return "Навыки не определены"

# --- ОСНОВНАЯ ЛОГИКА ---
logging.info("Система запущена на Indeed...")

# Создаем скрейпер, который обходит защиту Cloudflare
scraper = cloudscraper.create_scraper()

# URL для Indeed Canada (Machine Operator в BC)
url = "https://ca.indeed.com/jobs?q=machine+operator&l=British+Columbia"

# Имитируем реальный браузер более детально
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9'
}

try:
    response = scraper.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # На Indeed заголовки обычно находятся в h2 с классом jobTitle
        # Мы вытаскиваем текст из вложенных span или a
        job_cards = soup.select('h2.jobTitle span[title]')
        
        conn = sqlite3.connect('jobs.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE,
                required_skills TEXT,
                date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        new_count = 0
        for card in job_cards:
            title = card.get('title') or card.text.strip()
            
            # Базовая фильтрация
            if not title or len(title) < 3:
                continue
                
            cursor.execute('SELECT id FROM vacancies WHERE title = ?', (title,))
            if cursor.fetchone() is None:
                skills = get_skills_with_langchain(title)
                cursor.execute('INSERT INTO vacancies (title, required_skills) VALUES (?, ?)', (title, skills))
                conn.commit()
                
                send_telegram_msg(f"🚀 [Indeed] Новая вакансия!\n\n📌 {title}\n\n🛠 Навыки: {skills}")
                logging.info(f"Добавлено с Indeed: {title}")
                new_count += 1

        print(f"Поиск завершен. Найдено новых: {new_count}")
        conn.close()
    else:
        logging.error(f"Indeed отклонил запрос: {response.status_code}")
        print(f"Ошибка доступа к Indeed: {response.status_code}")
        
except Exception as e:
    logging.error(f"Глобальная ошибка скрейпера: {e}")