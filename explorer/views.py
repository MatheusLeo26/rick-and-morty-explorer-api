"""
API Views for Rick and Morty Explorer.
Thin HTTP presentation layer that delegates business logic to services.
"""
from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from explorer.serializers import (
    CharacterFilterSerializer,
    CharacterSerializer,
    ErrorResponseSerializer,
    FavoriteCharacterCreateSerializer,
    FavoriteCharacterModelSerializer,
    FavoriteEpisodeCreateSerializer,
    FavoriteEpisodeModelSerializer,
    PaginatedCharacterListSerializer,
    StatsFilterSerializer,
)
from explorer.services import CharacterService, FavoriteService, StatsService


class HealthCheckView(APIView):
    """Returns health and configuration metadata for the API."""

    @extend_schema(
        tags=["Health"],
        summary="Healthcheck da API",
        description="Verifica se a API local e o banco SQLite estão operacionais.",
        responses={200: dict},
    )
    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "service": "rick-and-morty-explorer-api",
                "external_api_base_url": settings.RICK_AND_MORTY_API_BASE_URL,
                "cache_ttl_seconds": settings.CACHE_TTL_SECONDS,
            },
            status=status.HTTP_200_OK,
        )


class CharacterListView(APIView):
    """
    Lists characters from the public Rick and Morty API respecting pagination and filters.
    """

    @extend_schema(
        tags=["Characters"],
        summary="Listar e filtrar personagens da API pública",
        description=(
            "Consulta personagens na API pública de Rick and Morty respeitando a paginação "
            "e permitindo filtrar por `name`, `status` (`alive`, `dead`, `unknown`), "
            "`species`, `gender` e `type`. Utiliza cache configurável e indica quais "
            "personagens já estão favoritados no SQLite."
        ),
        parameters=[
            OpenApiParameter("page", int, description="Número da página (padrão: 1)"),
            OpenApiParameter("name", str, description="Filtro por nome (ex: Rick)"),
            OpenApiParameter(
                "status",
                str,
                description="Filtro por status (alive, dead, unknown)",
            ),
            OpenApiParameter("species", str, description="Filtro por espécie (ex: Human, Alien)"),
            OpenApiParameter(
                "gender",
                str,
                description="Filtro por gênero (female, male, genderless, unknown)",
            ),
            OpenApiParameter("type", str, description="Filtro por subespécie/tipo"),
        ],
        responses={
            200: PaginatedCharacterListSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            502: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
            504: ErrorResponseSerializer,
        },
    )
    def get(self, request: Request) -> Response:
        filter_serializer = CharacterFilterSerializer(data=request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        validated = filter_serializer.validated_data

        service = CharacterService()
        result = service.list_characters(
            page=validated.get("page", 1),
            name=validated.get("name"),
            status=validated.get("status"),
            species=validated.get("species"),
            gender=validated.get("gender"),
            type_filter=validated.get("type"),
        )
        return Response(result, status=status.HTTP_200_OK)


class CharacterDetailView(APIView):
    """
    Retrieves a single character by ID from the external API, with automatic fallback
    to local SQLite if the character is favorited and the external API is unavailable.
    """

    @extend_schema(
        tags=["Characters"],
        summary="Buscar personagem pelo ID",
        description=(
            "Busca os detalhes de um personagem pelo seu ID na API pública. "
            "Caso a API pública esteja indisponível ou sofra timeout, se o personagem "
            "estiver salvo localmente nos favoritos (SQLite), seus dados essenciais "
            "serão retornados via fallback local (`source: local_sqlite_fallback`)."
        ),
        responses={
            200: CharacterSerializer,
            404: ErrorResponseSerializer,
            502: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
            504: ErrorResponseSerializer,
        },
    )
    def get(self, request: Request, character_id: int) -> Response:
        service = CharacterService()
        character = service.get_character_by_id(character_id)
        return Response(character, status=status.HTTP_200_OK)


class FavoriteListCreateView(APIView):
    """
    Lists locally stored favorite characters from SQLite or adds a new favorite character.
    """

    @extend_schema(
        tags=["Favorites"],
        summary="Listar personagens favoritos salvos no SQLite",
        description=(
            "Retorna todos os personagens favoritos persistidos localmente no SQLite. "
            "Funciona mesmo se a API pública estiver fora do ar. Suporta filtros "
            "locais opcionais por `name`, `status` e `species`."
        ),
        parameters=[
            OpenApiParameter("name", str, description="Filtra favoritos localmente por nome"),
            OpenApiParameter("status", str, description="Filtra favoritos localmente por status"),
            OpenApiParameter("species", str, description="Filtra favoritos localmente por espécie"),
        ],
        responses={200: FavoriteCharacterModelSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        service = FavoriteService()
        favorites = service.list_favorites(
            name=request.query_params.get("name"),
            status=request.query_params.get("status"),
            species=request.query_params.get("species"),
        )
        serializer = FavoriteCharacterModelSerializer(favorites, many=True)
        return Response(
            {
                "count": len(serializer.data),
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Favorites"],
        summary="Adicionar um personagem aos favoritos",
        description=(
            "Busca os dados essenciais do personagem na API pública pelo `character_id` "
            "e salva localmente no SQLite para garantir disponibilidade offline e análise estatística."
        ),
        request=FavoriteCharacterCreateSerializer,
        responses={
            201: FavoriteCharacterModelSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            503: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = FavoriteCharacterCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FavoriteService()
        favorite = service.add_favorite(
            character_id=serializer.validated_data["resolved_character_id"],
            notes=serializer.validated_data.get("notes", ""),
        )
        output = FavoriteCharacterModelSerializer(favorite)
        return Response(output.data, status=status.HTTP_201_CREATED)


class FavoriteDetailView(APIView):
    """
    Retrieves or removes a specific favorite character from SQLite.
    """

    @extend_schema(
        tags=["Favorites"],
        summary="Consultar favorito salvo localmente",
        description="Busca um personagem favorito no SQLite pelo `external_id` (ID da API pública) ou `id` local.",
        responses={
            200: FavoriteCharacterModelSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def get(self, request: Request, lookup_id: int) -> Response:
        service = FavoriteService()
        favorite = service.get_favorite(lookup_id)
        return Response(FavoriteCharacterModelSerializer(favorite).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Favorites"],
        summary="Remover personagem dos favoritos",
        description="Remove um personagem favorito do banco SQLite pelo `external_id` ou `id` local.",
        responses={
            200: dict,
            404: ErrorResponseSerializer,
        },
    )
    def delete(self, request: Request, lookup_id: int) -> Response:
        service = FavoriteService()
        removed = service.remove_favorite(lookup_id)
        return Response(
            {
                "message": "Personagem removido dos favoritos com sucesso.",
                "removed": removed,
            },
            status=status.HTTP_200_OK,
        )


class FavoriteEpisodeListCreateView(APIView):
    """
    Lists or adds favorite episodes in SQLite, and summarizes episodes from favorite characters.
    """

    @extend_schema(
        tags=["Favorite Episodes"],
        summary="Listar episódios favoritos no SQLite",
        description=(
            "Lista os episódios favoritos persistidos localmente no SQLite e também "
            "apresenta o ranking de episódios vinculados aos personagens favoritos salvos."
        ),
        parameters=[
            OpenApiParameter("name", str, description="Filtra episódios favoritos pelo título"),
            OpenApiParameter("episode", str, description="Filtra pelo código (ex: S01E01 ou S01)"),
        ],
        responses={200: FavoriteEpisodeModelSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        service = FavoriteService()
        data = service.list_favorite_episodes(
            name=request.query_params.get("name"),
            episode_code=request.query_params.get("episode"),
        )
        serialized_episodes = FavoriteEpisodeModelSerializer(data["favorite_episodes"], many=True).data
        return Response(
            {
                "count": len(serialized_episodes),
                "results": serialized_episodes,
                "total_unique_episodes_in_favorite_characters": data[
                    "total_unique_episodes_in_favorite_characters"
                ],
                "episodes_from_favorite_characters": data["episodes_from_favorite_characters"],
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Favorite Episodes"],
        summary="Adicionar um episódio aos favoritos no SQLite",
        description="Consulta um episódio na API pública pelo `episode_id` e salva seus dados essenciais no SQLite.",
        request=FavoriteEpisodeCreateSerializer,
        responses={
            201: FavoriteEpisodeModelSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    def post(self, request: Request) -> Response:
        serializer = FavoriteEpisodeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = FavoriteService()
        fav_episode = service.add_favorite_episode(
            episode_id=serializer.validated_data["resolved_episode_id"],
            notes=serializer.validated_data.get("notes", ""),
        )
        return Response(
            FavoriteEpisodeModelSerializer(fav_episode).data,
            status=status.HTTP_201_CREATED,
        )


class FavoriteEpisodeDetailView(APIView):
    """
    Removes a favorite episode from SQLite.
    """

    @extend_schema(
        tags=["Favorite Episodes"],
        summary="Remover episódio dos favoritos",
        description="Remove um episódio favorito do SQLite pelo `external_id` ou `id` local.",
        responses={200: dict, 404: ErrorResponseSerializer},
    )
    def delete(self, request: Request, lookup_id: int) -> Response:
        service = FavoriteService()
        removed = service.remove_favorite_episode(lookup_id)
        return Response(
            {
                "message": "Episódio removido dos favoritos com sucesso.",
                "removed": removed,
            },
            status=status.HTTP_200_OK,
        )


class FavoriteStatsView(APIView):
    """
    Computes analytical statistics on saved favorites using Pandas.
    Supports both GET (RESTful read-only aggregation) and POST (ad-hoc filtered calculation).
    """

    @extend_schema(
        tags=["Statistics"],
        summary="Consultar estatísticas dos favoritos com Pandas (GET)",
        description=(
            "Gera métricas analíticas sobre os favoritos salvos no SQLite utilizando Pandas "
            "(contagem e percentuais por status, espécie, gênero, origens, localizações, "
            "média/mediana/máximo/mínimo de episódios e matriz espécie x status)."
        ),
        parameters=[
            OpenApiParameter("status", str, description="Filtra o DataFrame por status"),
            OpenApiParameter("species", str, description="Filtra o DataFrame por espécie"),
        ],
        responses={200: dict},
    )
    def get(self, request: Request) -> Response:
        serializer = StatsFilterSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        stats = StatsService.compute_favorites_stats(
            status=serializer.validated_data.get("status"),
            species=serializer.validated_data.get("species"),
        )
        return Response(stats, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Statistics"],
        summary="Processar estatísticas dos favoritos com filtros via Pandas (POST)",
        description=(
            "Permite enviar filtros opcionais no corpo da requisição (`status`, `species`) "
            "para processar um relatório estatístico customizado com Pandas sobre os favoritos."
        ),
        request=StatsFilterSerializer,
        responses={200: dict},
    )
    def post(self, request: Request) -> Response:
        serializer = StatsFilterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        stats = StatsService.compute_favorites_stats(
            status=serializer.validated_data.get("status"),
            species=serializer.validated_data.get("species"),
        )
        return Response(stats, status=status.HTTP_200_OK)
