"""
Main models module for al database objects
"""
# pylint: disable=no-member

from colorfield.fields import ColorField
from django.urls import reverse
from django.db import models

# Create your models here.


class Procedure(models.Model):
    title = models.CharField(max_length=40)
    step = models.PositiveIntegerField()
    slug = models.SlugField(unique=True)

    def __str__(self) -> str:
        return self.title.__str__()

    def get_absolute_url(self):
        return reverse("checklist:detail", kwargs={"slug": self.slug})


class CheckItem(models.Model):
    item = models.CharField(max_length=50)
    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE)
    step = models.PositiveIntegerField()
    setting = models.CharField(max_length=80)
    attributes = models.ManyToManyField(
        "Attribute", blank=True, related_name="checkItems"
    )

    def __str__(self) -> str:
        return self.item.__str__()

    def shouldshow(self, profile_list):
        attributes = self.attributes.values_list("id", flat=True)
        if attributes:
            matching = set(attributes) & set(profile_list)
            return len(matching) == len(attributes)

        # Is a mandatory checkitem as it has no attributes
        return True

    class Meta:
        ordering = ["step"]


class Attribute(models.Model):
    """
    Model for the attributes of a procedure
    The Title is the main identifier
    The order is used to sort
    """

    title = models.CharField(max_length=30)
    order = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    show = models.BooleanField(default="True")
    over_ruled_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, blank=True, null=True
    )
    btn_color = ColorField(default="#194D33")

    def __str__(self) -> str:
        return self.title.__str__()
