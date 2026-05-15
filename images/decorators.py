from django.http import HttpRequest, JsonResponse


def login_required_json(view):
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "auth required"}, status=401)
        return view(request, *args, **kwargs)

    return wrapper
