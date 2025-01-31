import json
from django.core.management.base import BaseCommand
from recipes.models import Ingredient

class Command(BaseCommand):
    help = 'Загружает ингредиенты из JSON файла в базу данных'

    def handle(self, *args, **kwargs):
        try:
            with open('ingredients.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
                created_ingredients = []
                for item in data:
                    ingredient = Ingredient(
                        name=item['name'],
                        measurement_unit=item['measurement_unit']
                    )
                    created_ingredients.append(ingredient)

                Ingredient.objects.bulk_create(created_ingredients, ignore_conflicts=True)

            self.stdout.write(
                self.style.SUCCESS(f'Успешно добавлено {len(created_ingredients)} ингредиентов.')
            )
        except Exception as e:
            self.stderr.write(f'Произошла ошибка: {e}')
