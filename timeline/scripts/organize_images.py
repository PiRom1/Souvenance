import os
import shutil

from django.conf import settings

from timeline.models import Image, date_de_rangement


def _deplacer(champ, dossier, jour, appliquer):
    """
    Range le fichier d'un champ image dans <dossier>/<année>/<mois>/ ; renvoie True s'il bouge (ou bougerait)
    """

    if not champ:
        return False
    ancien = champ.name
    nouveau = f"{dossier}/{jour:%Y}/{jour:%m}/{os.path.basename(ancien)}"
    if ancien == nouveau:
        return False
    source = os.path.join(settings.MEDIA_ROOT, ancien)
    if not os.path.exists(source):
        print(f"  fichier introuvable, ignoré : {ancien}")
        return False
    if appliquer:
        destination = os.path.join(settings.MEDIA_ROOT, nouveau)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        racine, extension = os.path.splitext(destination)
        numero = 1
        while os.path.exists(destination):
            destination = f"{racine}_{numero}{extension}"
            numero += 1
        shutil.move(source, destination)
        champ.name = os.path.relpath(destination, settings.MEDIA_ROOT)
    print(f"  {ancien} -> {nouveau}")
    return True


def run(*args):
    """
    Range les photos existantes dans les dossiers de leur date (prise de vue, sinon premier jour du moment).
    Sans argument : montre seulement ce qui bougerait. Avec `--script-args appliquer` : déplace vraiment les fichiers.
    """

    appliquer = "appliquer" in args
    bougees = 0
    for image in Image.objects.select_related("note__moment"):
        jour = date_de_rangement(image)
        deplace_original = _deplacer(image.fichier, "images", jour, appliquer)
        deplace_miniature = _deplacer(image.miniature, "miniatures", jour, appliquer)
        if deplace_original or deplace_miniature:
            bougees += 1
            if appliquer:
                image.save(update_fields=["fichier", "miniature"])
    print(f"{bougees} photo(s) {'rangée(s)' if appliquer else 'à ranger (aperçu seulement : relance avec --script-args appliquer)'}")
