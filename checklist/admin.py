from django.contrib import admin

from .models import Procedure, CheckItem, Attribute


class CheckInline(admin.TabularInline):
    model = CheckItem


class ProcedureAdmin(admin.ModelAdmin):
    inlines = [CheckInline]
    list_display = ["title", "step"]
    ordering = ["step"]
    prepopulated_fields = {"slug": ("title",)}


# Register your models here.
admin.site.register(Procedure, ProcedureAdmin)
admin.site.register(Attribute)
