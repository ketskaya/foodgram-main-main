# Generated by Django 3.2.16 on 2025-01-30 19:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0003_alter_user_username'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ingredient',
            options={'ordering': ['name'], 'verbose_name': 'ингредиент', 'verbose_name_plural': 'Ингредиенты'},
        ),
        migrations.RemoveConstraint(
            model_name='ingredient',
            name='unique_ingredient_measurement',
        ),
        migrations.AlterField(
            model_name='ingredient',
            name='name',
            field=models.CharField(max_length=128, unique=True, verbose_name='Название'),
        ),
    ]
