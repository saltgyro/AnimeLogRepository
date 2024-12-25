# Generated by Django 4.1 on 2024-12-25 08:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('anime_tracker', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='anime',
            name='genres',
            field=models.ManyToManyField(related_name='animes', through='anime_tracker.Anime_genres', to='anime_tracker.genres'),
        ),
        migrations.AddField(
            model_name='anime',
            name='seasons',
            field=models.ManyToManyField(related_name='animes', through='anime_tracker.Anime_seasons', to='anime_tracker.seasons'),
        ),
        migrations.AddField(
            model_name='anime',
            name='studios',
            field=models.ManyToManyField(related_name='animes', through='anime_tracker.Anime_studio', to='anime_tracker.studios'),
        ),
        migrations.AddField(
            model_name='anime',
            name='tags',
            field=models.ManyToManyField(related_name='animes', through='anime_tracker.Anime_tags', to='anime_tracker.tags'),
        ),
    ]
