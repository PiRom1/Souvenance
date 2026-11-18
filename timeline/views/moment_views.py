from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from timeline.controls.book_controls import photos_du_moment, preparer_livre
from timeline.controls.image_controls import set_thumbnail
from timeline.controls.moment_controls import add_revision, sync_participants
from timeline.forms import MomentForm
from timeline.models import Image, Moment


@login_required
def moment(request, id):
    """
    Le livre d'un moment : titre, description, puis les notes à la suite
    """

    moment = get_object_or_404(Moment.objects.select_related("thumbnail"), id=id)
    participants = [ufm.user for ufm in moment.users_for_moment.select_related("user")]
    livre = preparer_livre(moment)
    context = {
        "moment": moment,
        "participants": participants,
        "est_participant": request.user in participants,
        **livre,
    }
    return render(request, "timeline/moment/moment.html", context)


@login_required
def moment_photos(request, id):
    """
    La photothèque d'un moment : toutes ses photos, filtrables par personne
    """

    moment = get_object_or_404(Moment.objects.select_related("thumbnail"), id=id)
    images, personnes_taguees = photos_du_moment(moment)
    est_participant = moment.users_for_moment.filter(user=request.user).exists()
    context = {"moment": moment, "images": images, "personnes_taguees": personnes_taguees, "est_participant": est_participant}
    return render(request, "timeline/moment/photos.html", context)


@login_required
def moment_add(request):
    """
    Création d'un moment
    """

    form = MomentForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            moment = form.save(commit=False)
            moment.createur = request.user
            moment.save()
            sync_participants(moment, form.cleaned_data["participants"])
            add_revision(moment, request.user)
        return redirect("moment", id=moment.id)
    return render(request, "timeline/moment/moment_form.html", {"form": form, "titre": "Nouveau moment"})


@login_required
def moment_edit(request, id):
    """
    Modification d'un moment (réservé à son créateur)
    """

    moment = get_object_or_404(Moment, id=id)
    if moment.createur != request.user:
        raise PermissionDenied

    form = MomentForm(request.POST or None, instance=moment)
    if form.is_valid():
        with transaction.atomic():
            description_changee = "description" in form.changed_data
            moment = form.save()
            sync_participants(moment, form.cleaned_data["participants"])
            if description_changee:
                add_revision(moment, request.user)
        return redirect("moment", id=moment.id)
    return render(request, "timeline/moment/moment_form.html", {"form": form, "titre": "Modifier le moment"})


@login_required
@require_POST
def moment_thumbnail(request, id, image_id):
    """
    Choix de la vignette d'un moment parmi les photos de ses notes (réservé aux participants)
    """

    moment = get_object_or_404(Moment, id=id)
    if not moment.users_for_moment.filter(user=request.user).exists():
        raise PermissionDenied
    set_thumbnail(moment, get_object_or_404(Image, id=image_id, note__moment=moment))
    return redirect("moment_photos" if request.POST.get("retour") == "photos" else "moment", id=moment.id)
