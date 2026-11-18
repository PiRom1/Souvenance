from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from timeline.models import Image, Moment, MomentRevision, Note, User, UserForImage, UserForMoment


admin.site.register(User, UserAdmin)


class UserForMomentInline(admin.TabularInline):
    model = UserForMoment
    extra = 0


class MomentRevisionInline(admin.TabularInline):
    model = MomentRevision
    extra = 0
    readonly_fields = ("datetime",)


@admin.register(Moment)
class MomentAdmin(admin.ModelAdmin):
    list_display = ("nom", "date_debut", "date_fin", "lieu", "createur")
    list_filter = ("createur",)
    search_fields = ("nom", "lieu")
    date_hierarchy = "date_debut"
    inlines = (UserForMomentInline, MomentRevisionInline)


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("moment", "auteur", "datetime_creation")
    list_filter = ("auteur",)
    ordering = ("-datetime_creation",)
    readonly_fields = ("datetime_creation",)


class UserForImageInline(admin.TabularInline):
    model = UserForImage
    extra = 0


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    inlines = (UserForImageInline,)
    list_display = ("nom", "date_prise", "datetime_ajout")
    ordering = ("-datetime_ajout",)
    readonly_fields = ("datetime_ajout",)
