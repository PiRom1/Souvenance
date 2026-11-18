import io
import os
import random
from datetime import date, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image as PILImage

from timeline.controls.image_controls import create_images
from timeline.controls.moment_controls import add_revision, sync_participants
from timeline.models import Moment, Note, User

PREMIERE_ANNEE = 2020
EVENEMENTS_PAR_AN = 6

NOMS = ["Week-end à la mer", "Anniversaire", "Randonnée", "Festival", "Soirée jeux", "Vacances d'été", "Réveillon", "Barbecue",
        "Ski", "Brocante", "Pique-nique", "Mariage", "Concert", "Road trip", "Dîner de Noël", "Fête de la musique",
        "Camping", "Vendanges", "Carnaval", "Cousinade", "Crémaillère", "Marché de Noël", "Sortie vélo", "Plage"]
LIEUX = ["Brest", "Lyon", "Annecy", "Quiberon", "Nantes", "Bordeaux", "Lille", "Rennes", "Chamonix", "Marseille", "Strasbourg", "Biarritz"]
DEBUTS = ["On a fini par arriver", "Franchement,", "Personne ne s'y attendait :", "Petit souvenir :", "Je retiens surtout que",
          "Bon, il faut le dire,", "Ce jour-là,", "Impossible d'oublier que"]
MILIEUX = ["Paul a perdu ses clés dans le sable", "Lise a gagné à tous les jeux", "il a plu pendant six heures", "Didier a refait la même blague dix fois",
           "on a mangé beaucoup trop de fromage", "Emma a conduit sans GPS", "la musique était bien trop forte", "Mathieu s'est endormi sur le canapé",
           "Alice a tout photographié", "Pierrick a cuisiné pour douze", "Romain a raté le dernier train", "le soleil s'est enfin montré"]
FINS = ["et on en rigole encore.", "mais c'était parfait.", "on y retourne l'an prochain.", "personne n'a voulu rentrer.",
        "c'est la photo qui le prouve.", "on n'a pas dormi.", "et c'était déjà fini.", "bref, une belle journée."]
LEGENDES = ["Avant la pluie", "Le fameux moment", "Tout le monde est là", "Dernière photo", "On ne sait plus pourquoi", "Au coucher du soleil"]


def texte(rng):
    phrases = [f"{rng.choice(DEBUTS)} {rng.choice(MILIEUX)} {rng.choice(FINS)}" for _ in range(rng.randint(1, 3))]
    return " ".join(phrases)


def photo(rng, nom):
    """
    Une image sans intérêt : un bruit aléatoire ou une couleur unie
    """

    if rng.random() < 0.5:
        image = PILImage.frombytes("RGB", (400, 300), os.urandom(400 * 300 * 3))
    else:
        image = PILImage.new("RGB", (800, 600), (rng.randint(40, 230), rng.randint(40, 230), rng.randint(40, 230)))
    tampon = io.BytesIO()
    image.save(tampon, "JPEG", quality=80)
    return SimpleUploadedFile(nom, tampon.getvalue(), "image/jpeg")


def jours_aleatoires(rng, annee, nombre):
    fin = min(date(annee, 12, 31), date.today())
    total = (fin - date(annee, 1, 1)).days
    return sorted(date(annee, 1, 1) + timedelta(days=rng.randint(0, total)) for _ in range(nombre))


def run():
    """
    Génère des événements factices (6 par an depuis 2020, ponctuels ou longs, ~5 notes chacun, parfois des photos).
    Ajoute à chaque lancement : à utiliser sur une base de test.
    """

    rng = random.Random()
    membres = list(User.objects.all())
    if len(membres) < 3:
        print("Il faut des utilisateurs : lance d'abord `runscript create_users`.")
        return

    nb_moments = nb_notes = nb_photos = 0
    for annee in range(PREMIERE_ANNEE, date.today().year + 1):
        for debut in jours_aleatoires(rng, annee, EVENEMENTS_PAR_AN):
            fin = debut + timedelta(days=rng.randint(1, 14)) if rng.random() < 0.5 else None
            participants = rng.sample(membres, rng.randint(3, len(membres)))
            moment = Moment.objects.create(
                nom=f"{rng.choice(NOMS)} {annee}", description=texte(rng), date_debut=debut, date_fin=fin,
                lieu=rng.choice(LIEUX), createur=rng.choice(participants),
            )
            sync_participants(moment, participants)
            add_revision(moment, moment.createur)
            nb_moments += 1

            for _ in range(max(1, round(rng.gauss(5, 2)))):
                jours = (fin - debut).days if fin else 0
                note = Note.objects.create(
                    moment=moment, auteur=rng.choice(participants), texte=texte(rng),
                    date=debut + timedelta(days=rng.randint(0, jours)),
                    lieu=rng.choice(LIEUX) if rng.random() < 0.2 else "",
                )
                nb_notes += 1
                if rng.random() < 0.4:
                    fichiers = [photo(rng, f"demo_{note.id}_{i}.jpg") for i in range(rng.randint(1, 3))]
                    details = [{"nom": "", "legende": rng.choice(LEGENDES) if rng.random() < 0.5 else None,
                                "date_prise": None, "tags": rng.sample(participants, rng.randint(0, 3))} for _ in fichiers]
                    create_images(note, fichiers, details)
                    nb_photos += len(fichiers)

    print(f"{nb_moments} moments, {nb_notes} notes, {nb_photos} photos créés.")
