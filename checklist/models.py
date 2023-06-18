from re import T
from django.urls import reverse
from django.db import models

# Create your models here.


class Procedure(models.Model):
    title = models.CharField(max_length=40)
    step = models.PositiveIntegerField()
    slug = models.SlugField(unique=True)

    def __str__(self) -> str:
        return self.title

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
        return self.item

    def shouldshow(self, profile):
        profattr = profile.attributes.all()
        attributes = self.attributes.all()
        if attributes:
            # if the checkitem attributes match all profile attributes, then shouldshow=true
            sel_attributes = attributes.intersection(profattr)
            return sel_attributes.count() == attributes.count()
        else:
            # Is a mandatory checkitem as it has no attributes
            return True

    class Meta:
        ordering = ["step"]


class Attribute(models.Model):
    title = models.CharField(max_length=30)
    order = models.PositiveIntegerField()
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.title


class SessionProfile(models.Model):
    sessionId = models.IntegerField()
    attributes = models.ManyToManyField("Attribute", blank=True)
