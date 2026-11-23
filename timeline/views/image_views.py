from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.templatetags.static import static
from django.views.decorators.http import require_POST

from timeline.controls.image_controls import ensure_thumbnail, sync_tags
from timeline.models import Image, User


@login_required
@require_POST
def image_tags(request, id):
    """
    Remplace les personnes taguées sur une photo. Ouvert à tous les membres, pas seulement à l'auteur de la note.
    """

    image = get_object_or_404(Image, id=id)
    users = list(User.objects.filter(id__in=request.POST.getlist("tags")).order_by("username"))
    sync_tags(image, users)
    return JsonResponse({"tags": [
        {"username": user.username, "nom": str(user), "avatar": static(f"timeline/img/{user.username}.png")}
        for user in users
    ]})


@login_required
@require_POST
def image_delete(request, id):
    """
    Supprime une photo et ses fichiers. Ouvert à tous les membres (les doublons viennent souvent de quelqu'un d'autre) ;
    la vignette du moment est recalculée si c'était elle.
    """

    image = get_object_or_404(Image.objects.select_related("note__moment"), id=id)
    moment = image.note.moment if image.note else None
    image.delete()
    if moment:
        moment.refresh_from_db()
        ensure_thumbnail(moment)
    return JsonResponse({"ok": True})
