from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.contrib.auth.models import AbstractUser

from .constants import (MIN_COOKING_TIME, MIN_AMOUNT, MAX_EMAIL_LENGTH,
                        MAX_NAME_LENGTH, USERNAME_REGEX,
                        MAX_INGREDIENT_NAME_LENGTH,
                        MAX_MEASUREMENT_UNIT_LENGTH, MAX_RECIPE_NAME_LENGTH,
                        MAX_STR_LENGTH_FOR_DISPLAY)


class User(AbstractUser):

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    email = models.EmailField(
        'Адрес электронной почты',
        max_length=MAX_EMAIL_LENGTH,
        unique=True
    )
    username = models.CharField(
        'Логин',
        max_length=MAX_NAME_LENGTH,
        unique=True,
        validators=[
            RegexValidator(
                regex=USERNAME_REGEX,
                message=('Логин может содержать только буквы, '
                         'цифры и следующие символы: @/./+/-/_'
                         )
            )
        ],
    )
    first_name = models.CharField('Имя', max_length=MAX_NAME_LENGTH)
    last_name = models.CharField('Фамилия', max_length=MAX_NAME_LENGTH)
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        null=True,
        blank=True
    )
    recipes_favorited = models.ManyToManyField(
        'Recipe',
        through='FavoriteRecipe',
        related_name='favorited_by',
        verbose_name='Избранные рецепты',
        blank=True
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Пользователь'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authors',
        verbose_name='Автор'
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follows'
            )
        ]
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ('user',)

    def __str__(self):
        return f'{self.user} подписан на {self.author}'


class Ingredient(models.Model):
    name = models.CharField(max_length=MAX_INGREDIENT_NAME_LENGTH,
                            verbose_name='Название',
                            help_text='Введите название ингредиента')
    measurement_unit = models.CharField(
        max_length=MAX_MEASUREMENT_UNIT_LENGTH,
        verbose_name='Единица измерения',
        help_text='Введите единицу измерения ингредиента'
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['name', 'measurement_unit'],
                name='unique_ingredient_measurement'
            )
        ]

    def __str__(self):
        return self.name[:MAX_STR_LENGTH_FOR_DISPLAY]


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField('Название', max_length=MAX_RECIPE_NAME_LENGTH)
    image = models.ImageField('Картинка', upload_to='recipes/images/')
    text = models.TextField('Описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления',
        help_text='Укажите время в минутах',
        validators=(MinValueValidator(MIN_COOKING_TIME),)
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-created_at']

    def __str__(self):
        return self.name[:MAX_STR_LENGTH_FOR_DISPLAY]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        related_name='recipe_ingredients',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        related_name='recipe_ingredients',
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        'Количество',
        validators=(MinValueValidator(MIN_AMOUNT),)
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_recipe_ingredient'
            )
        ]
        verbose_name = 'Продукт рецепта'
        verbose_name_plural = 'Продукты рецепта'
        ordering = ['recipe', 'ingredient']

    def __str__(self):
        return (
            f'{self.recipe.name[:MAX_STR_LENGTH_FOR_DISPLAY]} - '
            f'{self.ingredient.name[:MAX_STR_LENGTH_FOR_DISPLAY]}'
        )


class BaseUserRecipeModel(models.Model):
    user = models.ForeignKey(
        User,
        related_name='%(class)s',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='%(class)s',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        ordering = ('-user',)

    def __str__(self):
        return (
            f'{self.user.username[:MAX_STR_LENGTH_FOR_DISPLAY]} добавил '
            f'{self.recipe.name[:MAX_STR_LENGTH_FOR_DISPLAY]}'
        )


class FavoriteRecipe(BaseUserRecipeModel):
    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite_recipes',
            ),
        )


class ShoppingCart(BaseUserRecipeModel):
    class Meta(BaseUserRecipeModel.Meta):
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shoppingcart_recipes',
            ),
        )
