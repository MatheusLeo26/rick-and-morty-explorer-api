"""
Serializers for input validation, SQLite models, and OpenAPI schema generation.
"""
from rest_framework import serializers
from explorer.models import FavoriteCharacter, FavoriteEpisode


class CharacterFilterSerializer(serializers.Serializer):
    """Validates query parameters for listing and filtering characters."""

    VALID_STATUSES = ("alive", "dead", "unknown")
    VALID_GENDERS = ("female", "male", "genderless", "unknown")

    page = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text="Número da página da listagem (padrão: 1).",
    )
    name = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text="Filtra personagens pelo nome (ex: Rick, Morty).",
    )
    status = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Filtra pelo status de vida: alive, dead ou unknown.",
    )
    species = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Filtra pela espécie (ex: Human, Alien).",
    )
    gender = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Filtra pelo gênero: female, male, genderless ou unknown.",
    )
    type = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=150,
        help_text="Filtra pelo subtipo do personagem.",
    )

    def validate_status(self, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned and cleaned not in self.VALID_STATUSES:
            raise serializers.ValidationError(
                f"Status inválido '{value}'. Valores permitidos: {', '.join(self.VALID_STATUSES)}."
            )
        return cleaned

    def validate_gender(self, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned and cleaned not in self.VALID_GENDERS:
            raise serializers.ValidationError(
                f"Gênero inválido '{value}'. Valores permitidos: {', '.join(self.VALID_GENDERS)}."
            )
        return cleaned


class LocationRefSerializer(serializers.Serializer):
    name = serializers.CharField()
    url = serializers.CharField(allow_blank=True, required=False)


class CharacterSerializer(serializers.Serializer):
    """Represents a character returned from the API or local fallback."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    species = serializers.CharField()
    type = serializers.CharField(allow_blank=True)
    gender = serializers.CharField()
    origin = LocationRefSerializer()
    location = LocationRefSerializer()
    image = serializers.CharField(allow_blank=True)
    episode = serializers.ListField(child=serializers.CharField())
    episode_count = serializers.IntegerField()
    is_favorite = serializers.BooleanField()
    source = serializers.CharField()


class PaginationInfoSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    pages = serializers.IntegerField()
    next = serializers.CharField(allow_null=True)
    prev = serializers.CharField(allow_null=True)


class PaginatedCharacterListSerializer(serializers.Serializer):
    info = PaginationInfoSerializer()
    from_cache = serializers.BooleanField()
    results = CharacterSerializer(many=True)


class FavoriteCharacterModelSerializer(serializers.ModelSerializer):
    """Serializer for locally persisted FavoriteCharacter instances."""

    class Meta:
        model = FavoriteCharacter
        fields = [
            "id",
            "external_id",
            "name",
            "status",
            "species",
            "type",
            "gender",
            "origin_name",
            "location_name",
            "image",
            "episode_urls",
            "episode_count",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "name",
            "status",
            "species",
            "type",
            "gender",
            "origin_name",
            "location_name",
            "image",
            "episode_urls",
            "episode_count",
            "created_at",
            "updated_at",
        ]


class FavoriteCharacterCreateSerializer(serializers.Serializer):
    """Validates payload for adding a character to favorites."""

    character_id = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="ID do personagem na API pública de Rick and Morty (ex: 1 para Rick Sanchez).",
    )
    external_id = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Alias opcional para character_id.",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
        help_text="Anotação opcional sobre o personagem favorito.",
    )

    def validate(self, attrs: dict) -> dict:
        char_id = attrs.get("character_id") or attrs.get("external_id")
        if not char_id:
            raise serializers.ValidationError(
                {"character_id": "Informe o campo 'character_id' (inteiro positivo)."}
            )
        attrs["resolved_character_id"] = char_id
        return attrs


class FavoriteEpisodeModelSerializer(serializers.ModelSerializer):
    """Serializer for locally persisted FavoriteEpisode instances."""

    class Meta:
        model = FavoriteEpisode
        fields = [
            "id",
            "external_id",
            "name",
            "episode_code",
            "air_date",
            "character_urls",
            "character_count",
            "url",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "name",
            "episode_code",
            "air_date",
            "character_urls",
            "character_count",
            "url",
            "created_at",
            "updated_at",
        ]


class FavoriteEpisodeCreateSerializer(serializers.Serializer):
    """Validates payload for adding an episode to favorites in SQLite."""

    episode_id = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="ID do episódio na API pública de Rick and Morty (ex: 1 para Pilot S01E01).",
    )
    external_id = serializers.IntegerField(
        required=False,
        min_value=1,
        help_text="Alias opcional para episode_id.",
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
        help_text="Anotação opcional sobre o episódio favorito.",
    )

    def validate(self, attrs: dict) -> dict:
        ep_id = attrs.get("episode_id") or attrs.get("external_id")
        if not ep_id:
            raise serializers.ValidationError(
                {"episode_id": "Informe o campo 'episode_id' (inteiro positivo)."}
            )
        attrs["resolved_episode_id"] = ep_id
        return attrs


class StatsFilterSerializer(serializers.Serializer):
    """Optional filter parameters for computing Pandas statistics on favorites."""

    status = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
        help_text="Filtra os favoritos analisados por status (ex: Alive, Dead, unknown).",
    )
    species = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
        help_text="Filtra os favoritos analisados por espécie (ex: Human, Alien).",
    )


class ErrorResponseSerializer(serializers.Serializer):
    """Standardized error response schema for OpenAPI documentation."""

    error = serializers.BooleanField(default=True)
    code = serializers.CharField()
    message = serializers.CharField()
    status_code = serializers.IntegerField()
    details = serializers.DictField(required=False)
