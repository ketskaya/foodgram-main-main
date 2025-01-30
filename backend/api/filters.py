import django_filters
from recipes.models import Recipe


class RecipeFilter(django_filters.FilterSet):
    is_favorited = django_filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = django_filters.BooleanFilter(method='filter_is_in_shopping_cart')

    class Meta:
        model = Recipe
        fields = ['author', 'ingredients']

    def filter_is_favorited(self, recipes, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            return recipes.filter(favorited_by__user=user)
        return recipes

    def filter_is_in_shopping_cart(self, recipes, name, value):
        user = self.request.user
        if user.is_authenticated and value:
            return recipes.filter(in_shopping_cart__user=user)
        return recipes
