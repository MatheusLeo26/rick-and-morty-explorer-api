"""
Custom DRF exception handler that converts domain and integration exceptions
into standardized JSON responses.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from explorer.exceptions import ExplorerBaseException


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    Intercepts ExplorerBaseException subclasses and standard DRF exceptions
    to return a consistent error payload structure.
    """
    if isinstance(exc, ExplorerBaseException):
        payload = {
            "error": True,
            "code": exc.code,
            "message": exc.message,
            "status_code": exc.status_code,
            "details": exc.details,
        }
        return Response(payload, status=exc.status_code)

    response = exception_handler(exc, context)
    if response is not None:
        custom_data = {
            "error": True,
            "code": "validation_or_request_error",
            "message": "Erro na validação dos parâmetros ou na requisição.",
            "status_code": response.status_code,
            "details": response.data,
        }
        response.data = custom_data
    return response
