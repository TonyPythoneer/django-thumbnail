from django.urls import path

from . import views

urlpatterns = [
    # API
    path("api/images/", views.images_list, name="images-list"),
    path("api/images/<uuid:image_id>/", views.images_detail, name="images-detail"),
    path("api/tasks/", views.tasks_create, name="tasks-create"),
    path("api/tasks/<uuid:task_id>/", views.tasks_detail, name="tasks-detail"),
    path("api/auth/login/", views.auth_login, name="auth-login"),
    path("api/auth/logout/", views.auth_logout, name="auth-logout"),
    # HTML
    path("login/", views.html_login, name="login"),
    path("logout/", views.html_logout, name="html-logout"),
    path("", views.gallery, name="gallery"),
    path("upload/", views.upload, name="upload"),
    path("images/<uuid:image_id>/delete/", views.image_delete, name="image-delete"),
]
