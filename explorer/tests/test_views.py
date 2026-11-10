"""
Integration tests for the API views using Django REST Framework's APIClient
and mocked external HTTP calls.
"""
from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from explorer.tests.test_client import MOCK_CHARACTER_LIST_PAYLOAD, MOCK_RICK_PAYLOAD
from explorer.tests.test_services import MOCK_EPISODE_PAYLOAD, MOCK_MORTY_PAYLOAD


class ExplorerAPIViewsTests(APITestCase):
    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_health_check_endpoint(self):
        response = self.client.get(reverse("explorer:health"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_list_characters_endpoint_with_filters(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = MOCK_CHARACTER_LIST_PAYLOAD
        mock_get.return_value = mock_resp

        url = reverse("explorer:character-list")
        response = self.client.get(url, {"name": "rick", "status": "alive", "species": "Human"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["info"]["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Rick Sanchez")

    def test_list_characters_invalid_status_filter_returns_400(self):
        url = reverse("explorer:character-list")
        response = self.client.get(url, {"status": "immortal"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data["error"])

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_get_character_by_id_and_not_found_404(self, mock_get):
        mock_ok = MagicMock()
        mock_ok.status_code = 200
        mock_ok.json.return_value = MOCK_RICK_PAYLOAD
        mock_get.return_value = mock_ok

        detail_url = reverse("explorer:character-detail", kwargs={"character_id": 1})
        res_ok = self.client.get(detail_url)
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ok.data["name"], "Rick Sanchez")

        mock_404 = MagicMock()
        mock_404.status_code = 404
        mock_404.json.return_value = {"error": "Character not found"}
        mock_get.return_value = mock_404

        not_found_url = reverse("explorer:character-detail", kwargs={"character_id": 99999})
        res_404 = self.client.get(not_found_url)
        self.assertEqual(res_404.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res_404.data["code"], "resource_not_found")

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_get_character_timeout_returns_504(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout("Timed out")
        url = reverse("explorer:character-detail", kwargs={"character_id": 10})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_504_GATEWAY_TIMEOUT)
        self.assertEqual(response.data["code"], "external_api_timeout")

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_favorites_lifecycle_and_stats_endpoints(self, mock_get):
        mock_rick = MagicMock()
        mock_rick.status_code = 200
        mock_rick.json.return_value = MOCK_RICK_PAYLOAD

        mock_morty = MagicMock()
        mock_morty.status_code = 200
        mock_morty.json.return_value = MOCK_MORTY_PAYLOAD

        mock_get.side_effect = [mock_rick, mock_morty]

        fav_url = reverse("explorer:favorite-list-create")

        # Add Rick (#1) and Morty (#2)
        res1 = self.client.post(fav_url, {"character_id": 1, "notes": "Rick C-137"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(fav_url, {"character_id": 2, "notes": "Morty"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        # Duplicate favorite returns 400
        res_dup = self.client.post(fav_url, {"character_id": 1}, format="json")
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_dup.data["code"], "duplicate_favorite")

        # List favorites
        list_res = self.client.get(fav_url)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(list_res.data["count"], 2)

        # Query Pandas stats via GET and POST
        stats_url = reverse("explorer:favorite-stats")
        stats_get = self.client.get(stats_url)
        self.assertEqual(stats_get.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_get.data["total_favorites"], 2)
        self.assertEqual(stats_get.data["by_species"], {"Human": 2})

        stats_post = self.client.post(stats_url, {"status": "Alive"}, format="json")
        self.assertEqual(stats_post.status_code, status.HTTP_200_OK)
        self.assertEqual(stats_post.data["total_favorites"], 2)

        # Delete favorite (#2)
        del_url = reverse("explorer:favorite-detail", kwargs={"lookup_id": 2})
        del_res = self.client.delete(del_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)
        self.assertEqual(del_res.data["removed"]["external_id"], 2)

    @patch("explorer.clients.rick_and_morty.requests.get")
    def test_favorite_episodes_endpoints(self, mock_get):
        mock_ep = MagicMock()
        mock_ep.status_code = 200
        mock_ep.json.return_value = MOCK_EPISODE_PAYLOAD
        mock_get.return_value = mock_ep

        ep_url = reverse("explorer:favorite-episode-list-create")
        post_res = self.client.post(ep_url, {"episode_id": 1, "notes": "Piloto"}, format="json")
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(post_res.data["episode_code"], "S01E01")

        get_res = self.client.get(ep_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data["count"], 1)

        del_url = reverse("explorer:favorite-episode-detail", kwargs={"lookup_id": 1})
        del_res = self.client.delete(del_url)
        self.assertEqual(del_res.status_code, status.HTTP_200_OK)

    def test_openapi_schema_and_swagger_docs_accessible(self):
        schema_res = self.client.get(reverse("schema"))
        self.assertEqual(schema_res.status_code, status.HTTP_200_OK)

        swagger_res = self.client.get(reverse("swagger-ui"))
        self.assertEqual(swagger_res.status_code, status.HTTP_200_OK)
