import io
import os
from datetime import datetime, time

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image as PILImage
from PIL import ImageOps

from timeline.models import Image, UserForImage

MAX_OCTETS = 2 * 1024 * 1024
MAX_DIMENSION = 2560  # pixels, sur le grand côté
QUALITE_JPEG = (85, 80, 75, 70)
MINIATURE_DIMENSION = 600
QUALITE_MINIATURE = 80
FORMATS_COMPRESSIBLES = {"JPEG", "PNG", "WEBP"}

EXIF_IFD = 0x8769
EXIF_DATE_TIME_ORIGINAL = 36867
EXIF_DATE_TIME = 306


def lire_date_prise(fichier):
    """
    Date et heure de prise de vue lues dans l'EXIF, None si absentes ou illisibles
    """

    try:
        with PILImage.open(fichier) as image:
            exif = image.getexif()
            brut = exif.get_ifd(EXIF_IFD).get(EXIF_DATE_TIME_ORIGINAL) or exif.get(EXIF_DATE_TIME)
        return timezone.make_aware(datetime.strptime(brut, "%Y:%m:%d %H:%M:%S")) if brut else None
    except (OSError, ValueError, TypeError, KeyError):
        return None
    finally:
        fichier.seek(0)


def compresser_image(fichier):
    """
    Réduit une photo trop grande : grand côté limité à MAX_DIMENSION, puis qualité JPEG abaissée par paliers
    et dimensions réduites jusqu'à passer sous MAX_OCTETS. Une photo déjà assez petite (ou d'un format non
    géré, comme un GIF) est renvoyée telle quelle. Une photo réduite perd son EXIF (orientation appliquée).
    """

    with PILImage.open(fichier) as image:
        if image.format not in FORMATS_COMPRESSIBLES or (
            fichier.size <= MAX_OCTETS and max(image.size) <= MAX_DIMENSION
        ):
            fichier.seek(0)
            return fichier

        image = ImageOps.exif_transpose(image)
        image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        transparente = image.mode in ("RGBA", "LA") or "transparency" in image.info
        extension = ".png" if transparente else ".jpg"
        if not transparente:
            image = image.convert("RGB")

        while True:
            for qualite in (None,) if transparente else QUALITE_JPEG:
                tampon = io.BytesIO()
                if transparente:
                    image.save(tampon, "PNG", optimize=True)
                else:
                    image.save(tampon, "JPEG", quality=qualite, optimize=True)
                if tampon.tell() <= MAX_OCTETS:
                    nom = os.path.splitext(fichier.name)[0] + extension
                    return ContentFile(tampon.getvalue(), name=nom)
            image = image.resize((int(image.width * 0.85), int(image.height * 0.85)), PILImage.LANCZOS)


def date_par_defaut(moment):
    """
    Date proposée pour une photo dont on ne sait rien : le premier jour du moment, à midi
    """

    return timezone.make_aware(datetime.combine(moment.date_debut, time(12, 0)))


def create_images(note, fichiers, details):
    """
    Enregistre les photos téléversées sur une note avec leurs détails (un dict nom/legende/date_prise/tags
    par fichier, dans le même ordre) et crée l'aperçu léger de chacune, puis donne une vignette au moment s'il
    n'en a pas
    """

    for fichier, detail in zip(fichiers, details):
        # Avant compression : l'EXIF y est perdu. La date proposée par défaut (premier jour du moment) cède devant
        # la vraie date de prise de vue quand la photo en a une
        date_exif = lire_date_prise(fichier)
        saisie = detail["date_prise"]
        date_prise = date_exif if date_exif and (not saisie or saisie == date_par_defaut(note.moment)) else saisie or None
        image = Image.objects.create(
            fichier=compresser_image(fichier),
            nom=detail["nom"] or fichier.name,
            legende=detail["legende"],
            date_prise=date_prise,
            note=note,
        )
        create_miniature(image)
        sync_tags(image, detail["tags"])
    ensure_thumbnail(note.moment)


def ensure_thumbnail(moment):
    """
    Si le moment n'a pas de vignette, prend la première photo importée
    """

    if moment.thumbnail_id is None:
        premiere = Image.objects.filter(note__moment=moment).order_by("datetime_ajout", "id").first()
        if premiere:
            set_thumbnail(moment, premiere)


def set_thumbnail(moment, image):
    """
    Définit la vignette d'un moment (son aperçu léger est créé au besoin)
    """

    moment.thumbnail = image
    moment.save(update_fields=["thumbnail"])
    if not image.miniature:
        create_miniature(image)


def create_miniature(image):
    """
    Génère l'aperçu léger (grand côté MINIATURE_DIMENSION, environ 100 Ko) d'une image
    """

    with PILImage.open(image.fichier) as source:
        reduite = ImageOps.exif_transpose(source).convert("RGB")
    reduite.thumbnail((MINIATURE_DIMENSION, MINIATURE_DIMENSION))
    tampon = io.BytesIO()
    reduite.save(tampon, "JPEG", quality=QUALITE_MINIATURE, optimize=True)
    image.miniature.save(f"{image.pk}.jpg", ContentFile(tampon.getvalue()), save=True)


def sync_tags(image, users):
    """
    Aligne les utilisateurs taggés sur une image avec la liste donnée
    """

    UserForImage.objects.filter(image=image).exclude(user__in=users).delete()
    deja_tagges = set(UserForImage.objects.filter(image=image).values_list("user_id", flat=True))
    UserForImage.objects.bulk_create(
        UserForImage(image=image, user=user) for user in users if user.pk not in deja_tagges
    )
