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
        return reverse("procedure_detail", kwargs={"slug": self.slug})

class CheckItem(models.Model):
    item = models.CharField(max_length=50)
    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE)
    step = models.PositiveIntegerField()
    setting = models.CharField(max_length=80)
    attributes = models.ManyToManyField('Attribute', blank=True, related_name='checkItems')

    def __str__(self) -> str:
        return self.item

    class Meta:
        ordering = ['step']

class Attribute(models.Model):
     title = models.CharField(max_length=30)
     order = models.PositiveIntegerField()
     description = models.TextField(blank=True)
    
     def __str__(self) -> str:
         return self.title


class SessionProfile(models.Model):
    sessionId = models.IntegerField()
    attributes = models.ManyToManyField('Attribute',blank=True)