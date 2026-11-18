from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from timeline.controls.image_controls import create_images, date_par_defaut, ensure_thumbnail, sync_tags
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
    if form.is_valid():
        details = _new_image_forms(request, form)
        if details is not None:
            with transaction.atomic():
                note = form.save(commit=False)
                note.moment = moment
                note.auteur = request.user
                note.save()
                create_images(note, form.cleaned_data["images"], details)
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
    if form.is_valid() and formset.is_valid():
        details = _new_image_forms(request, form)
        if details is not None:
            with transaction.atomic():
                form.save()
                formset.save()
                for image_form in formset.forms:
                    if image_form not in formset.deleted_forms:
                        sync_tags(image_form.instance, image_form.cleaned_data["tags"])
                create_images(note, form.cleaned_data["images"], details)
                ensure_thumbnail(note.moment)
            return redirect("moment", id=note.moment_id)
    return _render_form(request, form, note.moment, "Modifier la note", formset=formset, note=note)
