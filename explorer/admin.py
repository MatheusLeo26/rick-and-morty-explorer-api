from django.contrib import admin
from .models import FavoriteCharacter, FavoriteEpisode


@admin.register(FavoriteCharacter)
class FavoriteCharacterAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "name",
        "status",
        "species",
        "gender",
        "episode_count",
        "created_at",
    )
    list_filter = ("status", "species", "gender")
    search_fields = ("name", "species", "origin_name", "location_name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(FavoriteEpisode)
class FavoriteEpisodeAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "episode_code",
        "name",
        "air_date",
        "character_count",
        "created_at",
    )
    search_fields = ("name", "episode_code")
    readonly_fields = ("created_at", "updated_at")
