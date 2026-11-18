from django.db.models.signals import post_delete
from django.dispatch import receiver

from timeline.models import Image


@receiver(post_delete, sender=Image)
def supprimer_fichiers_image(sender, instance, **kwargs):
    """
    Django ne supprime pas les fichiers avec la ligne en base : on retire l'original et la miniature
    """

    instance.fichier.delete(save=False)
    instance.miniature.delete(save=False)
