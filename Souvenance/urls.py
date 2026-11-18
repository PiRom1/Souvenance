from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path
from django.views.static import serve

urlpatterns = [
    path("", include("timeline.urls")),
    path("admin/", admin.site.urls),
]

# Photos : servies par Django (dev et prod) mais réservées aux utilisateurs connectés.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", login_required(serve), {"document_root": settings.MEDIA_ROOT}),
]
