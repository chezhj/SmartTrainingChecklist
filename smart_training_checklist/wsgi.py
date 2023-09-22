"""
WSGI config for SmartTrainingChecklist project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SmartTrainingChecklist.settings.dev")

if os.environ.get("DJANGO_SETTINGS_MODULE").endswith("dev"):
    application = get_wsgi_application()
else:
    app = get_wsgi_application()
