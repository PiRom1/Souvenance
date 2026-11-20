from django.contrib.auth import views as auth_views
from django.urls import path

from timeline.views import app_views, image_views, moment_views, note_views

urlpatterns = [
    # Auth
    path("login/", auth_views.LoginView.as_view(template_name="timeline/auth/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Generic
    path("", app_views.home, name="home"),

    # Moment
    path("moment/ajouter", moment_views.moment_add, name="moment_add"),
    path("moment/<int:id>", moment_views.moment, name="moment"),
    path("moment/<int:id>/photos", moment_views.moment_photos, name="moment_photos"),
    path("moment/<int:id>/modifier", moment_views.moment_edit, name="moment_edit"),
    path("moment/<int:id>/vignette/<int:image_id>", moment_views.moment_thumbnail, name="moment_thumbnail"),

    # Note
    path("moment/<int:moment_id>/note/ajouter", note_views.note_add, name="note_add"),
    path("note/<int:id>/modifier", note_views.note_edit, name="note_edit"),

    # Image
    path("image/<int:id>/tags", image_views.image_tags, name="image_tags"),
]
