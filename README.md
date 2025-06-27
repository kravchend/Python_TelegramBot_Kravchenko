# Проект: Telegram-бот с функцией календаря и веб-админкой на Django

**Автор:** Дмитрий Кравченко  
**GitHub:** [kravchend](https://github.com/kravchend)  
**E-mail:** kravchend@gmail.com

---

## Описание

Данный проект реализует Telegram-бота с календарём и заметками.  
Кроме Телеграм-бота, проект содержит полноценную веб-админку на Django для управления событиями и пользователями.  
Проект работает в Docker-контейнерах и использует базу данных PostgreSQL.

**Функционал бота и веб-интерфейса:**
- Просмотр событий календаря
- Добавление событий
- Получение напоминаний в Telegram
- Управление пользователями и событиями через админ-панель

---

## Структура проекта

- `calendarapp/` — Django-приложение, основная бизнес-логика
- `bot/` — исходный код Telegram-бота (aiogram)
- `Dockerfile.web` — сборка Django-приложения
- `Dockerfile.bot` — сборка Telegram-бота
- `docker-compose.yml` — запуск всех сервисов
- `.env` — переменные окружения для конфигурации сервиса

---

## Запуск в Docker

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/kravchend/Python_TelegramBot_Kravchenko.git
    cd Python_TelegramBot_Kravchenko
    ```

2. Создайте файл `.env` на основе `.env.example` и задайте значения переменных:
    - `BOT_TOKEN` — токен Telegram-бота
    - и остальные параметры подключения к базе (см. пример в `.env.example`)

3. Постройте и запустите проект:
    ```bash
    docker compose build
    docker compose up
    ```

4. В первом запуске создайте суперпользователя Django для доступа в админ-панель:
    ```bash
    docker compose exec web python manage.py createsuperuser
    ```

5. Перейдите в браузере по адресу [http://localhost:8000/admin/](http://localhost:8000/admin/) для веб-админки  
   и используйте Telegram-бота, отправляя команды на указанный при настройке аккаунт бота.

---

## Разработка без Docker (локально)

1. Установите Python 3.12+ и PostgreSQL.
2. Заполните `.env` и установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```
3. Проведите миграции и создайте суперпользователя Django:
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```
4. Запустите Django-сервер:
    ```bash
    python manage.py runserver
    ```
5. Запустите бота:
    ```bash
    PYTHONPATH=. python -m bot.bot
    ```

---

## Контакты

Вопросы и предложения: kravchend@gmail.com  
Telegram: [@kravchend](https://t.me/kravchend)