import time
import os
import undetected_chromedriver as uc
from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. Загрузка настроек
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

def get_job_description(url):
    """Заходит на страницу вакансии и забирает текст"""
    print("🚀 Запускаю браузер для чтения вакансии...")
    options = uc.ChromeOptions()
    # options.add_argument('--headless') # Пока с окном, чтобы видеть капчу
    driver = uc.Chrome(options=options)
    
    try:
        driver.get(url)
        print("⏳ Ждем 15 секунд (проходим защиту)...")
        time.sleep(15)
        
        try:
            # Пытаемся найти текст описания на Indeed
            description = driver.find_element(By.ID, 'jobDescriptionText').text
            title = driver.find_element(By.TAG_NAME, 'h1').text
            return title, description
        except:
            print("❌ Не удалось найти текст описания автоматически.")
            print("Совет: Скопируй текст вручную.")
            return None, None
    finally:
        driver.quit()

def generate_cover_letter(url, user_note):
    # 1. Читаем резюме
    try:
        with open("resume.txt", "r", encoding="utf-8") as f:
            resume = f.read()
    except:
        print("⚠️ Нет файла resume.txt!")
        return

    # 2. Получаем текст вакансии
    title, job_description = get_job_description(url)
    if not job_description:
        return

    print(f"\n🧠 Генерирую письмо для: {title}...")

    # 3. Промпт с учетом твоих пожеланий (Adjustable)
    llm = ChatOpenAI(model="gpt-5-mini", api_key=api_key)
    
    prompt = ChatPromptTemplate.from_template("""
    Ты — профессиональный консультант по карьере. Напиши Cover Letter (сопроводительное письмо) на английском языке.
    
    ДАННЫЕ:
    1. РЕЗЮМЕ КАНДИДАТА:
    {resume}
    
    2. ОПИСАНИЕ ВАКАНСИИ:
    {job_desc}
    
    3. ⚠️ ЛИЧНЫЙ КОММЕНТАРИЙ КАНДИДАТА (УЧТИ ОБЯЗАТЕЛЬНО):
    "{user_note}"
    
    ИНСТРУКЦИЯ:
    - Письмо должно быть кратким (3-4 абзаца), уверенным и профессиональным.
    - Не пересказывай резюме, а объясни, как опыт кандидата решает боли работодателя из описания.
    - Обязательно внедри идею из "Личного комментария кандидата".
    - Используй стандартную структуру Cover Letter.
    """)
    
    chain = prompt | llm | StrOutputParser()
    
    letter = chain.invoke({
        "resume": resume,
        "job_desc": job_description,
        "user_note": user_note
    })
    
    # 4. Сохраняем результат
    filename = f"Letter_{title.replace(' ', '_')[:20]}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(letter)
        
    print(f"\n✅ ГОТОВО! Письмо сохранено в файл: {filename}")
    print("-" * 30)
    print(letter)
    print("-" * 30)

if __name__ == "__main__":
    # Интерактивный ввод
    print("\n📝 ГЕНЕРАТОР COVER LETTER")
    target_url = input("🔗 Вставь ссылку на вакансию (Indeed): ").strip()
    
    print("\n💡 ЧТО ДОБАВИТЬ ОТ СЕБЯ? (Например: 'Я быстро учусь', 'Есть опыт с пищевым оборудованием')")
    custom_note = input("✍️ Твой комментарий (Enter, если пусто): ").strip()
    
    if not custom_note:
        custom_note = "Подчеркни высокую мотивацию и готовность работать в смены."
        
    generate_cover_letter(target_url, custom_note)