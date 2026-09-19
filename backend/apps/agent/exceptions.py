"""Consistent, safe API error handling.

Internal details (stack traces, SQL, provider errors) are logged but never
returned to the client. The client always receives a human, useful message.
"""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if response is None:
        # Unhandled exception: log the technical detail, return a neutral one.
        logger.exception("Unhandled API error", exc_info=exc)
        return Response(
            {"detail": "Ocurrió un error inesperado. Intenta nuevamente en un momento."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if response.status_code >= 500:
        logger.error(
            "Server error in %s: %s",
            context.get("view"),
            exc,
            exc_info=True,
        )
        response.data = {
            "detail": "Ocurrió un error inesperado. Intenta nuevamente en un momento."
        }

    return response
