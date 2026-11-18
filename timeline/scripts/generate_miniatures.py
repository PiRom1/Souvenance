from timeline.controls.image_controls import create_miniature
from timeline.models import Image


def run():
    """
    Crée l'aperçu léger des photos existantes qui n'en ont pas. Relançable.
    """

    manquantes = Image.objects.filter(miniature="") | Image.objects.filter(miniature__isnull=True)
    total = manquantes.count()
    for numero, image in enumerate(manquantes, start=1):
        try:
            create_miniature(image)
        except (FileNotFoundError, OSError) as erreur:
            print(f"{numero}/{total} : image {image.pk} ignorée ({erreur})")
            continue
        print(f"{numero}/{total} : aperçu créé pour {image.nom or image.pk}")
