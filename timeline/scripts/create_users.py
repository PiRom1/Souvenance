from timeline.models import User


def run():
    """
    Crée les membres de la bande (mot de passe = <username>password). Relançable sans doublon.
    """

    for username in ["lise", "emma", "mathieu", "paul", "alice", "didier", "pierrick", "romain"]:
        user, _ = User.objects.get_or_create(username=username)
        user.set_password(f"{username}password")
        user.save()
