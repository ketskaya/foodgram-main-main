# Foodgram

## Описание
**«Фудграм»** — это сайт, на котором пользователи будут публиковать свои рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Зарегистрированным пользователям также будет доступен сервис «Список покупок». Он позволит создавать список продуктов, которые нужно купить для приготовления выбранных блюд.

---

## Технологии
- Python 
- Django
- Django REST Framework
- Simple JWT
- PostgreSQL
- SQLite 
- Docker
- Docker Compose
- Nginx

---

## Запуск проекта

1. Клонируйте репозиторий:
   
   `git clone https://github.com/ketskaya/foodgram-main-main.git`

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

---

## Примеры запросов

### 1) POST-запрос: Регистрация пользователя

```
{
    "email": "user@example.com",
    "username": "new_user",
    "first_name": "Вася",
    "last_name": "Иванов",
    "password": "password123"
}
```

Ответ:
```
{
    "id": 1,
    "username": "new_user",
    "first_name": "Вася",
    "last_name": "Иванов",
    "email": "user@example.com"
}
```

### 2) GET-запрос: Получение списка рецептов

`GET /api/recipes/`

Ответ:
```
{
  "count": 2,
  "next": "http://127.0.0.1:8000/api/recipes/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "author": {
        "id": 1,
        "username": "new_user",
        "first_name": "Вася",
        "last_name": "Иванов",
        "email": "user@example.com",
        "is_subscribed": false,
        "avatar": null
      },
      "ingredients": [
        {
          "id": 1,
          "name": "Тесто для пиццы",
          "measurement_unit": "г",
          "amount": 500
        },
        {
          "id": 2,
          "name": "Ананас",
          "measurement_unit": "шт",
          "amount": 1
        }
      ],
      "is_favorited": false,
      "is_in_shopping_cart": false,
      "name": "Пицца с ананасами",
      "image": "http://127.0.0.1:8000/media/images/pizza_with_pineapple.jpg",
      "text": "Вкусная пицца с ананасами и ветчиной.",
      "cooking_time": 30
    },
    {
      "id": 2,
      "author": {
        "id": 2,
        "username": "another_user",
        "first_name": "Иван",
        "last_name": "Петров",
        "email": "anotheruser@example.com",
        "is_subscribed": true,
        "avatar": null
      },
      "ingredients": [
        {
          "id": 3,
          "name": "Шоколад",
          "measurement_unit": "г",
          "amount": 200
        },
        {
          "id": 4,
          "name": "Мука",
          "measurement_unit": "г",
          "amount": 250
        }
      ],
      "is_favorited": true,
      "is_in_shopping_cart": false,
      "name": "Шоколадный торт",
      "image": "http://127.0.0.1:8000/media/images/chocolate_cake.jpg",
      "text": "Нежный шоколадный торт с кремом.",
      "cooking_time": 60
    }
  ]
}
```

### 3) DELETE-запрос: Удаление аватара пользователя

`DELETE /api/users/me/avatar/`

Ответ:
```
Status Code:
204 No Content

Тело ответа:
{}
```

---

### Автор
Проект разработан:  
**Екатерина Бутрина**   
GitHub: [ketskaya](https://github.com/ketskaya)

