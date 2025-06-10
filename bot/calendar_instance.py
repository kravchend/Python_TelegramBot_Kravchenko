import psycopg2
import os
from dotenv import load_dotenv
from bot.mycalendar import Calendar

load_dotenv()


def get_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DATABASE_HOST", "localhost"),
            database=os.getenv("DATABASE_NAME", "ваша_база"),
            user=os.getenv("DATABASE_USER", "ваш_логин"),
            password=os.getenv("DATABASE_PASSWORD", "ваш_пароль"),
            port=os.getenv("DATABASE_PORT", 5432)
        )

    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        raise


conn = get_connection()
calendar = Calendar(conn)
