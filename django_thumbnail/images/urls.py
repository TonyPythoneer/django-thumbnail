from django.urls import path

from . import views

app_name = "images"

urlpatterns = [
    path("images/", views.images_list, name="images-list"),
    path("images/", views.images_create, name="images-create"),
    path("images/<uuid:image_id>/", views.images_detail, name="images-detail"),
    path("tasks/", views.tasks_create, name="tasks-create"),
    path("tasks/<uuid:task_id>/", views.tasks_detail, name="tasks-detail"),
    path("auth/login/", views.auth_login, name="auth-login"),
    path("auth/logout/", views.auth_logout, name="auth-logout"),
]
