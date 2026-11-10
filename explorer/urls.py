"""
URL routing for the explorer API endpoints.
"""
from django.urls import path
from explorer.views import (
    CharacterDetailView,
    CharacterListView,
    FavoriteDetailView,
    FavoriteEpisodeDetailView,
    FavoriteEpisodeListCreateView,
    FavoriteListCreateView,
    FavoriteStatsView,
    HealthCheckView,
)

app_name = "explorer"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    # Characters (External API + Cache + Local Fallback)
    path("characters/", CharacterListView.as_view(), name="character-list"),
    path("characters/<int:character_id>/", CharacterDetailView.as_view(), name="character-detail"),
    # Favorites & Statistics (SQLite + Pandas)
    path("favorites/", FavoriteListCreateView.as_view(), name="favorite-list-create"),
    path("favorites/stats/", FavoriteStatsView.as_view(), name="favorite-stats"),
    path(
        "favorites/episodes/",
        FavoriteEpisodeListCreateView.as_view(),
        name="favorite-episode-list-create",
    ),
    path(
        "favorites/episodes/<int:lookup_id>/",
        FavoriteEpisodeDetailView.as_view(),
        name="favorite-episode-detail",
    ),
    path("favorites/<int:lookup_id>/", FavoriteDetailView.as_view(), name="favorite-detail"),
]
