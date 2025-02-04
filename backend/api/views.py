import base64
from collections import Counter

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework.filters import SearchFilter
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from djoser.views import UserViewSet as DjoserUserViewSet

from recipes.models import (Ingredient, Recipe, FavoriteRecipe, ShoppingCart,
                            User, Subscription)
from .filters import RecipeFilter
from .pagination import PageToOffsetPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (IngredientSerializer, RecipeSerializer,
                          UsersSerializer, UserWithRecipesSerializer,
                          ShoppingCartSerializer, FavoriteRecipeSerializer,
                          SubscriptionSerializer, SubscriptionDeleteSerializer)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    search_fields = ('^name',)

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name', None)
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset.order_by('name')


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.select_related("author").all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = PageToOffsetPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        return RecipeSerializer

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            raise AuthenticationFailed(
                'Вы должны быть авторизованы для создания рецепта.'
            )
        print("Переданные данные для создания рецепта:",
              serializer.validated_data)
        serializer.save(author=user)

    @staticmethod
    def handle_recipe_action(model, user, recipe, action_type,
                             serializer_class):
        serializer = serializer_class(data={'user': user.id,
                                            'recipe': recipe.id})
        if action_type == 'add':
            if not serializer.is_valid():
                raise ValidationError(serializer.errors)
            serializer.save()
            return Response({
                'id': recipe.id,
                'name': recipe.name,
                'image': recipe.image.url if recipe.image else None,
                'cooking_time': recipe.cooking_time
            }, status=status.HTTP_201_CREATED)
        elif action_type == 'remove':
            instance = model.objects.filter(user=user, recipe=recipe).first()
            if not instance:
                return Response(
                    {'detail': 'Рецепт не найден в корзине.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(ShoppingCart, request.user, recipe,
                                         'add', ShoppingCartSerializer)

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(ShoppingCart, request.user, recipe,
                                         'remove', ShoppingCartSerializer)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(FavoriteRecipe, request.user, recipe,
                                         'add', FavoriteRecipeSerializer)

    @favorite.mapping.delete
    def remove_from_favorites(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(FavoriteRecipe, request.user, recipe,
                                         'remove', FavoriteRecipeSerializer)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        return Response({'short-link': request.build_absolute_uri(
            reverse('recipe_redirect', args=[recipe.pk])
        )}, status=status.HTTP_200_OK)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart = user.shoppingcart.all()
        if not shopping_cart.exists():
            return Response({'detail': 'Список покупок пуст.'},
                            status=status.HTTP_200_OK)

        shopping_list = self.generate_shopping_cart_text(shopping_cart)
        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    def generate_shopping_cart_text(self, shopping_cart):
        ingredients_counter = Counter()
        for item in shopping_cart:
            recipe = item.recipe
            for recipe_ingredient in recipe.recipe_ingredients.all():
                ingredient = recipe_ingredient.ingredient
                ingredients_counter[ingredient.name] += (
                    recipe_ingredient.amount
                )
        shopping_list = 'Список покупок:\n\n'
        for ingredient_name, total_amount in ingredients_counter.items():
            shopping_list += f'- {ingredient_name}: {total_amount} шт.\n'
        return shopping_list


class UserViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    serializer_class = UsersSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        author = self.get_object()
        if request.method == 'POST':
            if Subscription.objects.filter(user=request.user,
                                           author=author).exists():
                user_data = UserWithRecipesSerializer(
                    author, context={'request': request}
                ).data
                return Response(user_data, status=status.HTTP_400_BAD_REQUEST)
            serializer = SubscriptionSerializer(
                data={'author': author.id, 'user': request.user.id},
                context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                user_data = UserWithRecipesSerializer(
                    author, context={'request': request}
                ).data
                return Response(user_data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)
        if request.method == 'DELETE':
            serializer = SubscriptionDeleteSerializer(
                data={'author': author.id}, context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(authors__user=request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = UserWithRecipesSerializer(queryset, many=True,
                                               context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar',
            permission_classes=[IsAuthenticated])
    def avatar(self, request):
        user = request.user
        if request.method == 'PUT':
            avatar_data = request.data.get('avatar')
            if not avatar_data:
                raise ValidationError('Требуются данные для аватара.')
            try:
                format, imgstr = avatar_data.split(';base64,')
                ext = format.split('/')[-1]
            except ValueError:
                raise ValidationError(
                    'Недопустимый формат аватара. Ожидаемое - base64.'
                )
            try:
                avatar_file = ContentFile(base64.b64decode(imgstr),
                                          name=f'avatar.{ext}')
            except Exception as e:
                raise ValidationError(f"Ошибка при загрузке аватара: {str(e)}")
            if user.avatar:
                user.avatar.delete(save=False)

            user.avatar = avatar_file
            user.save()
            return Response({'avatar': user.avatar.url})
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
