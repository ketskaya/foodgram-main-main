import base64

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserSerializer

from recipes.models import (Ingredient, Recipe, RecipeIngredient,
                            FavoriteRecipe, ShoppingCart, Subscription)
from .constants import MIN_COOKING_TIME, MAX_COOKING_TIME

User = get_user_model()


class Base64ImageField(serializers.ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,') 
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class UsersSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=False, allow_null=True, default=None)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, author):
        user = self.context['request'].user
        if user.is_authenticated:
            has_subscription = user.followers.filter(author=author).exists()
            return has_subscription
        return False


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        fields = '__all__'
        model = Ingredient


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    author = UsersSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipe_ingredients',
                                             many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(allow_null=True)
    cooking_time = serializers.IntegerField(min_value=MIN_COOKING_TIME,
                                            max_value=MAX_COOKING_TIME)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def validate(self, data):
        ingredients_data = data.get('recipe_ingredients', [])
        if not ingredients_data:
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы один ингредиент.'
            )
        ingredient_ids = [ingredient['id'] for ingredient in ingredients_data]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не могут повторяться.'
            )
        image = data.get('image', None)
        if not image:
            raise serializers.ValidationError('Необходимо добавить фото.')
        return data

    def save_ingredients(self, recipe, ingredients_data):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient.get('amount')
            )
            for ingredient in ingredients_data
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        recipe = super().create(validated_data)
        self.save_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients')
        self.save_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def get_is_favorited(self, recipe):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and user.favoriterecipe.filter(recipe=recipe).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        user = self.context['request'].user
        return (
            user.is_authenticated
            and user.shoppingcart.filter(recipe=recipe).exists()
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        print(f"Результат сериализации: {representation}")
        representation['is_favorited'] = self.get_is_favorited(instance)
        representation['is_in_shopping_cart'] = (self.get_is_in_shopping_cart(instance))
        return representation

class SubscriptionSerializer(serializers.ModelSerializer):
    author = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = Subscription
        fields = ['author', 'user']

    def validate_author(self, value):
        if self.context['request'].user == value:
            raise serializers.ValidationError('Нельзя подписаться на самого себя.')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        author = validated_data['author']
        existing_subscription = Subscription.objects.filter(user=user, author=author).first()
        if existing_subscription:
            return existing_subscription
        subscription = Subscription.objects.create(user=user, author=author)
        return subscription


class SubscriptionDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = ['author']
    def validate(self, attrs):
        user = self.context['request'].user
        author = attrs.get('author')
        if not user.followers.filter(author=author).exists():
            raise serializers.ValidationError(
                'Вы не подписаны на этого пользователя.'
            )
        return attrs
    def save(self):
        user = self.context['request'].user
        author = self.validated_data['author']
        subscription = user.followers.get(author=author)
        subscription.delete()


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class UserWithRecipesSerializer(UsersSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)

    class Meta:
        model = User
        fields = UsersSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )

    def get_recipes(self, obj): 
        request = self.context.get('request') 
        recipes_limit = request.query_params.get('recipes_limit', 10**10)
        return SubscriptionRecipeSerializer( 
            obj.recipes.all()[:int(recipes_limit)], many=True,
            context=self.context).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['recipes'] = self.get_recipes(instance)
        representation['recipes_count'] = instance.recipes.count()
        if 'subscription' in representation:
            del representation['subscription']
        return representation


class FavoriteRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = FavoriteRecipe
        fields = ('user', 'recipe')

    def validate(self, attrs):
        if FavoriteRecipe.objects.filter(user=attrs['user'],
                                         recipe=attrs['recipe']).exists():
            raise ValidationError('Рецепт уже добавлен в избранное.')
        return attrs


class ShoppingCartSerializer(serializers.ModelSerializer):

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')

    def validate(self, attrs):
        if ShoppingCart.objects.filter(user=attrs['user'],
                                       recipe=attrs['recipe']).exists():
            raise ValidationError('Рецепт уже добавлен в корзину покупок.')
        return attrs
