from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from timeline.controls.moment_controls import filter_moments
from timeline.controls.timeline_controls import construire_frise, plage_annees
from timeline.forms import MomentFilterForm


@login_required
def home(request):
    """
    Page d'accueil de Souvenance : une frise continue de toutes les années, filtrable via la query string
    """

    form = MomentFilterForm(request.GET)
    filtres = form.cleaned_data if form.is_valid() else {}
    moments = list(filter_moments(filtres).prefetch_related("users_for_moment__user"))

    annee_courante = date.today().year
    annees = plage_annees(annee_courante)
    try:
        annee_choisie = int(request.GET.get("annee", annee_courante))
    except ValueError:
        annee_choisie = annee_courante
    if annee_choisie not in annees:
        annee_choisie = annee_courante

    context = {
        "form": form,
        "filtres_actifs": any(filtres.values()),
        "frise": construire_frise(moments, annees),
        "annee_choisie": annee_choisie,
        "annee_courante": annee_courante,
    }
    return render(request, "timeline/app/home.html", context)
