import io
from http import HTTPMethod, HTTPStatus
from typing import cast

from celery.result import AsyncResult
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .decorators import login_required_json, parse_json_body
from .forms import LoginForm, UploadForm
from .models import Image, ImageStatus, ImageTask
from .storage import public_s3

# ---------- Images ----------


@login_required_json
@require_http_methods([HTTPMethod.GET, HTTPMethod.POST])
def images_list(request: HttpRequest) -> JsonResponse:
    if request.method == HTTPMethod.POST:
        body = parse_json_body(request)
        if body is None:
            return JsonResponse({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
        filename = body.get("filename")
        if not filename:
            return JsonResponse({"error": "filename required"}, status=HTTPStatus.BAD_REQUEST)
        image = Image.create_with_key(cast(User, request.user), filename)
        presign_url = public_s3.presign_put(image.original_key)
        return JsonResponse(
            {"image_id": str(image.id), "upload_url": presign_url},
            status=HTTPStatus.CREATED,
        )

    qs = Image.objects.for_user(cast(User, request.user)).prefetch_related("tasks")
    return JsonResponse({"images": [i.to_dict() for i in qs]})


@login_required_json
@require_http_methods([HTTPMethod.DELETE])
def images_detail(request: HttpRequest, image_id: str) -> JsonResponse:
    image = Image.objects.for_user(cast(User, request.user)).filter(id=image_id).first()
    if not image:
        return JsonResponse({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    image.delete_from_storage()
    image.delete()
    return JsonResponse({"deleted": image_id})


# ---------- Tasks ----------


@login_required_json
@require_http_methods([HTTPMethod.POST])
def tasks_create(request: HttpRequest) -> JsonResponse:
    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
    image_id = body.get("image_id")
    if not image_id:
        return JsonResponse({"error": "image_id required"}, status=HTTPStatus.BAD_REQUEST)

    image = Image.objects.for_user(cast(User, request.user)).filter(id=image_id).first()
    if not image:
        return JsonResponse({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    task = ImageTask.create_and_dispatch(image)
    return JsonResponse(task.to_dict(), status=HTTPStatus.CREATED)


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
def auth_login(request: HttpRequest) -> JsonResponse:
    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"error": "invalid json"}, status=HTTPStatus.BAD_REQUEST)
    username = body.get("username") or body.get("email")
    password = body.get("password")
    user = authenticate(request, username=username, password=password)
    if not user:
        return JsonResponse({"error": "invalid credentials"}, status=HTTPStatus.UNAUTHORIZED)

    login(request, user)
    return JsonResponse({"user": cast(User, user).username})


@csrf_exempt
@require_http_methods([HTTPMethod.POST])
def auth_logout(request: HttpRequest) -> JsonResponse:
    logout(request)
    return JsonResponse({"ok": True})


# ---------- HTML Views ----------


def _gallery_row(img: Image, task: ImageTask | None) -> dict:
    return {
        "id": str(img.id),
        "original_filename": img.original_filename,
        "status": task.status if task else ImageStatus.PENDING,
        "task_id": str(task.id) if task else "",
        "original_url": public_s3.presign_get(img.original_key),
        "thumbnail_url": public_s3.presign_get(img.thumbnail_key)
        if task and task.status == ImageStatus.DONE
        else None,
        "created_at": img.created_at,
    }


def html_login(request: HttpRequest):
    if request.user.is_authenticated:
        return redirect("gallery")
    form = LoginForm(request.POST or None)
    if request.method == HTTPMethod.POST and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user:
            login(request, user)
            return redirect("gallery")
        form.add_error(None, "Invalid credentials")
    return render(request, "auth/login.html", {"form": form})


@require_http_methods([HTTPMethod.POST])
def html_logout(request: HttpRequest):
    logout(request)
    return redirect("login")


@login_required(login_url="login")
def gallery(request: HttpRequest):
    images_qs = Image.objects.for_user(cast(User, request.user)).prefetch_related("tasks")
    rows = [_gallery_row(img, img.latest_task()) for img in images_qs]
    return render(request, "images/gallery.html", {"images": rows})


@login_required(login_url="login")
def upload(request: HttpRequest):
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == HTTPMethod.POST and form.is_valid():
        f = form.cleaned_data["file"]
        image = Image.create_with_key(cast(User, request.user), f.name)
        image.upload_original(io.BytesIO(f.read()))
        ImageTask.create_and_dispatch(image)
        return redirect("gallery")
    return render(request, "images/upload.html", {"form": form})


@login_required(login_url="login")
@require_http_methods([HTTPMethod.POST])
def image_delete(request: HttpRequest, image_id: str):
    image = Image.objects.for_user(cast(User, request.user)).filter(id=image_id).first()
    if image:
        image.delete_from_storage()
        image.delete()
    return redirect("gallery")
