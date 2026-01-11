from fastapi import FastAPI
import sqlite3

app = FastAPI()

@app.get("/jobs")
def get_jobs():
    conn = sqlite3.connect('jobs.db')
    cursor = conn.cursor()
    cursor.execute("SELECT title, required_skills FROM vacancies")
    rows = cursor.fetchall()
    conn.close()
    
    # Превращаем данные в удобный список словарей
    return [{"title": r[0], "skills": r[1]} for r in rows]

# Запуск: uvicorn api:app --reload