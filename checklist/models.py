"""
Main models module for al database objects
"""

# pylint: disable=no-member

import secrets

from colorfield.fields import ColorField
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse


def _generate_session_key():
    """Generate a short session key in ABCD-1234 format."""
    letters = secrets.token_hex(2).upper()
    digits = str(secrets.randbelow(10000)).zfill(4)
    return f"{letters}-{digits}"


class Procedure(models.Model):
    title = models.CharField(max_length=40)
    step = models.PositiveIntegerField()
    slug = models.SlugField(unique=True)
    show_expression = models.TextField(blank=True)
    auto_continue = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.title.__str__()

    def get_absolute_url(self):
        return reverse("checklist:detail", kwargs={"slug": self.slug})


class CheckItem(models.Model):
    item = models.CharField(max_length=50)
    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE)
    step = models.PositiveIntegerField()
    setting = models.CharField(max_length=80)
    action_label = models.CharField(max_length=8, blank=True)
    dataref_expression = models.TextField(blank=True)
    attributes = models.ManyToManyField(
        "Attribute", blank=True, related_name="checkItems"
    )

    ROLE_CHOICES = [
        ("PF", "Pilot Flying"),
        ("PM", "Pilot Monitoring"),
        ("C", "Captain"),
        ("BOTH", "Both"),
        ("FO", "First Officer"),
    ]
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="",
        blank=True,
        help_text="Indicates who should perform this check item.",
    )

    auto_check_rule = models.JSONField(
        blank=True,
        null=True,
        help_text="v2.0 auto-check rule (JSON). Do not modify dataref_expression.",
    )

    def __str__(self) -> str:
        return self.item.__str__()

    def get_action_label(self):
        if self.action_label:
            return self.action_label

        if not self.attributes.filter(title="NoActionNeed").exists():
            return "SET"
        else:
            return "CHECKED"

    def shouldshow(self, profile_list):
        attributes = self.attributes.values_list("id", flat=True)
        if attributes:
            matching = set(attributes) & set(profile_list)
            return len(matching) == len(attributes)

        # Is a mandatory checkitem as it has no attributes
        return True

    class Meta:
        ordering = ["step"]


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    simbrief_id = models.CharField(max_length=20, blank=True)

    def __str__(self) -> str:
        return f"Profile({self.user.username})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def _create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


class FlightSession(models.Model):
    """Central session model. Created when the pilot clicks 'Start Checklist'."""

    ROLE_CHOICES = [("PF", "Pilot Flying"), ("PM", "Pilot Monitoring"), ("SOLO", "Solo")]
    FUNCTION_CHOICES = [("C", "Captain"), ("FO", "First Officer"), ("BOTH", "Both")]

    session_key = models.CharField(
        max_length=20,
        unique=True,
        default=_generate_session_key,
        help_text="Short code shown to pilot (e.g. A3F2-0891).",
    )
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="flight_sessions",
    )
    pilot_role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="SOLO")
    pilot_function = models.CharField(
        max_length=10, choices=FUNCTION_CHOICES, default="BOTH"
    )
    active_phase = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_plugin_contact = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        user = self.user_profile.user.username if self.user_profile else "anon"
        return f"FlightSession({self.session_key}, {user})"


class FlightInfo(models.Model):
    """Current flight conditions for a session. Seeded from SimBrief OFP."""

    flight_session = models.OneToOneField(
        FlightSession, on_delete=models.CASCADE, related_name="flight_info"
    )
    origin_icao = models.CharField(max_length=10)
    destination_icao = models.CharField(max_length=10)
    alternate_icao = models.CharField(max_length=10, blank=True)
    oat = models.IntegerField(null=True, blank=True, help_text="Outside air temp °C")
    departure_runway = models.CharField(max_length=10, blank=True)
    departure_stand = models.CharField(max_length=20, blank=True)
    fuel_on_board = models.IntegerField(null=True, blank=True, help_text="kg")
    ofp_loaded = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"FlightInfo({self.origin_icao}→{self.destination_icao})"


class FlightSessionAttribute(models.Model):
    """Active attribute set for a flight session. One row per Attribute, created eagerly."""

    SOURCE_CHOICES = [
        ("user_default", "User Default"),
        ("ofp_derived", "OFP Derived"),
        ("pilot_override", "Pilot Override"),
    ]

    flight_session = models.ForeignKey(
        FlightSession, on_delete=models.CASCADE, related_name="session_attributes"
    )
    attribute = models.ForeignKey("Attribute", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES, default="user_default"
    )

    class Meta:
        unique_together = [("flight_session", "attribute")]

    def __str__(self) -> str:
        return f"{self.flight_session.session_key}/{self.attribute.title}={'on' if self.is_active else 'off'}"


class FlightItemState(models.Model):
    """Runtime state per checklist item. Lazy — only rows that differ from unchecked."""

    STATUS_CHOICES = [
        ("checked", "Checked"),
        ("skipped", "Skipped"),
        ("pending", "Pending"),
    ]
    SOURCE_CHOICES = [
        ("manual", "Manual"),
        ("auto", "Auto"),
    ]

    flight_session = models.ForeignKey(
        FlightSession, on_delete=models.CASCADE, related_name="item_states"
    )
    checklist_item = models.ForeignKey("CheckItem", on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    source = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, null=True, blank=True
    )
    checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("flight_session", "checklist_item")]

    def __str__(self) -> str:
        return f"{self.flight_session.session_key}/{self.checklist_item.item}={self.status}"


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
