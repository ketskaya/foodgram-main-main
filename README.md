# Foodgram

## Описание
**«Фудграм»** — это сайт, на котором пользователи будут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

---

## Запуск проекта

1. Клонируйте репозиторий:
   
   `git clone https://github.com/ketskaya/foodgram.git`

2. Перейдите в директорию `infra`:
   
   `cd foodgram-st/infra`

3. Создайте файл .env на основе .env.example:
   
   `cp .env.example .env`

4. Запустите проект с помощью Docker Compose:
   
   `docker-compose up`

5. Выполните миграции:
    
   `docker compose exec backend python manage.py migrate`

6. Заполните базу данными:
    
   `docker-compose exec backend python manage.py load_ingredients`
