from django.contrib import admin

from .models import Procedure, CheckItem, Attribute


class CheckInline(admin.TabularInline):
    model = CheckItem


class ProcedureAdmin(admin.ModelAdmin):
    inlines = [CheckInline]
    list_display = ["title", "step"]
    ordering = ["step"]
    prepopulated_fields = {"slug": ("title",)}


admin.site.site_header = "SimFlow Admin"
admin.site.site_title = "SimFlow"

# Register your models here.
admin.site.register(Procedure, ProcedureAdmin)
admin.site.register(CheckItem)
admin.site.register(Attribute)
