"""
Database models for persisting favorite characters and episodes locally in SQLite.
Stores essential fields from the public API so favorites remain accessible
even when the external Rick and Morty API is unavailable.
"""
from django.db import models


class FavoriteCharacter(models.Model):
    """
    Represents a favorite character saved locally in SQLite.
    """

    external_id = models.PositiveIntegerField(
        unique=True,
        db_index=True,
        help_text="ID original do personagem na API pública de Rick and Morty.",
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Nome do personagem.",
    )
    status = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Status de vida do personagem (Alive, Dead, unknown).",
    )
    species = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Espécie do personagem (ex: Human, Alien).",
    )
    type = models.CharField(
        max_length=150,
        blank=True,
        default="",
        help_text="Subespécie ou tipo do personagem.",
    )
    gender = models.CharField(
        max_length=50,
        default="unknown",
        help_text="Gênero do personagem (Female, Male, Genderless, unknown).",
    )
    origin_name = models.CharField(
        max_length=255,
        default="unknown",
        help_text="Nome da origem do personagem.",
    )
    location_name = models.CharField(
        max_length=255,
        default="unknown",
        help_text="Nome da última localização conhecida do personagem.",
    )
    image = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL da imagem/avatar do personagem.",
    )
    episode_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de URLs dos episódios em que o personagem aparece.",
    )
    episode_count = models.PositiveIntegerField(
        default=0,
        help_text="Quantidade total de episódios em que o personagem aparece.",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Observação opcional adicionada pelo usuário ao favoritar.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "external_id"]
        verbose_name = "Personagem Favorito"
        verbose_name_plural = "Personagens Favoritos"

    def __str__(self) -> str:
        return f"#{self.external_id} - {self.name} ({self.status} / {self.species})"

    def to_character_representation(self, source: str = "local_sqlite") -> dict:
        """
        Returns a dictionary representation matching the character structure,
        allowing local fallback when the external API is unavailable.
        """
        return {
            "id": self.external_id,
            "name": self.name,
            "status": self.status,
            "species": self.species,
            "type": self.type,
            "gender": self.gender,
            "origin": {"name": self.origin_name, "url": ""},
            "location": {"name": self.location_name, "url": ""},
            "image": self.image,
            "episode": self.episode_urls,
            "episode_count": self.episode_count,
            "is_favorite": True,
            "source": source,
            "favorited_at": self.created_at.isoformat() if self.created_at else None,
        }


class FavoriteEpisode(models.Model):
    """
    Represents a favorite episode saved locally in SQLite.
    """

    external_id = models.PositiveIntegerField(
        unique=True,
        db_index=True,
        help_text="ID original do episódio na API pública de Rick and Morty.",
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Título do episódio.",
    )
    episode_code = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Código de temporada e episódio (ex: S01E01).",
    )
    air_date = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Data de exibição original do episódio.",
    )
    character_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de URLs dos personagens que participam do episódio.",
    )
    character_count = models.PositiveIntegerField(
        default=0,
        help_text="Quantidade de personagens que aparecem no episódio.",
    )
    url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL original do episódio na API pública.",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Observação opcional adicionada pelo usuário.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["episode_code", "external_id"]
        verbose_name = "Episódio Favorito"
        verbose_name_plural = "Episódios Favoritos"

    def __str__(self) -> str:
        return f"{self.episode_code} - {self.name} (#{self.external_id})"
