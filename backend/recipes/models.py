from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.contrib.auth.models import AbstractUser

MIN_COOKING_TIME = 1
MIN_AMOUNT = 1


class User(AbstractUser):
    email = models.EmailField(
        'Адрес электронной почты',
        max_length=254,
        unique=True
    )
    username = models.CharField(
        'Логин',
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message=('Логин может содержать только буквы, '
                         'цифры и следующие символы: @/./+/-/_'
                         )
            )
        ],
    )
    first_name = models.CharField('Имя', max_length=150)
    last_name = models.CharField('Фамилия', max_length=150)
    avatar = models.ImageField(
        'Аватар',
        upload_to='avatars/',
        null=True,
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

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
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='authors',
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

    def __str__(self):
        return f'{self.user} подписан на {self.author}'


class Ingredient(models.Model):
    name = models.CharField(max_length=128, verbose_name='Название',
                            help_text='Введите название ингредиента')
    measurement_unit = models.CharField(
        max_length=64,
        verbose_name='Единица измерения',
        help_text='Введите единицу измерения ингредиента'
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField('Название', max_length=256)
    image = models.ImageField('Картинка', upload_to='recipes/images/')
    text = models.TextField('Описание')
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        related_name='recipes',
        verbose_name='Ингредиенты'
    )
    cooking_time = models.IntegerField(
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
        return self.name


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
        verbose_name='Продукт'
    )
    amount = models.IntegerField(
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


class FavoriteRecipe(models.Model):
    user = models.ForeignKey(
        User,
        related_name='favorites',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='favorites',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
        ordering = ('-user',)
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_favorite_recipes',
            ),
        )

    def __str__(self) -> str:
        return f'{self.user.username} добавил в избранное {self.recipe.name}'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        User,
        related_name='shopping_carts',
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        related_name='shopping_carts',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'корзина'
        verbose_name_plural = 'Корзина'
        ordering = ('-user',)
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_shoppingcart_recipes',
            ),
        )

    def __str__(self) -> str:
        return f'{self.user.username} добавил в корзину {self.recipe.name}'
