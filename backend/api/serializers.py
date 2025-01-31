from rest_framework import serializers
from collections import Counter
from recipes.models import (Ingredient, Recipe, RecipeIngredient, FavoriteRecipe, ShoppingCart)
from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField

User = get_user_model()


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
            return user.followers.filter(author=author).exists()
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


class SubscriptionRecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeSerializer(serializers.ModelSerializer):

    author = UsersSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(source='recipe_ingredients',
                                             many=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField(allow_null=True)
    cooking_time = serializers.IntegerField(min_value=1)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def validate_ingredients(self, ingredients):
        if not ingredients:
            raise serializers.ValidationError(
                'Необходимо добавить хотя бы один ингредиент.')
        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        duplicate_ingredients = [
            ingredient_id for ingredient_id,
            count in Counter(ingredient_ids).items() if count > 1
        ]

        if duplicate_ingredients:
            raise serializers.ValidationError(
                f'Ингредиенты с id {duplicate_ingredients} повторяются.')

        return ingredients

    def validate_image(self, image):
        if not image:
            raise serializers.ValidationError(
                'Необходимо добавить фото.')
        return image

    @staticmethod
    def save_ingredients(recipe, ingredients_data):
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
        ingredients_data = validated_data.pop('recipe_ingredients', None)
        validated_ingredients = self.validate_ingredients(ingredients_data)
        instance.recipe_ingredients.all().delete()
        self.save_ingredients(instance, validated_ingredients)
        return super().update(instance, validated_data)

    def get_is_favorited(self, recipe):
        user = self.context['request'].user
        if user.is_authenticated:
            return FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists()
        return False

    def get_is_in_shopping_cart(self, recipe):
        user = self.context['request'].user
        return user.is_authenticated and ShoppingCart.objects.filter(
            user=user, recipe=recipe).exists()


class UserWithRecipesSerializer(UsersSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit', 10)
        try:
            recipes_limit = int(recipes_limit)
        except ValueError:
            recipes_limit = 10
        return SubscriptionRecipeSerializer(
            obj.recipes.all()[:recipes_limit], many=True,
            context=self.context).data
