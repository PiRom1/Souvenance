from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import F, Q
from django.utils import timezone



## Utilisateurs

class User(AbstractUser):
    """
    Un membre de la bande (a un compte, participe aux moments, écrit des notes)
    """

    def __str__(self):
        return self.get_full_name() or self.username



## Moments

class Moment(models.Model):
    """
    Un moment de vie : ponctuel (sans date de fin) ou étalé dans le temps (avec date de fin)
    """

    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date_debut = models.DateField(db_index=True)
    date_fin = models.DateField(null=True, blank=True, help_text="Vide pour un moment ponctuel")
    lieu = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    createur = models.ForeignKey(User, on_delete=models.PROTECT, related_name="moments_crees")
    thumbnail = models.ForeignKey("Image", on_delete=models.SET_NULL, null = True, blank = True)

    class Meta:
        ordering = ["-date_debut"]
        constraints = [
            models.CheckConstraint(
                condition=Q(date_fin__isnull=True) | Q(date_fin__gte=F("date_debut")),
                name="date_fin_apres_date_debut",
            ),
            models.CheckConstraint(
                condition=(Q(latitude__isnull=True) & Q(longitude__isnull=True))
                | (Q(latitude__isnull=False) & Q(longitude__isnull=False)),
                name="latitude_et_longitude_ensemble_for_moment",
            ),
        ]

    @property
    def est_ponctuel(self):
        return self.date_fin is None

    def __str__(self):
        return f"{self.nom} ({self.date_debut})"



class UserForMoment(models.Model):
    """
    La participation d'un membre à un moment
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="users_for_moment")
    moment = models.ForeignKey(Moment, on_delete=models.CASCADE, related_name="users_for_moment")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "moment"], name="un_participant_une_fois_par_moment")]

    def __str__(self):
        return f"{self.user} à {self.moment.nom}"


class MomentRevision(models.Model):
    """
    Une modification de la description d'un moment, faite par un membre à un instant précis.
    Contient la description telle qu'elle est après la modification.
    """

    moment = models.ForeignKey(Moment, on_delete=models.CASCADE, related_name="revisions")
    description = models.TextField(blank=True)
    auteur = models.ForeignKey(User, on_delete=models.PROTECT, related_name="revisions")
    datetime = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-datetime"]

    def __str__(self):
        return f"{self.moment.nom} modifié par {self.auteur} le {self.datetime:%d/%m/%Y %H:%M}"



## Notes et images

class Note(models.Model):
    """
    La note d'un membre sur un moment (texte libre et/ou photos). Seul son auteur peut la modifier.
    """

    moment = models.ForeignKey(Moment, on_delete=models.CASCADE, related_name="notes")
    date = models.DateField(null=True, blank=True, help_text="Date à laquelle se rapporte la note. Vide : date de début du moment")
    auteur = models.ForeignKey(User, on_delete=models.PROTECT, related_name="notes")
    texte = models.TextField(blank=True)
    lieu = models.CharField(max_length=200, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    datetime_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "datetime_creation"]
        constraints = [
            models.CheckConstraint(
                        condition=(Q(latitude__isnull=True) & Q(longitude__isnull=True))
                        | (Q(latitude__isnull=False) & Q(longitude__isnull=False)),
                        name="latitude_et_longitude_ensemble_for_note",)
                ]

    def save(self, *args, **kwargs):
        if self.date is None:
            self.date = self.moment.date_debut
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Note de {self.auteur} sur {self.moment.nom}"


def date_de_rangement(image):
    """
    Date qui range une photo dans les dossiers : celle de la prise de vue (saisie ou EXIF), à défaut le premier jour
    de son moment, à défaut aujourd'hui
    """

    if image.date_prise:
        return timezone.localtime(image.date_prise).date()
    if image.note_id and image.note.moment_id:
        return image.note.moment.date_debut
    return timezone.localdate()


def chemin_image(image, nom_fichier):
    """
    Dossier de l'original : images/<année>/<mois>/ de la date de rangement
    """

    jour = date_de_rangement(image)
    return f"images/{jour:%Y}/{jour:%m}/{nom_fichier}"


def chemin_miniature(image, nom_fichier):
    """
    Dossier de l'aperçu léger : miniatures/<année>/<mois>/ de la même date
    """

    jour = date_de_rangement(image)
    return f"miniatures/{jour:%Y}/{jour:%m}/{nom_fichier}"


class Image(models.Model):
    """
    Une photo stockée sur le serveur
    """

    fichier = models.ImageField(upload_to=chemin_image)
    miniature = models.ImageField(upload_to=chemin_miniature, null=True, blank=True, editable=False,
                                  help_text="Aperçu léger (grand côté 600 px) utilisé dans la frise, le livre et la photothèque")
    nom = models.CharField(max_length=200, blank=True)
    date_prise = models.DateTimeField(null=True, blank=True, help_text="Date et heure de la prise de vue (lues dans la photo, ou le jour saisi à midi)")
    datetime_ajout = models.DateTimeField(auto_now_add=True)
    legende = models.TextField(default=None, blank=True, null=True)
    note = models.ForeignKey(Note, on_delete=models.SET_NULL, null=True, blank=True, related_name="images")
    

    @property
    def url_affichage(self):
        """
        Aperçu léger si on en a un, sinon l'original
        """

        return (self.miniature or self.fichier).url

    def __str__(self):
        return self.nom or self.fichier.name


class UserForImage(models.Model):
    """
    Un tag, un utilisateur apparaissant sur une image
        - Aujourd'hui ajouté manuellement, plus tard qui sait un modèle le fera
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
