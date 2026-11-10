"""
Business logic service for managing favorite characters and favorite episodes in SQLite.
"""
from collections import Counter
from typing import Any

from django.db.models import Q, QuerySet

from explorer.clients.rick_and_morty import RickAndMortyClient
from explorer.exceptions import DuplicateFavoriteError, ExternalResourceNotFoundError
from explorer.models import FavoriteCharacter, FavoriteEpisode


class FavoriteService:
    """
    Handles CRUD operations for local favorites stored in SQLite.
    """

    def __init__(self, client: RickAndMortyClient | None = None):
        self.client = client or RickAndMortyClient()

    def list_favorites(
        self,
        name: str | None = None,
        status: str | None = None,
        species: str | None = None,
    ) -> QuerySet[FavoriteCharacter]:
        """
        Lists favorite characters directly from SQLite, supporting optional local filters.
        Works even when the external Rick and Morty API is completely offline.
        """
        queryset = FavoriteCharacter.objects.all()
        if name:
            queryset = queryset.filter(name__icontains=name.strip())
        if status:
            queryset = queryset.filter(status__iexact=status.strip())
        if species:
            queryset = queryset.filter(species__icontains=species.strip())
        return queryset

    def get_favorite(self, lookup_id: int) -> FavoriteCharacter:
        """
        Retrieves a single favorite character from SQLite by its external_id or local PK.
        """
        favorite = FavoriteCharacter.objects.filter(
            Q(external_id=lookup_id) | Q(pk=lookup_id)
        ).first()
        if favorite is None:
            raise ExternalResourceNotFoundError(
                message=f"Favorito com identificador {lookup_id} não foi encontrado no banco local.",
                details={"lookup_id": lookup_id},
            )
        return favorite

    def add_favorite(self, character_id: int, notes: str = "") -> FavoriteCharacter:
        """
        Fetches a character from the public API and persists its essential data locally in SQLite.
        Raises DuplicateFavoriteError if the character is already favorited.
        """
        if FavoriteCharacter.objects.filter(external_id=character_id).exists():
            raise DuplicateFavoriteError(
                message=f"O personagem com ID {character_id} já está salvo nos favoritos.",
                details={"character_id": character_id},
            )

        char_data = self.client.get_character(character_id)
        origin_obj = char_data.get("origin") or {}
        location_obj = char_data.get("location") or {}
        episodes = char_data.get("episode") or []

        favorite = FavoriteCharacter.objects.create(
            external_id=char_data["id"],
            name=char_data["name"],
            status=char_data.get("status", "unknown"),
            species=char_data.get("species", "unknown"),
            type=char_data.get("type", "") or "",
            gender=char_data.get("gender", "unknown") or "unknown",
            origin_name=origin_obj.get("name", "unknown") if isinstance(origin_obj, dict) else "unknown",
            location_name=location_obj.get("name", "unknown") if isinstance(location_obj, dict) else "unknown",
            image=char_data.get("image", "") or "",
            episode_urls=episodes if isinstance(episodes, list) else [],
            episode_count=len(episodes) if isinstance(episodes, list) else 0,
            notes=notes.strip() if notes else "",
        )
        return favorite

    def remove_favorite(self, lookup_id: int) -> dict[str, Any]:
        """
        Removes a favorite character from SQLite by external_id or local PK.
        """
        favorite = self.get_favorite(lookup_id)
        summary = {
            "id": favorite.id,
            "external_id": favorite.external_id,
            "name": favorite.name,
        }
        favorite.delete()
        return summary

    # --- Favorite Episodes in SQLite ---

    def list_favorite_episodes(
        self,
        name: str | None = None,
        episode_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Lists favorite episodes stored in SQLite, plus an aggregated summary of episodes
        linked to the user's favorite characters in SQLite.
        """
        queryset = FavoriteEpisode.objects.all()
        if name:
            queryset = queryset.filter(name__icontains=name.strip())
        if episode_code:
            queryset = queryset.filter(episode_code__icontains=episode_code.strip())

        # Also aggregate episode references stored locally inside FavoriteCharacter records
        episode_counter: Counter[str] = Counter()
        character_map: dict[str, list[str]] = {}
        for fav_char in FavoriteCharacter.objects.all():
            for ep_url in fav_char.episode_urls or []:
                episode_counter[ep_url] += 1
                character_map.setdefault(ep_url, []).append(fav_char.name)

        appearances_summary = [
            {
                "episode_url": ep_url,
                "episode_id": int(ep_url.rstrip("/").split("/")[-1])
                if ep_url.rstrip("/").split("/")[-1].isdigit()
                else None,
                "favorite_characters_count": count,
                "favorite_characters": character_map.get(ep_url, []),
            }
            for ep_url, count in episode_counter.most_common(20)
        ]

        return {
            "favorite_episodes": queryset,
            "episodes_from_favorite_characters": appearances_summary,
            "total_unique_episodes_in_favorite_characters": len(episode_counter),
        }

    def add_favorite_episode(self, episode_id: int, notes: str = "") -> FavoriteEpisode:
        """
        Fetches an episode from the public API and saves its essential data locally in SQLite.
        """
        if FavoriteEpisode.objects.filter(external_id=episode_id).exists():
            raise DuplicateFavoriteError(
                message=f"O episódio com ID {episode_id} já está salvo nos favoritos.",
                details={"episode_id": episode_id},
            )

        ep_data = self.client.get_episode(episode_id)
        characters = ep_data.get("characters") or []

        favorite_ep = FavoriteEpisode.objects.create(
            external_id=ep_data["id"],
            name=ep_data["name"],
            episode_code=ep_data.get("episode", ""),
            air_date=ep_data.get("air_date", "") or "",
            character_urls=characters if isinstance(characters, list) else [],
            character_count=len(characters) if isinstance(characters, list) else 0,
            url=ep_data.get("url", "") or "",
            notes=notes.strip() if notes else "",
        )
        return favorite_ep

    def remove_favorite_episode(self, lookup_id: int) -> dict[str, Any]:
        """
        Removes a favorite episode from SQLite by external_id or local PK.
        """
        favorite_ep = FavoriteEpisode.objects.filter(
            Q(external_id=lookup_id) | Q(pk=lookup_id)
        ).first()
        if favorite_ep is None:
            raise ExternalResourceNotFoundError(
                message=f"Episódio favorito com identificador {lookup_id} não foi encontrado no banco local.",
                details={"lookup_id": lookup_id},
            )
        summary = {
            "id": favorite_ep.id,
            "external_id": favorite_ep.external_id,
            "name": favorite_ep.name,
            "episode_code": favorite_ep.episode_code,
        }
        favorite_ep.delete()
        return summary
