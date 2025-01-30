from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.filters import SearchFilter
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from recipes.models import Ingredient, Recipe, FavoriteRecipe, ShoppingCart
from .serializers import IngredientSerializer, RecipeSerializer, RecipeCreateUpdateSerializer, UserSerializer
from .pagination import LimitPagination
from .filters import RecipeFilter

User = get_user_model()


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    pagination_class = LimitPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticatedOrReadOnly()]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_favorites(self, request, id):
        recipe = get_object_or_404(Recipe, pk=id)
        _, created = FavoriteRecipe.objects.get_or_create(user=request.user, recipe=recipe)
        if created:
            return Response(status=status.HTTP_201_CREATED)
        return Response({'detail': 'Рецепт уже в избранном.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_shopping_cart(self, request, id):
        recipe = get_object_or_404(Recipe, pk=id)
        _, created = ShoppingCart.objects.get_or_create(user=request.user, recipe=recipe)
        if created:
            return Response(status=status.HTTP_201_CREATED)
        return Response({'detail': 'Рецепт уже в списке покупок.'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_list(self, request):
        shopping_cart = request.user.shopping_cart.all()
        if not shopping_cart.exists():
            return Response({'detail': 'Список покупок пуст.'}, status=status.HTTP_400_BAD_REQUEST)
        shopping_list = 'Список покупок:\n\n'
        for item in shopping_cart:
            shopping_list += f'- {item.recipe.name} ({item.recipe.cooking_time} мин.)\n'
        return Response({'shopping_list': shopping_list}, status=status.HTTP_200_OK)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = (DjangoFilterBackend, SearchFilter)
    search_fields = ['^name']

    def get_queryset(self):
        queryset = Ingredient.objects.all().order_by('name')
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
