from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import PermissionDenied, NotFound
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework.filters import SearchFilter
from django.http import HttpResponse
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import Ingredient, Recipe, FavoriteRecipe, ShoppingCart, User, Subscription
from .serializers import IngredientSerializer, RecipeSerializer, UsersSerializer, SubscriptionRecipeSerializer

from .filters import RecipeFilter
from .pagination import PageToOffsetPagination


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all().order_by('name')
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    search_fields = ('^name',)

    def get_queryset(self):
        queryset = Ingredient.objects.all().order_by('name')
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.select_related("author").all()
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageToOffsetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        queryset = super().get_queryset()

        author_id = self.request.query_params.get('author_id', None)
        if author_id:
            queryset = queryset.filter(author__id=author_id)

        is_favorited = self.request.query_params.get('is_favorited', None)
        if is_favorited:
            user = self.request.user
            if is_favorited == '1':
                queryset = queryset.filter(favoriterecipe__user=user)
            elif is_favorited == '0':
                queryset = queryset.exclude(favoriterecipe__user=user)

        return queryset

    def handle_collection_action(self, request, recipe_id, model, collection_name, action_type):
        try:
            recipe = get_object_or_404(Recipe, pk=recipe_id)
        except Recipe.DoesNotExist:
            return Response({'detail': 'Рецепт не найден.'}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_authenticated:
            return Response({'detail': 'Необходима авторизация.'}, status=status.HTTP_401_UNAUTHORIZED)

        if action_type == 'add':
            if model.objects.filter(user=request.user, recipe=recipe).exists():
                return Response({'detail': f'Рецепт уже в {collection_name}.'}, status=status.HTTP_400_BAD_REQUEST)
            model.objects.create(user=request.user, recipe=recipe)
            return Response({'detail': f'Рецепт добавлен в {collection_name}.'}, status=status.HTTP_201_CREATED)

        elif action_type == 'remove':
            obj = model.objects.filter(user=request.user, recipe=recipe)
            if not obj.exists():
                return Response({'detail': f'Рецепт не найден в {collection_name}.'}, status=status.HTTP_400_BAD_REQUEST)
            obj.delete()
            return Response({'detail': f'Рецепт удалён из {collection_name}.'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['delete'], permission_classes=[IsAuthenticated])
    def delete_recipe(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        if recipe.author != request.user:
            return Response({'detail': 'Вы не можете удалить этот рецепт.'}, status=status.HTTP_403_FORBIDDEN)
        recipe.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_favorites(self, request, pk):
        return self.handle_collection_action(request, pk, FavoriteRecipe, 'избранное', 'add')

    @add_to_favorites.mapping.delete
    def remove_from_favorites(self, request, pk):
        try:
            if not request.user.is_authenticated:
                return Response({'detail': 'Необходима авторизация.'}, status=status.HTTP_401_UNAUTHORIZED)
            recipe = get_object_or_404(Recipe, pk=pk)
            favorite_item = FavoriteRecipe.objects.filter(user=request.user, recipe=recipe)
            if not favorite_item.exists():
                return Response({'detail': 'Рецепт не найден в избранном.'}, status=status.HTTP_400_BAD_REQUEST)
            favorite_item.delete()
            return Response({'detail': 'Рецепт удалён из избранного.'}, status=status.HTTP_204_NO_CONTENT)
        except Recipe.DoesNotExist:
            return Response({'detail': 'Рецепт не найден.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def add_to_shopping_cart(self, request, pk):
        return self.handle_collection_action(request, pk, ShoppingCart, 'список покупок', 'add')

    @add_to_shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'detail': 'Необходима авторизация.'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            recipe = get_object_or_404(Recipe, pk=pk)
        except Recipe.DoesNotExist:
            return Response({'detail': 'Рецепт не найден.'}, status=status.HTTP_404_NOT_FOUND)

        cart_item = ShoppingCart.objects.filter(user=request.user, recipe=recipe)
        if not cart_item.exists():
            return Response({'detail': 'Рецепт не найден в корзине.'}, status=status.HTTP_400_BAD_REQUEST)

        cart_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def download_shopping_list(self, request):
        shopping_cart = request.user.shopping_cart.all()
        if not shopping_cart.exists():
            return Response({'detail': 'Список покупок пуст.'}, status=status.HTTP_200_OK)

        shopping_list = 'Список покупок:\n\n'
        for item in shopping_cart:
            recipe = item.recipe
            shopping_list += f'- {recipe.name} (время приготовления: {recipe.cooking_time} мин.)\n'

        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly])
    def get_short_link(self, request, pk):
        short_link = request.build_absolute_uri(
            reverse('recipe_redirect', kwargs={'short_id': pk})
        )
        return Response({"short-link": short_link}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        recipe = self.get_object()
        if recipe.author != self.request.user:
            raise PermissionDenied("Вы не можете обновлять чужой рецепт.")
        serializer.save()

    def update(self, request, *args, **kwargs):
        recipe = self.get_object()
        if recipe.author != request.user:
            raise PermissionDenied("Вы не можете обновлять чужой рецепт.")
        return super().update(request, *args, **kwargs)


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated], url_path='profile')
    def get_profile(self, request, pk=None):
        user = get_object_or_404(User, pk=pk)
        is_subscribed = user.followers.filter(user=request.user).exists()
        user_data = {
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar': user.avatar.url if user.avatar else None,
            'is_subscribed': is_subscribed
        }
        return Response(user_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put', 'delete'], permission_classes=[IsAuthenticated], url_path='me/avatar')
    def update_avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            avatar = request.data.get('avatar')
            if not avatar:
                return Response({'avatar': 'Поле "avatar" обязательно.'}, status=status.HTTP_400_BAD_REQUEST)
            user.avatar = avatar
            user.save()
            return Response({'avatar': user.avatar.url}, status=status.HTTP_200_OK)

        if user.avatar:
            user.avatar.delete(save=True)
            user.avatar = None
            user.save()
        return Response({'avatar': None}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated], url_path='subscribe')
    def subscribe(self, request, pk):
        author = User.objects.filter(pk=pk).first()
        if not author:
            return Response({'detail': 'Пользователь не найден.'}, status=status.HTTP_404_NOT_FOUND)
        if author.id == request.user.id:
            return Response({'detail': 'Нельзя подписаться на себя.'}, status=status.HTTP_400_BAD_REQUEST)
        if Subscription.objects.filter(user=request.user, author=author).exists():
            return Response({'detail': 'Вы уже подписаны.'}, status=status.HTTP_400_BAD_REQUEST)
        Subscription.objects.create(user=request.user, author=author)
        recipes_limit = request.query_params.get('recipes_limit', 10)
        try:
            recipes_limit = int(recipes_limit)
        except ValueError:
            return Response({'detail': 'Некорректное значение для параметра recipes_limit.'}, status=status.HTTP_400_BAD_REQUEST)
        recipes = author.recipes.all()[:recipes_limit]
        recipes_data = SubscriptionRecipeSerializer(recipes, many=True, context=self.get_serializer_context()).data
        data = {
            'id': author.id,
            'username': author.username,
            'recipes': recipes_data,
        }
        return Response(data, status=status.HTTP_201_CREATED)


    @subscribe.mapping.delete
    def unsubscribe(self, request, pk):
        try:
            author = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'Пользователь не найден.'}, status=status.HTTP_400_BAD_REQUEST)
        subscription = Subscription.objects.filter(user=request.user, author=author)
        if not subscription.exists():
            return Response({'detail': 'Вы не подписаны на этого пользователя.'}, status=status.HTTP_400_BAD_REQUEST)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated], url_path='subscriptions')
    def get_subscriptions(self, request):
        subscriptions = Subscription.objects.filter(user=request.user)
        recipes_limit = request.query_params.get('recipes_limit', 10)
        try:
            recipes_limit = int(recipes_limit)
        except ValueError:
            return Response({'detail': 'Некорректное значение для параметра recipes_limit.'}, status=status.HTTP_400_BAD_REQUEST)

        paginator = PageToOffsetPagination()
        result_page = paginator.paginate_queryset(subscriptions, request)

        subscriptions_data = []
        for subscription in result_page:
            recipes = subscription.author.recipes.all()[:recipes_limit]
            recipes_data = SubscriptionRecipeSerializer(recipes, many=True, context=self.get_serializer_context()).data
            subscriptions_data.append({
                'author_id': subscription.author.id,
                'author_username': subscription.author.username,
                'recipes': recipes_data,
            })

        return paginator.get_paginated_response(subscriptions_data)

