import math
from datetime import date

from django.db.models import Max, Min
from django.db.models.functions import Coalesce

from timeline.models import Moment

# Demi-largeur d'une pastille sur la frise (sa vignette et son titre), en jours
DEMI_PASTILLE = 20   # demi-largeur d'une pastille, en jours
MAX_ETAGES = 12
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def plage_annees(annee_courante):
    """
    Toutes les années à proposer dans le sélecteur : du premier moment à l'année courante (ou au dernier moment)
    """

    bornes = Moment.objects.aggregate(premiere=Min("date_debut"), derniere=Max(Coalesce("date_fin", "date_debut")))
    premiere = bornes["premiere"].year if bornes["premiere"] else annee_courante
    derniere = bornes["derniere"].year if bornes["derniere"] else annee_courante
    return list(range(min(premiere, annee_courante), max(derniere, annee_courante) + 1))


AMPLITUDE_ONDE = 1.3   # rem
POINTS_AXE = 160       # points du tracé par année
UNITES_AN = 1000       # largeur d'une année dans le viewBox du tracé
JOURS_PAR_AN = 365.2425
LARGEUR_BOUCLE = 34    # unités parcourues le long de l'axe par une boucle
RAYON_BOUCLE = 13      # unités de hauteur du viewBox
POINTS_BOUCLE = 28
BOUCLES_PAR_AN = 4
INCLINAISONS = [-7, -4, -2, 3, 5, 8, -5, 2, 6, -3]


def onde(annees):
    """
    Décalage vertical (en rem, positif vers le bas) de l'axe ondulant, à une position exprimée en années depuis le début
    """

    return AMPLITUDE_ONDE * (math.sin(annees * 2 * math.pi * 3.2) + 0.45 * math.sin(annees * 2 * math.pi * 8.1 + 1.3)) / 1.45


def _trace(debut, fin, boucles=()):
    """
    Tracé SVG (1 unité de hauteur = 1/16 rem, 1000 unités de largeur par année) de l'axe entre deux positions en unités.
    Chaque boucle est un tuple (position de départ, sens) : le tracé s'enroule sur lui-même puis reprend sa route
    """

    nombre = max(2, round((fin - debut) / UNITES_AN * POINTS_AXE))
    points = []

    def ajouter(x, y):
        points.append(f"{'M' if not points else 'L'}{x:.1f} {y:.1f}")

    boucles = sorted(b for b in boucles if debut <= b[0] and b[0] + LARGEUR_BOUCLE <= fin)
    x = debut
    pas = (fin - debut) / nombre
    while x < fin - 1e-6:
        if boucles and x >= boucles[0][0] - 1e-6:
            depart, sens = boucles.pop(0)
            base_y = 24 + onde(depart / UNITES_AN) * 16
            c = LARGEUR_BOUCLE / (2 * math.pi)
            for i in range(POINTS_BOUCLE + 1):
                phi = 2 * math.pi * i / POINTS_BOUCLE
                ajouter(depart + c * phi + RAYON_BOUCLE * math.sin(phi), base_y + sens * RAYON_BOUCLE * (math.cos(phi) - 1))
            x = depart + LARGEUR_BOUCLE
            continue
        ajouter(x, 24 + onde(x / UNITES_AN) * 16)
        x += pas
    ajouter(fin, 24 + onde(fin / UNITES_AN) * 16)
    return " ".join(points)


def choisir_boucles(largeur, nombre_annees, pastilles_brutes):
    """
    Emplacements des boucles de l'axe : au milieu des plus grands espaces entre deux pastilles (jamais sous une
    pastille ni sur une période étalée), avec un sens alterné. Positions en unités ; renvoie [(position, sens)]
    """

    marge = LARGEUR_BOUCLE + 12
    bornes = sorted({0, largeur} | {debut for debut, _ in pastilles_brutes})
    occupe = [(debut, fin) for debut, fin in pastilles_brutes if fin > debut]

    candidats = []
    for a, b in zip(bornes, bornes[1:]):
        if b - a < marge + 20:
            continue
        depart = (a + b) / 2 - LARGEUR_BOUCLE / 2
        if any(debut < depart + marge and fin > depart - 10 for debut, fin in occupe):
            continue
        candidats.append((b - a, depart))

    candidats.sort(reverse=True)
    retenus = sorted(depart for _, depart in candidats[:BOUCLES_PAR_AN * nombre_annees])
    return [(depart, 1 if i % 2 else -1) for i, depart in enumerate(retenus)]


def _trouver_place(places, jour):
    """
    Premier emplacement libre (côté, étage) pour une pastille posée au jour donné : on monte d'un étage tant
    qu'elle chevaucherait une pastille déjà posée au même étage et du même côté de l'axe
    """

    for etage in range(MAX_ETAGES):
        for cote in ("haut", "bas"):
            if not any(p["cote"] == cote and p["etage"] == etage and abs(p["jour"] - jour) < 2 * DEMI_PASTILLE
                       for p in places):
                return cote, etage
    return "haut", MAX_ETAGES


def construire_frise(moments, annees):
    """
    La frise continue de toutes les années, mises bout à bout : chaque moment n'y figure qu'une fois, positionné en %
    de la largeur totale (au jour près) et réparti sur des étages au-dessus ou en dessous de l'axe
    """

    debut_frise = date(annees[0], 1, 1)
    total_jours = (date(annees[-1], 12, 31) - debut_frise).days + 1
    largeur = total_jours * UNITES_AN / JOURS_PAR_AN

    def jours(jour):
        return (jour - debut_frise).days

    def pourcent(nombre_de_jours):
        return nombre_de_jours / total_jours * 100

    def unites(nombre_de_jours):
        return nombre_de_jours / total_jours * largeur

    moments = sorted(moments, key=lambda m: (m.date_debut, m.id))
    places, pastilles, brutes = [], [], []
    for moment in moments:
        debut = jours(moment.date_debut)
        fin = jours(moment.date_fin or moment.date_debut)
        cote, etage = _trouver_place(places, debut)
        places.append({"cote": cote, "etage": etage, "jour": debut})
        brutes.append((unites(debut), unites(fin)))
        pastilles.append({
            "moment": moment,
            "x": f"{pourcent(debut):.3f}",
            "est_etale": fin > debut,
            "decalage": f"{onde(unites(debut) / UNITES_AN):.2f}",
            "trace": _trace(unites(debut), unites(fin)) if fin > debut else "",
            "cote": cote,
            "etage": etage,
            "inclinaison": INCLINAISONS[(moment.id * 7 + moment.date_debut.year) % len(INCLINAISONS)],
            "participants": [ufm.user for ufm in moment.users_for_moment.all()],
        })

    liste_annees, mois = [], []
    for annee in annees:
        premier, dernier = date(annee, 1, 1), date(annee, 12, 31)
        liste_annees.append({
            "annee": annee,
            "x": f"{pourcent(jours(premier)):.3f}",
            "largeur": f"{pourcent((dernier - premier).days + 1):.3f}",
            "nombre": sum(1 for m in moments if m.date_debut <= dernier and (m.date_fin or m.date_debut) >= premier),
        })
        for numero in range(1, 13):
            debut_mois = date(annee, numero, 1)
            suivant = date(annee + (numero == 12), numero % 12 + 1, 1)
            mois.append({
                "nom": MOIS[numero - 1],
                "x": f"{pourcent(jours(debut_mois)):.3f}",
                "largeur": f"{pourcent((suivant - debut_mois).days):.3f}",
                "debut_annee": numero == 1,
            })

    boucles = choisir_boucles(largeur, len(annees), brutes)
    return {
        "annees": liste_annees,
        "nombre_annees": len(annees),
        "pastilles": pastilles,
        "mois": mois,
        "axe": _trace(0, largeur, boucles),
        "largeur_trace": round(largeur),
        "etages_haut": max([p["etage"] + 1 for p in pastilles if p["cote"] == "haut"], default=1),
        "etages_bas": max([p["etage"] + 1 for p in pastilles if p["cote"] == "bas"], default=1),
    }
