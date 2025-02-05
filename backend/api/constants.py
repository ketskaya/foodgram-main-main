# Константы для пагинации (pagination.py)
PAGE_SIZE = 6
MAX_PAGE_SIZE = 100
LIMIT_QUERY_PARAM = 'limit'

# Константы для рецептов (serializers.py)
MIN_COOKING_TIME = 1  # Минимальное время приготовления (в мин.)
MAX_COOKING_TIME = 600  # Максимальное время приготовления (в мин.)
MIN_INGREDIENT_AMOUNT = 1  # Минимальное количество ингредиента
MAX_INGREDIENT_AMOUNT = 1000  # Максимальное количество ингредиента
