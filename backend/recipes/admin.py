from django.contrib import admin
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .models import Ingredient, Recipe, Subscription, RecipeIngredient, ShoppingCart, FavoriteRecipe

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'get_full_name', 'email', 'avatar_preview', 'recipe_total', 'following_count', 'followers_count')
    search_fields = ('username', 'email')
    list_filter = ('is_active', 'is_staff')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'email', 'avatar')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}), 
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions')

    @admin.display(description='ФИО')
    def get_full_name(self, user) -> str:
        return f'{user.first_name} {user.last_name}'

    @admin.display(description='Аватар')
    @mark_safe
    def avatar_preview(self, user) -> str:
        return f'<img src="{getattr(user.avatar, "url", "")}" style="width: 40px; height: 40px; border-radius: 50%;">' if user.avatar else ''

    @admin.display(description='Количество рецептов')
    def recipe_total(self, user) -> int:
        return user.recipes_list.count()

    @admin.display(description='Подписки')
    def following_count(self, user) -> int:
        return user.subscriptions.count()

    @admin.display(description='Подписчики')
    def followers_count(self, user) -> int:
        return user.followers.count()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'author__username')
    list_filter = ('user', 'author')


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


class CookingTimeCategory(admin.SimpleListFilter):
    title = 'Категории по времени'
    parameter_name = 'cooking_duration'

    def lookups(self, request, model_admin):
        times = Recipe.objects.values_list('cooking_time', flat=True)
        if not times:
            return []
        
        sorted_times = sorted(set(times))
        third = len(sorted_times) // 3
        low, mid, high = sorted_times[third], sorted_times[2 * third], sorted_times[-1]

        return [
            ('short', f'До {low} мин'),
            ('medium', f'{low} - {mid} мин'),
            ('long', f'Более {mid} мин'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'short':
            return queryset.filter(cooking_time__lt=self.low)
        if self.value() == 'medium':
            return queryset.filter(cooking_time__range=(self.low, self.mid))
        if self.value() == 'long':
            return queryset.filter(cooking_time__gt=self.mid)
        return queryset


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cooking_time', 'author', 'get_favorite_count', 'show_ingredients_list', 'preview_image')
    search_fields = ('name', 'author__username')
    list_filter = (CookingTimeCategory, 'author')
    inlines = (RecipeIngredientInline,)
    readonly_fields = ('get_favorite_count',)

    @admin.display(description='Ингредиенты')
    @mark_safe
    def show_ingredients_list(self, recipe) -> str:
        return '<br>'.join(
            f'{ri.ingredient.name} - {ri.amount} {ri.ingredient.measurement_unit}'
            for ri in recipe.recipe_ingredients.all()
        )

    @admin.display(description='Изображение')
    @mark_safe
    def preview_image(self, recipe) -> str:
        return f'<img src="{recipe.image.url}" width="100" height="100" style="border-radius: 8px;">' if recipe.image else ''

    @admin.display(description='В избранном')
    def get_favorite_count(self, recipe) -> int:
        return FavoriteRecipe.objects.filter(recipe=recipe).count()


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    list_filter = ('user', 'recipe')


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass