import json
from functools import wraps

from django.http import HttpRequest, JsonResponse


def login_required_json(view):
    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "auth required"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def parse_json_body(request: HttpRequest) -> dict | None:
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return None
