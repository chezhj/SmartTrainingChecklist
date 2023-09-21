"""
Custom filter code to enable access to environment variables
in templates
"""
import os
from django import template

from django.conf import settings as conf_settings

register = template.Library()


@register.filter
def env(key):
    """Get environment key"""
    return os.environ.get(key, None)


@register.filter
def setting(key):
    """Get setting based on key"""

    return getattr(conf_settings, key, None)
