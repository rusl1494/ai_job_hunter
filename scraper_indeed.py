import time
import sqlite3
import os
import requests
import sys
import html
import re  # Для надежного парсинга
import undetected_chromedriver as uc
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# --- 1. КОНФИГУРАЦИЯ И FAIL FAST ---
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
tg_token = os.getenv("TELEGRAM_TOKEN")
tg_chat_id = os.getenv("TELEGRAM_CHAT_ID")

if not api_key:
    print("❌ ОШИБКА: Не найден OPENAI_API_KEY в .env")
    sys.exit(1)
if not tg_token or not tg_chat_id:
    print("❌ ОШИБКА: Не настроен Telegram в .env")
    sys.exit(1)

# --- 2. ГЛОБАЛЬНЫЕ РЕСУРСЫ ---
try:
    with open("resume.txt", "r", encoding="utf-8") as f:
        MY_RESUME = f.read()
except:
    print("⚠️ resume.txt не найден, использую заглушку.")
    MY_RESUME = "Machine Operator, 5 years experience."

print("🧠 Инициализация AI...", flush=True)
# Создаем один раз, чтобы не терять время в цикле
llm = ChatOpenAI(model="gpt-5-mini", api_key=api_key, temperature=0)

prompt_template = ChatPromptTemplate.from_template("""
Ты — HR. Сравни вакансию и резюме.
РЕЗЮМЕ: {resume}
ВАКАНСИЯ: {title}
ОПИСАНИЕ: {description}

1. Оцени (0-100%).
2. Чего нет в резюме (3 пункта).
Ответ: Score: [число] | Missing: [текст]
""")

global_chain = prompt_template | llm | StrOutputParser()

# --- 3. ФУНКЦИИ-ПОМОЩНИКИ ---

def send_tg(text):
    """Отправка в Telegram с защитой от сбоев"""
    url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
    params = {
        "chat_id": tg_chat_id, 
        "text": text, 
        "parse_mode": "HTML", 
        "disable_web_page_preview": "true"
    }
    try:
        requests.get(url, params=params, timeout=10)
    except Exception as e:
        print(f"⚠️ Ошибка отправки TG: {e}")

def analyze_vacancy_deep(title, description):
    """Вызов глобальной цепочки"""
    try:
        return global_chain.invoke({
            "title": title, 
            "description": description[:3000], 
            "resume": MY_RESUME
        })
    except Exception as e:
        return f"Score: 0 | Missing: Ошибка AI {e}"

def parse_ai_response(text):
    """
    Парсинг ответа AI с помощью Regex (защита от кривого формата)
    """
    # Ищем число после слова Score
    score_match = re.search(r'Score\D*(\d+)', text, re.IGNORECASE)
    score = int(score_match.group(1)) if score_match else 0

    # Ищем текст навыков
    if '|' in text:
        missing = text.split('|', 1)[1]
    elif 'Missing:' in text:
        missing = text.split('Missing:', 1)[1]
    else:
        missing = text # Если совсем плохо, возвращаем всё

    # Чистим мусор
    missing = missing.replace("Missing:", "").strip()
    return score, missing

# --- 4. ОСНОВНАЯ ЛОГИКА ---

def run_scraper():
    print("🚀 ЗАПУСК СКРЕЙПЕРА...", flush=True)
    options = uc.ChromeOptions()
    
    # ПРОВЕРКА: Мы в Докере или нет?
    if os.getenv("IN_DOCKER") == "true":
        print("🐳 Запуск внутри Docker (Headless + Stealth)...")
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument("--window-size=1920,1080")
        # МАСКИРОВКА: Притворяемся обычным браузером
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    else:
        pass 

    driver = uc.Chrome(options=options, version_main=None)
    
    try:
        url = "https://ca.indeed.com/jobs?q=machine+operator&l=British+Columbia"
        print(f"🌍 Переход на: {url}", flush=True)
        driver.get(url)
        
        print("⏳ Ждем 20 сек (Cloudflare)...", flush=True)
        time.sleep(20) # Увеличили время для надежности
        
        conn = sqlite3.connect('jobs.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vacancies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE,
            title TEXT,
            company TEXT,
            missing_skills TEXT,
            score INTEGER,
            date_found TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Поиск карточек
        cards = driver.find_elements(By.CSS_SELECTOR, 'div.job_seen_beacon')
        if not cards: 
            cards = driver.find_elements(By.CSS_SELECTOR, 'td.resultContent')
        
        print(f"✅ Найдено вакансий: {len(cards)}", flush=True)

        # 📸 ФОТО-ОТЧЕТ ЕСЛИ ПУСТО
        if len(cards) == 0:
            print("⚠️ ПУСТО! Делаю скриншот debug_docker.png...", flush=True)
            driver.save_screenshot("debug_docker.png")
            print("📸 Скриншот сохранен. Проверь папку проекта!")
            
            # Сохраняем HTML для анализа
            with open("debug_docker.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

        count_new = 0
        # ... (дальше твой цикл for card in cards без изменений) ...
        for card in cards:
            # Вставь сюда старый код цикла обработки карточек
            # (Я его не дублирую, чтобы не занимать место, он был правильным)
            try:
                # --- ШАГ 1: СБОР БАЗОВЫХ ДАННЫХ ---
                try:
                    link_el = card.find_element(By.CSS_SELECTOR, 'a.jcs-JobTitle')
                except:
                    link_el = card.find_element(By.TAG_NAME, 'a')
                
                title = link_el.text
                job_url = link_el.get_attribute('href')
                
                try:
                    company = card.find_element(By.CSS_SELECTOR, 'span[data-testid="company-name"]').text
                except:
                    company = "Unknown"

                # --- ШАГ 2: ПРОВЕРКА ДУБЛЕЙ ---
                cursor.execute('SELECT id FROM vacancies WHERE url = ?', (job_url,))
                if cursor.fetchone():
                    print(f"♻️ Уже в базе: {title}")
                    continue

                # --- ШАГ 3: КЛИК И ОЖИДАНИЕ ---
                driver.execute_script("arguments[0].scrollIntoView();", card)
                link_el.click()
                
                try:
                    desc_el = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.ID, 'jobDescriptionText'))
                    )
                    desc = desc_el.text
                except:
                    print(f"⚠️ Описание не загрузилось: {title}")
                    desc = ""

                # --- ШАГ 4: АНАЛИЗ ---
                print(f"🧠 Анализ: {title}...", flush=True)
                analysis = analyze_vacancy_deep(title, desc)
                score, missing = parse_ai_response(analysis)

                # --- ШАГ 5: СОХРАНЕНИЕ ---
                cursor.execute('''INSERT INTO vacancies 
                    (url, title, company, missing_skills, score) 
                    VALUES (?, ?, ?, ?, ?)''', 
                    (job_url, title, company, missing, score))
                conn.commit()
                count_new += 1

                # --- ШАГ 6: УВЕДОМЛЕНИЕ ---
                if score >= 75:
                    safe_title = html.escape(title)
                    safe_company = html.escape(company)
                    safe_missing = html.escape(missing)

                    msg = (
                        f"🔥 <b>{safe_title} ({score}%)</b>\n"
                        f"🏢 <i>{safe_company}</i>\n"
                        f"⚠️ Не хватает: {safe_missing}\n\n"
                        f"🔗 <a href='{job_url}'>Посмотреть на Indeed</a>"
                    )
                    send_tg(msg)
                    print(f"📤 Отправлено: {title}")
                else:
                    print(f"📉 Рейтинг {score}%: {title}")

            except Exception as e:
                print(f"❌ Сбой: {e}")
                continue
        
        print(f"🏁 Готово. Новых вакансий: {count_new}")
        conn.close()

    finally:
        print("🛑 Завершение работы...")
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    run_scraper()