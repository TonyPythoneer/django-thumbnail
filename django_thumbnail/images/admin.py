from django.contrib import admin
from .models import Image, ImageTask


class ImageTaskInline(admin.TabularInline):
    model = ImageTask
    extra = 0
    readonly_fields = ("celery_task_id", "status", "error_message", "created_at", "updated_at")


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "user", "current_status", "created_at")
    search_fields = ("original_filename", "user__email")
    readonly_fields = ("id", "original_key", "thumbnail_key", "created_at")
    inlines = [ImageTaskInline]


@admin.register(ImageTask)
class ImageTaskAdmin(admin.ModelAdmin):
    list_display = ("image", "status", "celery_task_id", "created_at")
    list_filter = ("status",)
    readonly_fields = ("id", "celery_task_id", "created_at", "updated_at")
