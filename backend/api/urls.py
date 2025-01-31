from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, RecipeViewSet, UserViewSet
from recipes.views import recipe_redirect_view

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet, basename='ingredients')
router.register(r'recipes', RecipeViewSet, basename='recipe')
router.register(r'users', UserViewSet, basename='users')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('djoser.urls.authtoken')),
    path('s/<int:short_id>/', recipe_redirect_view, name='recipe_redirect'),
    path('recipes/<int:pk>/get-link/', RecipeViewSet.as_view({'get': 'get_short_link'}), name='get_recipe_short_link'),
    path('users/<int:pk>/subscribe/', UserViewSet.as_view({'post': 'subscribe'}), name='subscribe'),
    path('users/<int:pk>/unsubscribe/', UserViewSet.as_view({'delete': 'unsubscribe'}), name='unsubscribe'),
    path('recipes/<int:pk>/favorite/', RecipeViewSet.as_view({'post': 'add_to_favorites'}), name='add_to_favorites'),
    path('users/subscriptions/', UserViewSet.as_view({'get': 'get_subscriptions'}), name='get_subscriptions'),
    path('users/me/avatar/', UserViewSet.as_view({'put': 'update_avatar'}), name='update_avatar'),
    path('recipes/<int:pk>/shopping_cart/', RecipeViewSet.as_view({
        'post': 'add_to_shopping_cart',
        'delete': 'remove_from_shopping_cart'
    }), name='shopping_cart'),
    path('recipes/download_shopping_cart/', RecipeViewSet.as_view({'get': 'download_shopping_cart'}), name='download_shopping_cart'),
    
]
