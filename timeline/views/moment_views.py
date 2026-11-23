from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms import DateField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from timeline.controls.book_controls import membres, photos_du_moment, preparer_livre
from timeline.controls.image_controls import set_thumbnail
from timeline.controls.moment_controls import add_revision, delete_moment, moments_proches, sync_participants
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
        "membres": membres(),
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
    context = {"moment": moment, "images": images, "personnes_taguees": personnes_taguees, "est_participant": est_participant, "membres": membres()}
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
    Modification d'un moment (ouverte à tous les membres)
    """

    moment = get_object_or_404(Moment, id=id)
    form = MomentForm(request.POST or None, instance=moment)
    if form.is_valid():
        with transaction.atomic():
            description_changee = "description" in form.changed_data
            moment = form.save()
            sync_participants(moment, form.cleaned_data["participants"])
            if description_changee:
                add_revision(moment, request.user)
        return redirect("moment", id=moment.id)
    context = {"form": form, "titre": "Modifier le moment", "peut_supprimer": moment.createur == request.user}
    return render(request, "timeline/moment/moment_form.html", context)


@login_required
def moment_delete(request, id):
    """
    Suppression d'un moment avec ses notes et ses photos, après confirmation (réservé à son créateur)
    """

    moment = get_object_or_404(Moment, id=id)
    if moment.createur != request.user:
        raise PermissionDenied

    if request.method == "POST":
        delete_moment(moment)
        return redirect("home")
    context = {
        "titre": "Supprimer le moment",
        "objet": f"le moment « {moment.nom} »",
        "details": f"Ses {moment.notes.count()} note(s) et ses {Image.objects.filter(note__moment=moment).count()} photo(s) seront supprimées aussi.",
        "retour": reverse("moment_edit", args=[moment.id]),
    }
    return render(request, "timeline/confirm_delete.html", context)


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


@login_required
@require_GET
def moments_proches_json(request):
    """
    Les moments proches (à une semaine près) d'une période en cours de saisie, pour l'avertissement de doublon
    """

    champ = DateField(required=False)
    try:
        debut = champ.clean(request.GET.get("du"))
        fin = champ.clean(request.GET.get("au"))
    except ValidationError:
        debut = fin = None
    if debut is None:
        return JsonResponse({"moments": []})

    def periode(moment):
        if moment.est_ponctuel:
            return f"{moment.date_debut:%d/%m/%Y}"
        return f"{moment.date_debut:%d/%m/%Y} au {moment.date_fin:%d/%m/%Y}"

    return JsonResponse({"moments": [
        {"nom": moment.nom, "periode": periode(moment), "url": reverse("moment", args=[moment.id])}
        for moment in moments_proches(debut, fin)
    ]})
