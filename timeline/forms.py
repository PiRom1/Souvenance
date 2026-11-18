from datetime import datetime, time

from django import forms
from django.utils import timezone

from timeline.models import Image, Moment, Note, User


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, attrs=None):
        # Le <input type="date"> n'accepte que le format ISO, sinon il s'affiche vide
        super().__init__(attrs, format="%Y-%m-%d")


class AvatarSelectMultiple(forms.CheckboxSelectMultiple):
    """
    Sélection multiple d'utilisateurs par leur visage (static/timeline/img/<username>.png)
    """

    template_name = "timeline/widgets/avatar_select.html"

    def __init__(self, attrs=None, size="medium"):
        super().__init__(attrs)
        self.size = size

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["size"] = self.size
        return context

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        option["username"] = getattr(getattr(value, "instance", None), "username", "")
        option["tilt"] = (index * 37) % 9 - 4  # petite inclinaison stable, comme des autocollants posés à la main
        return option


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.FileField):
    """
    Champ qui accepte plusieurs fichiers image d'un coup
    """

    widget = MultipleFileInput

    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else [data]
        return [forms.ImageField().clean(f, initial) for f in files if f]


class MomentForm(forms.ModelForm):
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.order_by("username"),
        required=False,
        widget=AvatarSelectMultiple,
    )

    class Meta:
        model = Moment
        fields = ["nom", "description", "date_debut", "date_fin", "lieu"]
        labels = {"date_debut": "Date de début", "date_fin": "Date de fin"}
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Soirée de parrainage, Vacances à Luz…", "autofocus": True}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Quelques mots pour planter le décor…"}),
            "lieu": forms.TextInput(attrs={"placeholder": "Bordegrande, Chez Paul…"}),
            "date_debut": DateInput,
            "date_fin": DateInput,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["participants"].initial = User.objects.filter(users_for_moment__moment=self.instance)
        else:
            self.fields["participants"].initial = User.objects.all()  # toute la bande par défaut


class NoteForm(forms.ModelForm):
    images = MultipleImageField(required=False, label="Ajouter des photos")

    class Meta:
        model = Note
        fields = ["date", "texte", "lieu"]
        widgets = {"date": DateInput}

    def __init__(self, *args, moment, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.initial["date"] = moment.date_debut
            self.initial["lieu"] = moment.lieu
        lieu = self.fields["lieu"]
        lieu.widget.attrs["placeholder"] = moment.lieu or "Le même que le moment"
        self.fields["texte"].widget.attrs["placeholder"] = "Ce dont tu te souviens, une anecdote, un mot doux…"
        self.fields["images"].widget.attrs.update({"multiple": True, "accept": "image/*"})


class ImageForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=User.objects.order_by("username"),
        required=False,
        widget=AvatarSelectMultiple(size="small"),
        label="Personnes sur la photo",
    )
    # On ne saisit que le jour ; l'heure n'est qu'indiquée quand la photo la porte (sinon midi)
    jour = forms.DateField(required=False, label="Prise le", widget=DateInput)
    heure = forms.TimeField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Image
        fields = ["nom", "legende"]
        labels = {"legende": "Légende"}
        widgets = {"legende": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["tags"].initial = User.objects.filter(userforimage__image=self.instance)
            if self.instance.date_prise:
                prise = timezone.localtime(self.instance.date_prise)
                self.fields["jour"].initial = prise.date()
                if prise.time().replace(second=0, microsecond=0) != time(12, 0):
                    self.fields["heure"].initial = prise.strftime("%H:%M")

    def clean(self):
        cleaned = super().clean()
        jour = cleaned.get("jour")
        prise = timezone.make_aware(datetime.combine(jour, cleaned.get("heure") or time(12, 0))) if jour else None
        cleaned["date_prise"] = prise
        self.instance.date_prise = prise
        return cleaned


ImageFormSet = forms.modelformset_factory(Image, form=ImageForm, extra=0, can_delete=True)


class MomentFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Recherche (nom, description)")
    lieu = forms.CharField(required=False)
    du = forms.DateField(required=False, label="Du", widget=DateInput)
    au = forms.DateField(required=False, label="Au", widget=DateInput)
    participants = forms.ModelMultipleChoiceField(
        queryset=User.objects.order_by("username"),
        required=False,
        widget=AvatarSelectMultiple(size="small"),
        help_text="Les moments où tous les participants choisis étaient là.",
    )
