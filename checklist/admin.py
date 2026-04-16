from django.contrib import admin

from .models import Procedure, CheckItem, Attribute


class CheckInline(admin.TabularInline):
    model = CheckItem


class ProcedureAdmin(admin.ModelAdmin):
    inlines = [CheckInline]
    list_display = ["title", "step"]
    ordering = ["step"]
    prepopulated_fields = {"slug": ("title",)}


class AttributeAdmin(admin.ModelAdmin):
    list_display = ["title", "order", "show", "live_rule_mode"]
    list_filter = ["show", "live_rule_mode", "is_user_preference"]
    fieldsets = [
        (None, {
            "fields": ["title", "label", "order", "description", "show",
                       "is_user_preference", "over_ruled_by", "btn_color"],
        }),
        ("Live Rule", {
            "fields": ["live_rule", "live_rule_mode", "prompt_message"],
            "classes": ["collapse"],
        }),
    ]


admin.site.site_header = "SimFlow Admin"
admin.site.site_title = "SimFlow"

admin.site.register(Procedure, ProcedureAdmin)
admin.site.register(CheckItem)
admin.site.register(Attribute, AttributeAdmin)
