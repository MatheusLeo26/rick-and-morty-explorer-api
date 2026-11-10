# Generated initial migration for explorer app

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FavoriteCharacter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.PositiveIntegerField(
                        db_index=True,
                        help_text="ID original do personagem na API pública de Rick and Morty.",
                        unique=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        db_index=True,
                        help_text="Nome do personagem.",
                        max_length=255,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        db_index=True,
                        help_text="Status de vida do personagem (Alive, Dead, unknown).",
                        max_length=50,
                    ),
                ),
                (
                    "species",
                    models.CharField(
                        db_index=True,
                        help_text="Espécie do personagem (ex: Human, Alien).",
                        max_length=100,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Subespécie ou tipo do personagem.",
                        max_length=150,
                    ),
                ),
                (
                    "gender",
                    models.CharField(
                        default="unknown",
                        help_text="Gênero do personagem (Female, Male, Genderless, unknown).",
                        max_length=50,
                    ),
                ),
                (
                    "origin_name",
                    models.CharField(
                        default="unknown",
                        help_text="Nome da origem do personagem.",
                        max_length=255,
                    ),
                ),
                (
                    "location_name",
                    models.CharField(
                        default="unknown",
                        help_text="Nome da última localização conhecida do personagem.",
                        max_length=255,
                    ),
                ),
                (
                    "image",
                    models.URLField(
                        blank=True,
                        default="",
                        help_text="URL da imagem/avatar do personagem.",
                        max_length=500,
                    ),
                ),
                (
                    "episode_urls",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Lista de URLs dos episódios em que o personagem aparece.",
                    ),
                ),
                (
                    "episode_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Quantidade total de episódios em que o personagem aparece.",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Observação opcional adicionada pelo usuário ao favoritar.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Personagem Favorito",
                "verbose_name_plural": "Personagens Favoritos",
                "ordering": ["-created_at", "external_id"],
            },
        ),
        migrations.CreateModel(
            name="FavoriteEpisode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "external_id",
                    models.PositiveIntegerField(
                        db_index=True,
                        help_text="ID original do episódio na API pública de Rick and Morty.",
                        unique=True,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        db_index=True,
                        help_text="Título do episódio.",
                        max_length=255,
                    ),
                ),
                (
                    "episode_code",
                    models.CharField(
                        db_index=True,
                        help_text="Código de temporada e episódio (ex: S01E01).",
                        max_length=50,
                    ),
                ),
                (
                    "air_date",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Data de exibição original do episódio.",
                        max_length=100,
                    ),
                ),
                (
                    "character_urls",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Lista de URLs dos personagens que participam do episódio.",
                    ),
                ),
                (
                    "character_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Quantidade de personagens que aparecem no episódio.",
                    ),
                ),
                (
                    "url",
                    models.URLField(
                        blank=True,
                        default="",
                        help_text="URL original do episódio na API pública.",
                        max_length=500,
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Observação opcional adicionada pelo usuário.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Episódio Favorito",
                "verbose_name_plural": "Episódios Favoritos",
                "ordering": ["episode_code", "external_id"],
            },
        ),
    ]
