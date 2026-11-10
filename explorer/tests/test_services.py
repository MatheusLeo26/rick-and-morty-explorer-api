"""
Unit tests for business rules in CharacterService, FavoriteService, and StatsService (Pandas).
All external calls are mocked so tests never depend on the live public API.
"""
from unittest.mock import MagicMock

from django.core.cache import cache
from django.test import TestCase

from explorer.exceptions import (
    DuplicateFavoriteError,
    ExternalAPIUnavailableError,
    ExternalResourceNotFoundError,
)
from explorer.models import FavoriteCharacter, FavoriteEpisode
from explorer.services import CharacterService, FavoriteService, StatsService
from explorer.tests.test_client import MOCK_RICK_PAYLOAD


MOCK_MORTY_PAYLOAD = {
    "id": 2,
    "name": "Morty Smith",
    "status": "Alive",
    "species": "Human",
    "type": "",
    "gender": "Male",
    "origin": {"name": "unknown", "url": ""},
    "location": {"name": "Citadel of Ricks", "url": "https://rickandmortyapi.com/api/location/3"},
    "image": "https://rickandmortyapi.com/api/character/avatar/2.jpeg",
    "episode": [
        "https://rickandmortyapi.com/api/episode/1",
        "https://rickandmortyapi.com/api/episode/2",
        "https://rickandmortyapi.com/api/episode/3",
    ],
    "from_cache": False,
}

MOCK_BIRDPERSON_PAYLOAD = {
    "id": 47,
    "name": "Birdperson",
    "status": "Dead",
    "species": "Alien",
    "type": "Bird-Person",
    "gender": "Male",
    "origin": {"name": "Bird World", "url": ""},
    "location": {"name": "Planet Squanch", "url": ""},
    "image": "https://rickandmortyapi.com/api/character/avatar/47.jpeg",
    "episode": ["https://rickandmortyapi.com/api/episode/11"],
    "from_cache": False,
}

MOCK_EPISODE_PAYLOAD = {
    "id": 1,
    "name": "Pilot",
    "air_date": "December 2, 2013",
    "episode": "S01E01",
    "characters": [
        "https://rickandmortyapi.com/api/character/1",
        "https://rickandmortyapi.com/api/character/2",
    ],
    "url": "https://rickandmortyapi.com/api/episode/1",
    "from_cache": False,
}


class FavoriteAndCharacterServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.mock_client = MagicMock()
        self.favorite_service = FavoriteService(client=self.mock_client)
        self.character_service = CharacterService(client=self.mock_client)

    def test_add_list_and_remove_favorite_character(self):
        self.mock_client.get_character.return_value = MOCK_RICK_PAYLOAD

        fav = self.favorite_service.add_favorite(character_id=1, notes="Cientista C-137")
        self.assertEqual(fav.external_id, 1)
        self.assertEqual(fav.name, "Rick Sanchez")
        self.assertEqual(fav.episode_count, 2)
        self.assertEqual(fav.origin_name, "Earth (C-137)")

        # Verify listing from SQLite
        favorites = self.favorite_service.list_favorites(species="Human")
        self.assertEqual(favorites.count(), 1)

        # Verify duplicate prevention
        with self.assertRaises(DuplicateFavoriteError):
            self.favorite_service.add_favorite(character_id=1)

        # Verify removal
        removed = self.favorite_service.remove_favorite(1)
        self.assertEqual(removed["external_id"], 1)
        self.assertEqual(FavoriteCharacter.objects.count(), 0)

        with self.assertRaises(ExternalResourceNotFoundError):
            self.favorite_service.remove_favorite(1)

    def test_character_fallback_to_sqlite_when_external_api_unavailable(self):
        # Save character #1 locally as a favorite first
        self.mock_client.get_character.return_value = MOCK_RICK_PAYLOAD
        self.favorite_service.add_favorite(character_id=1)

        # Simulate external API going down
        self.mock_client.get_character.side_effect = ExternalAPIUnavailableError(
            "Public API is down"
        )

        # CharacterService should serve essential data from local SQLite fallback
        character = self.character_service.get_character_by_id(1)
        self.assertEqual(character["id"], 1)
        self.assertEqual(character["name"], "Rick Sanchez")
        self.assertTrue(character["is_favorite"])
        self.assertEqual(character["source"], "local_sqlite_fallback")

        # For a non-favorited character, unavailability should still raise 503
        with self.assertRaises(ExternalAPIUnavailableError):
            self.character_service.get_character_by_id(999)

    def test_favorite_episodes_crud_and_character_episode_aggregation(self):
        self.mock_client.get_character.return_value = MOCK_RICK_PAYLOAD
        self.favorite_service.add_favorite(character_id=1)

        self.mock_client.get_episode.return_value = MOCK_EPISODE_PAYLOAD
        fav_ep = self.favorite_service.add_favorite_episode(episode_id=1, notes="Ótimo piloto")
        self.assertEqual(fav_ep.episode_code, "S01E01")
        self.assertEqual(fav_ep.character_count, 2)

        ep_data = self.favorite_service.list_favorite_episodes()
        self.assertEqual(ep_data["favorite_episodes"].count(), 1)
        self.assertEqual(ep_data["total_unique_episodes_in_favorite_characters"], 2)

        removed = self.favorite_service.remove_favorite_episode(1)
        self.assertEqual(removed["episode_code"], "S01E01")
        self.assertEqual(FavoriteEpisode.objects.count(), 0)


class StatsServiceTests(TestCase):
    def test_stats_on_empty_favorites(self):
        stats = StatsService.compute_favorites_stats()
        self.assertEqual(stats["total_favorites"], 0)
        self.assertEqual(stats["by_status"], {})
        self.assertEqual(stats["episode_stats"]["mean_episodes_per_character"], 0.0)
        self.assertIsNone(stats["episode_stats"]["most_featured_character"])

    def test_stats_computation_with_pandas(self):
        mock_client = MagicMock()
        fav_service = FavoriteService(client=mock_client)

        mock_client.get_character.side_effect = [
            MOCK_RICK_PAYLOAD,        # 2 episodes, Alive, Human
            MOCK_MORTY_PAYLOAD,       # 3 episodes, Alive, Human
            MOCK_BIRDPERSON_PAYLOAD,  # 1 episode, Dead, Alien
        ]
        fav_service.add_favorite(1)
        fav_service.add_favorite(2)
        fav_service.add_favorite(47)

        stats = StatsService.compute_favorites_stats()

        self.assertEqual(stats["total_favorites"], 3)
        self.assertEqual(stats["by_status"], {"Alive": 2, "Dead": 1})
        self.assertEqual(stats["status_percentage"], {"Alive": 66.67, "Dead": 33.33})
        self.assertEqual(stats["by_species"], {"Human": 2, "Alien": 1})
        self.assertEqual(stats["episode_stats"]["mean_episodes_per_character"], 2.0)
        self.assertEqual(stats["episode_stats"]["median_episodes_per_character"], 2.0)
        self.assertEqual(stats["episode_stats"]["max_episodes"], 3)
        self.assertEqual(stats["episode_stats"]["min_episodes"], 1)
        self.assertEqual(stats["episode_stats"]["total_episode_appearances"], 6)
        self.assertEqual(stats["episode_stats"]["unique_episodes_across_favorites"], 4)
        self.assertEqual(stats["episode_stats"]["most_featured_character"]["name"], "Morty Smith")
        self.assertEqual(stats["episode_stats"]["least_featured_character"]["name"], "Birdperson")
        self.assertEqual(stats["species_by_status"]["Human"]["Alive"], 2)
        self.assertEqual(stats["species_by_status"]["Alien"]["Dead"], 1)
