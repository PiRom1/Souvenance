from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Coalesce

from timeline.models import Image, Moment, MomentRevision, UserForMoment


def sync_participants(moment, users):
    """
    Aligne les participants d'un moment avec la liste donnée (le créateur reste toujours participant)
    """

    voulus = set(users) | {moment.createur}
    UserForMoment.objects.filter(moment=moment).exclude(user__in=voulus).delete()
    deja_la = set(UserForMoment.objects.filter(moment=moment).values_list("user_id", flat=True))
    UserForMoment.objects.bulk_create(UserForMoment(moment=moment, user=u) for u in voulus if u.pk not in deja_la)


def add_revision(moment, auteur):
    """
    Historise la description actuelle du moment
    """

    MomentRevision.objects.create(moment=moment, description=moment.description, auteur=auteur)


def filter_moments(filtres):
    """
    Moments correspondant aux filtres (clés absentes ou vides ignorées).
    Une période filtre les moments qui la chevauchent.
    """

    moments = Moment.objects.select_related("thumbnail")
    if filtres.get("q"):
        moments = moments.filter(Q(nom__icontains=filtres["q"]) | Q(description__icontains=filtres["q"]))
    if filtres.get("lieu"):
        moments = moments.filter(lieu__icontains=filtres["lieu"])
    if filtres.get("du"):
        moments = moments.annotate(fin=Coalesce("date_fin", "date_debut")).filter(fin__gte=filtres["du"])
    if filtres.get("au"):
        moments = moments.filter(date_debut__lte=filtres["au"])
    for user in filtres.get("participants") or []:
        moments = moments.filter(users_for_moment__user=user)
    return moments


def delete_moment(moment):
    """
    Supprime un moment, ses notes et leurs photos (les photos ne sont pas liées en cascade, et leurs fichiers
    partent avec elles)
    """

    with transaction.atomic():
        Image.objects.filter(note__moment=moment).delete()
        moment.delete()


ECART_MOMENT_PROCHE = timedelta(days=7)


def moments_proches(debut, fin):
    """
    Moments dont la période chevauche, à une semaine près, celle donnée (fin vide : moment ponctuel)
    """

    fin = fin or debut
    return (Moment.objects.annotate(fin_effective=Coalesce("date_fin", "date_debut"))
            .filter(fin_effective__gte=debut - ECART_MOMENT_PROCHE, date_debut__lte=fin + ECART_MOMENT_PROCHE)
            .order_by("date_debut"))
