from django.http import JsonResponse
from rest_framework.authtoken.models import Token


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return JsonResponse({
                "status": "error",
                "message": "Authorization header required"
            }, status=403)

        parts = auth_header.split()

        if len(parts) != 2 or parts[0] != "Token":
            return JsonResponse({
                "status": "error",
                "message": "Invalid authorization format"
            }, status=403)

        token_key = parts[1]

        try:
            token = Token.objects.get(key=token_key)
        except Token.DoesNotExist:
            return JsonResponse({
                "status": "error",
                "message": "Invalid token"
            }, status=403)

        user = token.user

        if not user.is_staff:
            return JsonResponse({
                "status": "error",
                "message": "Admin only"
            }, status=403)

        request.user = user

        return view_func(request, *args, **kwargs)

    return wrapper