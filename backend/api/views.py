import base64
from rest_framework import viewsets, status
from rest_framework.permissions import (IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.exceptions import (PermissionDenied,
                                       ValidationError)
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from django.core.files.base import ContentFile
from rest_framework.filters import SearchFilter
from django.http import HttpResponse
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (Ingredient, Recipe, FavoriteRecipe, ShoppingCart,
                            User, Subscription)
from .serializers import (IngredientSerializer, RecipeSerializer,
                          UsersSerializer, UserWithRecipesSerializer)
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
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageToOffsetPagination
    filter_backends = (DjangoFilterBackend,)
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
        if is_favorited is not None:
            user = self.request.user
            if user.is_authenticated:
                if is_favorited in ['1', 'true']:
                    favorite_recipes = (
                        FavoriteRecipe.objects.filter(user=user)
                        .values('recipe')
                    )
                    queryset = queryset.filter(id__in=favorite_recipes)
                else:
                    favorite_recipes = (
                        FavoriteRecipe.objects.filter(user=user)
                        .values('recipe')
                    )
                    queryset = queryset.exclude(id__in=favorite_recipes)
        return queryset

    @staticmethod
    def handle_recipe_action(model, user, recipe, action_type):
        if action_type == 'add':
            obj, created = model.objects.get_or_create(
                user=user,
                recipe=recipe
            )
            if not created:
                raise ValidationError('Рецепт уже добавлен.')
            return Response({
                'id': recipe.id,
                'name': recipe.name,
                'image': recipe.image.url if recipe.image else None,
                'cooking_time': recipe.cooking_time
            }, status=status.HTTP_201_CREATED)
        elif action_type == 'remove':
            obj = model.objects.filter(user=user, recipe=recipe)
            if not obj.exists():
                raise ValidationError('Рецепт не найден.')
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(ShoppingCart, request.user, recipe,
                                         'add')

    @shopping_cart.mapping.delete
    def remove_from_shopping_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(ShoppingCart, request.user, recipe,
                                         'remove')

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(FavoriteRecipe, request.user, recipe,
                                         'add')

    @favorite.mapping.delete
    def remove_from_favorites(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        return self.handle_recipe_action(FavoriteRecipe, request.user, recipe,
                                         'remove')

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        return Response({'short-link': request.build_absolute_uri(
            reverse('recipe_redirect', args=[recipe.pk])
        )}, status=status.HTTP_200_OK)

    @action(detail=False, permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        shopping_cart = user.shopping_carts.all()
        if not shopping_cart.exists():
            return Response({'detail': 'Список покупок пуст.'},
                            status=status.HTTP_200_OK)

        shopping_list = 'Список покупок:\n\n'
        for item in shopping_cart:
            recipe = item.recipe
            shopping_list += (
                f'- {recipe.name} '
                f'(время приготовления: {recipe.cooking_time} мин.)\n'
            )

        response = HttpResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; '
            'filename="shopping_list.txt"'
        )
        return response

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("Вы не можете удалять чужие рецепты.")
        instance.delete()

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

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[IsAuthenticated])
    def subscribe(self, request, id=None):
        user = request.user
        author = self.get_object()
        if request.method == 'POST':
            if user == author:
                return Response(
                    {'error': 'Нельзя подписаться на самого себя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription, created = user.followers.get_or_create(author=author)
            if not created:
                return Response(
                    {'error': 'Вы уже подписаны на этого пользователя.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = UserWithRecipesSerializer(
                author, context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        try:
            subscription = user.followers.get(author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Subscription.DoesNotExist:
            raise ValidationError('Вы не подписаны на этого пользователя.')

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def subscriptions(self, request):
        queryset = User.objects.filter(authors__user=request.user)
        recipes_limit = request.query_params.get('recipes_limit')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True,
                context={'request': request, 'recipes_limit': recipes_limit}
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserWithRecipesSerializer(
            queryset, many=True,
            context={'request': request, 'recipes_limit': recipes_limit}
        )
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
            except ValueError:
                raise ValidationError(
                    'Недопустимый формат аватара. Ожидаемое - base64.'
                )
            ext = format.split('/')[-1]
            avatar_file = ContentFile(base64.b64decode(imgstr),
                                      name=f'avatar.{ext}')
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = avatar_file
            user.save()
            return Response({'avatar': user.avatar.url})
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)
