"""
Custom domain and integration exceptions for the Rick and Morty Explorer API.
"""


class ExplorerBaseException(Exception):
    """Base exception for all custom errors in the Explorer application."""

    default_message = "Ocorreu um erro interno na aplicação."
    default_code = "explorer_error"
    status_code = 500

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
        details: dict | None = None,
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ExternalResourceNotFoundError(ExplorerBaseException):
    """Raised when a requested character or episode does not exist (404)."""

    default_message = "Recurso não encontrado na API pública de Rick and Morty."
    default_code = "resource_not_found"
    status_code = 404


class ExternalAPITimeoutError(ExplorerBaseException):
    """Raised when the external Rick and Morty API request times out (504)."""

    default_message = "Tempo limite excedido ao consultar a API pública de Rick and Morty."
    default_code = "external_api_timeout"
    status_code = 504


class ExternalAPIUnavailableError(ExplorerBaseException):
    """Raised when the external Rick and Morty API is unreachable or returns 5xx (503)."""

    default_message = "A API pública de Rick and Morty está temporariamente indisponível."
    default_code = "external_api_unavailable"
    status_code = 503


class ExternalAPIUnexpectedResponseError(ExplorerBaseException):
    """Raised when the external API returns malformed JSON or unexpected schema (502)."""

    default_message = "Resposta inesperada ou malformada recebida da API pública de Rick and Morty."
    default_code = "external_api_unexpected_response"
    status_code = 502


class DuplicateFavoriteError(ExplorerBaseException):
    """Raised when attempting to favorite a resource that is already saved locally (400)."""

    default_message = "Este item já está cadastrado na sua lista de favoritos."
    default_code = "duplicate_favorite"
    status_code = 400
