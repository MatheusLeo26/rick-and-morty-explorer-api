"""
Unit tests for RickAndMortyClient using mocked HTTP responses.
Verifies caching, pagination, filters, timeout, 404, 5xx, and malformed responses.
"""
from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

from explorer.clients.rick_and_morty import RickAndMortyClient
from explorer.exceptions import (
    ExternalAPITimeoutError,
    ExternalAPIUnavailableError,
    ExternalAPIUnexpectedResponseError,
    ExternalResourceNotFoundError,
)


MOCK_RICK_PAYLOAD = {
    "id": 1,
    "name": "Rick Sanchez",
    "status": "Alive",
    "species": "Human",
    "type": "",
    "gender": "Male",
    "origin": {"name": "Earth (C-137)", "url": "https://rickandmortyapi.com/api/location/1"},
    "location": {"name": "Citadel of Ricks", "url": "https://rickandmortyapi.com/api/location/3"},
    "image": "https://rickandmortyapi.com/api/character/avatar/1.jpeg",
    "episode": [
        "https://rickandmortyapi.com/api/episode/1",
        "https://rickandmortyapi.com/api/episode/2",
    ],
    "url": "https://rickandmortyapi.com/api/character/1",
    "created": "2017-11-04T18:48:46.250Z",
}

MOCK_CHARACTER_LIST_PAYLOAD = {
    "info": {
        "count": 1,
        "pages": 1,
        "next": None,
        "prev": None,
    },
    "results": [MOCK_RICK_PAYLOAD],
}


class RickAndMortyClientTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.client = RickAndMortyClient(
            base_url="https://rickandmortyapi.com/api",
            timeout=3.0,
            cache_ttl=120,
        )

    def tearDown(self):
        cache.clear()

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_get_character_success_and_cache_hit(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_RICK_PAYLOAD
        mock_get.return_value = mock_response

        # First call -> HTTP request (cache miss)
        first_result = self.client.get_character(1)
        self.assertEqual(first_result["name"], "Rick Sanchez")
        self.assertFalse(first_result["from_cache"])
        self.assertEqual(mock_get.call_count, 1)

        # Second call -> Served from cache (no second HTTP request)
        second_result = self.client.get_character(1)
        self.assertEqual(second_result["name"], "Rick Sanchez")
        self.assertTrue(second_result["from_cache"])
        self.assertEqual(mock_get.call_count, 1)

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_list_characters_with_filters_and_pagination(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_CHARACTER_LIST_PAYLOAD
        mock_get.return_value = mock_response

        data = self.client.list_characters(
            page=2,
            name="rick",
            status="alive",
            species="Human",
        )
        self.assertEqual(data["info"]["count"], 1)
        self.assertEqual(len(data["results"]), 1)
        self.assertFalse(data["from_cache"])

        _, kwargs = mock_get.call_args
        self.assertEqual(
            kwargs["params"],
            {"page": 2, "name": "rick", "status": "alive", "species": "Human"},
        )

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_get_character_not_found_raises_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Character not found"}
        mock_get.return_value = mock_response

        with self.assertRaises(ExternalResourceNotFoundError) as ctx:
            self.client.get_character(99999)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.code, "resource_not_found")

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_timeout_raises_external_api_timeout_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with self.assertRaises(ExternalAPITimeoutError) as ctx:
            self.client.get_character(1)
        self.assertEqual(ctx.exception.status_code, 504)
        self.assertEqual(ctx.exception.code, "external_api_timeout")

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_connection_error_raises_unavailable_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("DNS failure")

        with self.assertRaises(ExternalAPIUnavailableError) as ctx:
            self.client.list_characters()
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertEqual(ctx.exception.code, "external_api_unavailable")

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_upstream_500_raises_unavailable_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_get.return_value = mock_response

        with self.assertRaises(ExternalAPIUnavailableError) as ctx:
            self.client.get_character(1)
        self.assertEqual(ctx.exception.status_code, 503)

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_invalid_json_raises_unexpected_response_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = mock_response

        with self.assertRaises(ExternalAPIUnexpectedResponseError) as ctx:
            self.client.get_character(1)
        self.assertEqual(ctx.exception.status_code, 502)

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_incomplete_character_schema_raises_unexpected_response_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "name": "Incomplete"}
        mock_get.return_value = mock_response

        with self.assertRaises(ExternalAPIUnexpectedResponseError) as ctx:
            self.client.get_character(1)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("missing_fields", ctx.exception.details)
