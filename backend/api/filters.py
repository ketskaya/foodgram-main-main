from django.db.models import OuterRef, Exists
from django_filters import rest_framework
from recipes.models import ShoppingCart, FavoriteRecipe, Recipe


class RecipeFilter(rest_framework.FilterSet):
    is_in_shopping_cart = rest_framework.BooleanFilter(
        method='filter_is_in_shopping_cart')
    is_favorited = rest_framework.BooleanFilter(method='filter_is_favorited')

    class Meta:
        model = Recipe
        fields = ['name', 'author']

    def filter_is_in_shopping_cart(self, shoppingcart, name, value):
        if self.request.user.is_authenticated:
            if value:
                return shoppingcart.filter(
                    Exists(
                        ShoppingCart.objects.filter(
                            user=self.request.user,
                            recipe=OuterRef('pk')
                        )
                    )
                )
            else:
                return shoppingcart.exclude(
                    Exists(
                        ShoppingCart.objects.filter(
                            user=self.request.user,
                            recipe=OuterRef('pk')
                        )
                    )
                )
        return shoppingcart

    def filter_is_favorited(self, favorite, name, value):
        if self.request.user.is_authenticated:
            if value:
                return favorite.filter(
                    Exists(
                        FavoriteRecipe.objects.filter(
                            user=self.request.user,
                            recipe=OuterRef('pk')
                        )
                    )
                )
            else:
                return favorite.exclude(
                    Exists(
                        FavoriteRecipe.objects.filter(
                            user=self.request.user,
                            recipe=OuterRef('pk')
                        )
                    )
                )
        return favorite
