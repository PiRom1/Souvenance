from timeline.models import Image

CADRES = ["polaroid", "ruban", "coins", "croquis"]
RATIOS = ["4-3", "1-1", "3-4"]
APERCU = 3   # photos montrées dans le livre ; les autres s'ouvrent dans la visionneuse du lot
ALIGNEMENTS = ["start", "center", "end"]
DOODLES = ["collines", "arbres", "plage", "moulin", "lac", "riviere", "grand-arbre", "cascade", "sapins", "montagne"]


def _decorer_image(image, note_id=0):
    """
    Donne à une photo son cadre, son format et son inclinaison, de façon stable (calculés depuis les identifiants)
    """

    image.cadre = CADRES[(image.id * 5 + note_id) % len(CADRES)]
    image.ratio = RATIOS[image.id % len(RATIOS)]
    image.inclinaison = f"{(image.id * 37) % 9 * 0.7 - 2.8:.1f}"
    image.tags = [ufi.user for ufi in image.userforimage_set.all()]
    return image


def preparer_livre(moment):
    """
    Les notes d'un moment prêtes à être mises en page dans le livre
    """

    notes = list(moment.notes.select_related("auteur").prefetch_related("images__userforimage_set__user"))
    for note in notes:
        note.lieu_effectif = note.lieu or moment.lieu
        note.alignement = ALIGNEMENTS[note.id % len(ALIGNEMENTS)]
        note.photos = [_decorer_image(image, note.id) for image in note.images.all()]
        note.apercu = note.photos[:APERCU]
        note.suite = note.photos[APERCU:]
        note.reste = len(note.suite)
        note.groupe = f"note-{note.id}"
        note.nombre_photos = "une" if len(note.apercu) == 1 else "deux" if len(note.apercu) == 2 else "plusieurs"

    return {
        "notes": notes,
        "doodle": DOODLES[moment.id % len(DOODLES)],
    }


def photos_du_moment(moment):
    """
    Toutes les photos d'un moment, pour la photothèque
    """

    images = (Image.objects.filter(note__moment=moment)
              .select_related("note__auteur").prefetch_related("userforimage_set__user")
              .order_by("date_prise", "datetime_ajout", "id"))
    images = [_decorer_image(image, image.note_id) for image in images]
    tagues = {user.username: user for image in images for user in image.tags}
    return images, [tagues[username] for username in sorted(tagues)]
