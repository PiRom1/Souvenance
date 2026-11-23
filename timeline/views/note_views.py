from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from timeline.controls.image_controls import create_images, date_par_defaut, ensure_thumbnail, lire_progression, sync_tags
from timeline.forms import ImageForm, ImageFormSet, NoteForm
from timeline.models import Image, Moment, Note

NEW_IMAGE_PREFIX = "new-{}"


def _new_image_forms(request, form):
    """
    Un formulaire de détails (légende, tags...) par photo téléversée, rempli côté navigateur dès la sélection.
    Appelé une fois `form` valide.
    """

    nombre = len(form.cleaned_data["images"])
    image_forms = [ImageForm(request.POST, prefix=NEW_IMAGE_PREFIX.format(i)) for i in range(nombre)]
    invalides = [str(i + 1) for i, image_form in enumerate(image_forms) if not image_form.is_valid()]
    if invalides:
        form.add_error(None, f"Détails invalides pour les photos n° {', '.join(invalides)}. Re-sélectionne les fichiers.")
        return None
    return [image_form.cleaned_data for image_form in image_forms]


MESSAGE_NOTE_VIDE = "Une note doit contenir du texte ou au moins une photo."


def _note_non_vide(form, photos_conservees=0):
    """
    Une note a du texte ou au moins une photo (déjà sur la note et gardée, ou nouvelle). Sinon l'erreur est
    posée sur le formulaire. Appelé une fois `form` valide.
    """

    if form.cleaned_data["texte"].strip() or form.cleaned_data["images"] or photos_conservees:
        return True
    form.add_error(None, MESSAGE_NOTE_VIDE)
    return False


def _render_form(request, form, moment, titre, **extra):
    context = {
        "form": form,
        "moment": moment,
        "titre": titre,
        "empty_image_form": ImageForm(prefix=NEW_IMAGE_PREFIX.format("__i__")),
        "date_defaut": moment.date_debut.isoformat(),
        **extra,
    }
    return render(request, "timeline/note/note_form.html", context)


@login_required
def note_add(request, moment_id):
    """
    Ajout d'une note (texte et/ou photos avec leurs détails) sur un moment
    """

    moment = get_object_or_404(Moment, id=moment_id)
    form = NoteForm(request.POST or None, request.FILES or None, moment=moment)
    if form.is_valid() and _note_non_vide(form):
        details = _new_image_forms(request, form)
        if details is not None:
            with transaction.atomic():
                note = form.save(commit=False)
                note.moment = moment
                note.auteur = request.user
                note.save()
                create_images(note, form.cleaned_data["images"], details, request.POST.get("progress_token"))
            return redirect("moment", id=moment.id)
    return _render_form(request, form, moment, "Nouvelle note")


@login_required
def note_edit(request, id):
    """
    Modification d'une note, de ses photos existantes et ajout de nouvelles (réservé à son auteur)
    """

    note = get_object_or_404(Note.objects.select_related("moment"), id=id)
    if note.auteur != request.user:
        raise PermissionDenied

    form = NoteForm(request.POST or None, request.FILES or None, instance=note, moment=note.moment)
    formset = ImageFormSet(request.POST or None, queryset=Image.objects.filter(note=note), prefix="photos")
    if form.is_valid() and formset.is_valid() and _note_non_vide(form, len(formset.forms) - len(formset.deleted_forms)):
        details = _new_image_forms(request, form)
        if details is not None:
            with transaction.atomic():
                form.save()
                formset.save()
                for image_form in formset.forms:
                    if image_form not in formset.deleted_forms:
                        sync_tags(image_form.instance, image_form.cleaned_data["tags"])
                create_images(note, form.cleaned_data["images"], details, request.POST.get("progress_token"))
                ensure_thumbnail(note.moment)
            return redirect("moment", id=note.moment_id)
    return _render_form(request, form, note.moment, "Modifier la note", formset=formset, note=note)


@login_required
def note_delete(request, id):
    """
    Suppression d'une note et de ses photos, après confirmation (réservé à son auteur)
    """

    note = get_object_or_404(Note.objects.select_related("moment"), id=id)
    if note.auteur != request.user:
        raise PermissionDenied

    if request.method == "POST":
        with transaction.atomic():
            note.images.all().delete()
            note.delete()
            ensure_thumbnail(note.moment)
        return redirect("moment", id=note.moment_id)
    context = {
        "titre": "Supprimer la note",
        "objet": "cette note",
        "details": f"Ses {note.images.count()} photo(s) seront supprimées aussi.",
        "retour": reverse("note_edit", args=[note.id]),
    }
    return render(request, "timeline/confirm_delete.html", context)


@login_required
def note_progress(request, token):
    """
    Avancement du traitement des photos d'une note en cours d'envoi (interrogé par la barre de progression)
    """

    return JsonResponse(lire_progression(token))
