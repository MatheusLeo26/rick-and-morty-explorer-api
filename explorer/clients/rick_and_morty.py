"""
HTTP Client for the official Rick and Morty Public API.
Completely decoupled from Django views and business rules.
Handles configurable caching, timeouts, unavailability, 404s, and unexpected payloads.
"""
import hashlib
import json
import logging
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache

from explorer.exceptions import (
    ExternalAPITimeoutError,
    ExternalAPIUnavailableError,
    ExternalAPIUnexpectedResponseError,
    ExternalResourceNotFoundError,
)

logger = logging.getLogger(__name__)


class RickAndMortyClient:
    """
    Isolated HTTP client responsible for querying the Rick and Morty REST API.
    """

    REQUIRED_CHARACTER_KEYS = {"id", "name", "status", "species"}
    REQUIRED_EPISODE_KEYS = {"id", "name", "episode"}
    REQUIRED_PAGINATED_KEYS = {"info", "results"}

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        cache_ttl: int | None = None,
    ):
        self.base_url = (
            base_url or getattr(settings, "RICK_AND_MORTY_API_BASE_URL", "https://rickandmortyapi.com/api")
        ).rstrip("/")
        self.timeout = (
            timeout
            if timeout is not None
            else float(getattr(settings, "RICK_AND_MORTY_API_TIMEOUT", 5.0))
        )
        self.cache_ttl = (
            cache_ttl
            if cache_ttl is not None
            else int(getattr(settings, "CACHE_TTL_SECONDS", 300))
        )

    def _build_cache_key(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """Creates a deterministic cache key for a given endpoint and query parameters."""
        clean_endpoint = endpoint.strip("/")
        if params:
            filtered = {k: v for k, v in sorted(params.items()) if v is not None and v != ""}
            query_string = urlencode(filtered)
        else:
            query_string = ""
        raw_key = f"{self.base_url}/{clean_endpoint}?{query_string}"
        digest = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
        return f"rick_and_morty_api:{clean_endpoint}:{digest}"

    def _request(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        use_cache: bool = True,
        not_found_message: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        """
        Executes a GET request against the Rick and Morty API with caching and error handling.
        Returns a tuple of (response_dict, from_cache).
        """
        cache_key = self._build_cache_key(endpoint, params)
        if use_cache and self.cache_ttl > 0:
            cached_payload = cache.get(cache_key)
            if cached_payload is not None:
                logger.debug("Cache HIT for %s (params=%s)", endpoint, params)
                return cached_payload, True

        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        clean_params = (
            {k: v for k, v in params.items() if v is not None and v != ""}
            if params
            else None
        )

        try:
            response = requests.get(
                url,
                params=clean_params,
                timeout=self.timeout,
                headers={"Accept": "application/json", "User-Agent": "RickAndMortyExplorerAPI/1.0"},
            )
        except requests.exceptions.Timeout as exc:
            logger.warning("Timeout calling Rick and Morty API at %s: %s", url, exc)
            raise ExternalAPITimeoutError(
                message=f"A requisição para '{endpoint}' excedeu o tempo limite de {self.timeout}s.",
                details={"endpoint": endpoint, "timeout_seconds": self.timeout},
            ) from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Connection error calling Rick and Morty API at %s: %s", url, exc)
            raise ExternalAPIUnavailableError(
                message="Não foi possível estabelecer conexão com a API pública de Rick and Morty.",
                details={"endpoint": endpoint, "reason": str(exc)},
            ) from exc

        if response.status_code == 404:
            raise ExternalResourceNotFoundError(
                message=not_found_message
                or f"Recurso não encontrado na API pública para '{endpoint}'.",
                details={"endpoint": endpoint, "params": clean_params or {}},
            )

        if response.status_code >= 500:
            logger.error(
                "External API server error (%s) for %s", response.status_code, url
            )
            raise ExternalAPIUnavailableError(
                message=(
                    f"A API pública de Rick and Morty retornou erro interno "
                    f"(HTTP {response.status_code})."
                ),
                details={"endpoint": endpoint, "upstream_status": response.status_code},
            )

        if response.status_code != 200:
            logger.warning(
                "Unexpected HTTP status %s from Rick and Morty API for %s",
                response.status_code,
                url,
            )
            raise ExternalAPIUnexpectedResponseError(
                message=(
                    f"A API pública retornou um status inesperado "
                    f"(HTTP {response.status_code})."
                ),
                details={"endpoint": endpoint, "upstream_status": response.status_code},
            )

        try:
            payload = response.json()
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("Invalid JSON received from Rick and Morty API for %s", url)
            raise ExternalAPIUnexpectedResponseError(
                message="A API pública retornou um corpo que não é um JSON válido.",
                details={"endpoint": endpoint},
            ) from exc

        if not isinstance(payload, dict):
            raise ExternalAPIUnexpectedResponseError(
                message="Formato de resposta inválido recebido da API pública (esperado objeto JSON).",
                details={"endpoint": endpoint, "received_type": type(payload).__name__},
            )

        if use_cache and self.cache_ttl > 0:
            cache.set(cache_key, payload, timeout=self.cache_ttl)

        return payload, False

    def _validate_paginated_payload(self, payload: dict[str, Any], endpoint: str) -> None:
        """Validates that a list response contains valid 'info' and 'results' structures."""
        if not self.REQUIRED_PAGINATED_KEYS.issubset(payload.keys()):
            raise ExternalAPIUnexpectedResponseError(
                message="A resposta paginada da API pública não contém os campos 'info' e 'results'.",
                details={"endpoint": endpoint, "keys_received": list(payload.keys())},
            )
        if not isinstance(payload.get("info"), dict) or not isinstance(payload.get("results"), list):
            raise ExternalAPIUnexpectedResponseError(
                message="Estrutura interna de 'info' ou 'results' inválida na resposta da API pública.",
                details={"endpoint": endpoint},
            )

    def _validate_character_payload(self, payload: dict[str, Any], endpoint: str) -> None:
        """Validates that a single character response contains all essential fields."""
        if not self.REQUIRED_CHARACTER_KEYS.issubset(payload.keys()):
            missing = sorted(self.REQUIRED_CHARACTER_KEYS - set(payload.keys()))
            raise ExternalAPIUnexpectedResponseError(
                message="Os dados do personagem retornados pela API pública estão incompletos.",
                details={"endpoint": endpoint, "missing_fields": missing},
            )

    def _validate_episode_payload(self, payload: dict[str, Any], endpoint: str) -> None:
        """Validates that a single episode response contains all essential fields."""
        if not self.REQUIRED_EPISODE_KEYS.issubset(payload.keys()):
            missing = sorted(self.REQUIRED_EPISODE_KEYS - set(payload.keys()))
            raise ExternalAPIUnexpectedResponseError(
                message="Os dados do episódio retornados pela API pública estão incompletos.",
                details={"endpoint": endpoint, "missing_fields": missing},
            )

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
        Fetches a paginated and optionally filtered list of characters from /character.
        """
        params = {
            "page": page,
            "name": name,
            "status": status,
            "species": species,
            "gender": gender,
            "type": type_filter,
        }
        payload, from_cache = self._request(
            "character",
            params=params,
            not_found_message="Nenhum personagem encontrado para os filtros ou página informados.",
        )
        self._validate_paginated_payload(payload, "character")
        for item in payload["results"]:
            if not isinstance(item, dict):
                raise ExternalAPIUnexpectedResponseError(
                    message="Item de personagem inválido na lista de resultados da API pública.",
                    details={"endpoint": "character"},
                )
            self._validate_character_payload(item, "character")

        return {
            "info": payload["info"],
            "results": payload["results"],
            "from_cache": from_cache,
        }

    def get_character(self, character_id: int) -> dict[str, Any]:
        """
        Fetches a single character by its ID from /character/{id}.
        """
        endpoint = f"character/{character_id}"
        payload, from_cache = self._request(
            endpoint,
            not_found_message=f"Personagem com ID {character_id} não foi encontrado na API pública.",
        )
        self._validate_character_payload(payload, endpoint)
        result = dict(payload)
        result["from_cache"] = from_cache
        return result

    def get_episode(self, episode_id: int) -> dict[str, Any]:
        """
        Fetches a single episode by its ID from /episode/{id}.
        """
        endpoint = f"episode/{episode_id}"
        payload, from_cache = self._request(
            endpoint,
            not_found_message=f"Episódio com ID {episode_id} não foi encontrado na API pública.",
        )
        self._validate_episode_payload(payload, endpoint)
        result = dict(payload)
        result["from_cache"] = from_cache
        return result

    def list_episodes(
        self,
        page: int = 1,
        name: str | None = None,
        episode_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetches a paginated list of episodes from /episode.
        """
        params = {
            "page": page,
            "name": name,
            "episode": episode_code,
        }
        payload, from_cache = self._request(
            "episode",
            params=params,
            not_found_message="Nenhum episódio encontrado para os filtros ou página informados.",
        )
        self._validate_paginated_payload(payload, "episode")
        return {
            "info": payload["info"],
            "results": payload["results"],
            "from_cache": from_cache,
        }
