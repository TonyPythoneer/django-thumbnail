import json
from http import HTTPMethod, HTTPStatus

from celery.result import AsyncResult
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Image, ImageTask
from .tasks import generate_thumbnail
from .utils import S3, login_required_json


def parse_json_body(view_func):
    def wrapper(request: HttpRequest, *args, **kwargs):
        try:
            body = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse(
                {"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST
            )
        return view_func(request, body, *args, **kwargs)

    return wrapper


# ---------- Images ----------


@csrf_exempt
@login_required_json
@require_http_methods([HTTPMethod.GET])
def images_list(request: HttpRequest) -> JsonResponse:
    qs = Image.objects.for_user(request.user)
    return JsonResponse({"images": [i.to_dict() for i in qs]})


@csrf_exempt
@login_required_json
@require_http_methods([HTTPMethod.POST])
@parse_json_body
def images_create(request: HttpRequest, body: dict) -> JsonResponse:
    filename = body.get("filename")
    if not filename:
        return JsonResponse(
            {"error": "filename required"}, status=HTTPStatus.BAD_REQUEST
        )

    image = Image.create_with_key(request.user, filename)
    presign_url = S3.presign_upload_url(image)

    return JsonResponse(
        {
            "image_id": str(image.id),
            "upload_url": presign_url,
        },
        status=HTTPStatus.CREATED,
    )


@csrf_exempt
@login_required_json
@require_http_methods([HTTPMethod.DELETE])
def images_detail(request: HttpRequest, image_id: str) -> JsonResponse:
    image = Image.objects.for_user(request.user).filter(id=image_id).first()
    if not image:
        return JsonResponse({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    for k in [image.original_key, image.thumbnail_key]:
        if k:
            S3.client().delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=k)
    image.delete()
    return JsonResponse({"deleted": image_id})


# ---------- Tasks ----------


@csrf_exempt
@login_required_json
@require_http_methods([HTTPMethod.POST])
@parse_json_body
def tasks_create(request: HttpRequest, body: dict) -> JsonResponse:
    image_id = body.get("image_id")
    if not image_id:
        return JsonResponse(
            {"error": "image_id required"}, status=HTTPStatus.BAD_REQUEST
        )

    image = Image.objects.for_user(request.user).filter(id=image_id).first()
    if not image:
        return JsonResponse({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    task = ImageTask.objects.create(image=image)
    async_result = generate_thumbnail.delay(str(task.id))
    task.celery_task_id = async_result.id
    task.save(update_fields=["celery_task_id", "updated_at"])

    return JsonResponse(task.to_dict(), status=HTTPStatus.CREATED)


@csrf_exempt
@login_required_json
@require_http_methods([HTTPMethod.GET, HTTPMethod.DELETE])
def tasks_detail(request: HttpRequest, task_id: str) -> JsonResponse:
    task = (
        ImageTask.objects.select_related("image")
        .filter(id=task_id, image__user=request.user)
        .first()
    )
    if not task:
        return JsonResponse({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    if request.method == HTTPMethod.DELETE:
        if task.celery_task_id:
            AsyncResult(task.celery_task_id).revoke(terminate=True)
        task.mark_failed("revoked")
        return JsonResponse({"revoked": task_id})

    return JsonResponse(task.to_dict())


# ---------- Auth ----------


@csrf_exempt
@require_http_methods([HTTPMethod.POST])
@parse_json_body
def auth_login(request: HttpRequest, body: dict) -> JsonResponse:
    username = body.get("username") or body.get("email")
    password = body.get("password")
    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse(
            {"error": "invalid credentials"}, status=HTTPStatus.UNAUTHORIZED
        )

    login(request, user)
    return JsonResponse({"user": user.username})


@csrf_exempt
@require_http_methods([HTTPMethod.POST])
def auth_logout(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({"ok": True})
