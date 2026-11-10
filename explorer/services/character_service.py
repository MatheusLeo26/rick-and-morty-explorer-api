"""
Business logic service for querying and enriching characters from the Rick and Morty API.
Includes local SQLite fallback for favorited characters when the external API is unavailable.
"""
import logging
from typing import Any

from explorer.clients.rick_and_morty import RickAndMortyClient
from explorer.exceptions import (
    ExternalAPITimeoutError,
    ExternalAPIUnavailableError,
)
from explorer.models import FavoriteCharacter

logger = logging.getLogger(__name__)


class CharacterService:
    """
    Coordinates character queries between the external HTTP client and local SQLite state.
    """

    def __init__(self, client: RickAndMortyClient | None = None):
        self.client = client or RickAndMortyClient()

    @staticmethod
    def _enrich_character(raw_character: dict[str, Any], favorite_ids: set[int]) -> dict[str, Any]:
        """Adds computed fields (episode_count, is_favorite, source) to a character dict."""
        episodes = raw_character.get("episode") or []
        char_id = raw_character.get("id")
        return {
            "id": char_id,
            "name": raw_character.get("name", ""),
            "status": raw_character.get("status", "unknown"),
            "species": raw_character.get("species", "unknown"),
            "type": raw_character.get("type", ""),
            "gender": raw_character.get("gender", "unknown"),
            "origin": raw_character.get("origin") or {"name": "unknown", "url": ""},
            "location": raw_character.get("location") or {"name": "unknown", "url": ""},
            "image": raw_character.get("image", ""),
            "episode": episodes,
            "episode_count": len(episodes) if isinstance(episodes, list) else 0,
            "is_favorite": char_id in favorite_ids,
            "source": "external_api_cache" if raw_character.get("from_cache") else "external_api",
            "url": raw_character.get("url", ""),
            "created": raw_character.get("created", ""),
        }

    def list_characters(
        self,
        page: int = 1,
        name: str | None = None,
        status: str | None = None,
        species: str | None = None,
        gender: str | None = None,
        type_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Lists characters from the public API respecting pagination and filters,
        marking which characters are already favorited locally.
        """
        data = self.client.list_characters(
            page=page,
            name=name,
            status=status,
            species=species,
            gender=gender,
            type_filter=type_filter,
        )
        results = data.get("results", [])
        char_ids = [item.get("id") for item in results if isinstance(item, dict) and item.get("id")]
        favorite_ids = set(
            FavoriteCharacter.objects.filter(external_id__in=char_ids).values_list(
                "external_id", flat=True
            )
        )

        enriched_results = [
            self._enrich_character({**item, "from_cache": data.get("from_cache", False)}, favorite_ids)
            for item in results
        ]

        return {
            "info": data["info"],
            "from_cache": data.get("from_cache", False),
            "results": enriched_results,
        }

    def get_character_by_id(self, character_id: int) -> dict[str, Any]:
        """
        Fetches a character by ID from the external API.
        If the external API times out or is unavailable AND the character is saved
        locally as a favorite in SQLite, returns the locally stored essential data
        so the favorite remains visible offline.
        """
        try:
            raw_character = self.client.get_character(character_id)
        except (ExternalAPIUnavailableError, ExternalAPITimeoutError) as exc:
            favorite = FavoriteCharacter.objects.filter(external_id=character_id).first()
            if favorite is not None:
                logger.info(
                    "External API unavailable; serving character #%s (%s) from local SQLite fallback.",
                    character_id,
                    favorite.name,
                )
                return favorite.to_character_representation(source="local_sqlite_fallback")
            raise exc

        is_fav = FavoriteCharacter.objects.filter(external_id=character_id).exists()
        favorite_ids = {character_id} if is_fav else set()
        return self._enrich_character(raw_character, favorite_ids)
