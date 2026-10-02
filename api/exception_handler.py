import traceback
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that catches ALL exceptions and returns
    a proper JSON response instead of a bare 500 HTML page.
    
    This makes debugging much easier — the actual error + traceback
    will be visible in the API response body.
    """
    # Call DRF's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # DRF handled it (e.g. 400, 401, 403, 404)
        return response

    # DRF did NOT handle it — this is an unhandled exception (500)
    # Log the full traceback to console
    print(f"\n{'='*60}")
    print(f"UNHANDLED EXCEPTION in {context.get('view', 'unknown view')}")
    print(f"{'='*60}")
    traceback.print_exc()
    print(f"{'='*60}\n")

    # Return a proper JSON 500 response with error details
    return Response(
        {
            'error': str(exc),
            'type': type(exc).__name__,
            'detail': traceback.format_exc(),
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
