"""passenger file to connect django app to server environment"""
import os
import sys

from smart_training_checklist.wsgi import app

sys.path.insert(0, os.path.dirname(__file__))

environ = os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "SmartTrainingChecklist.settings.dev"
)

application = app
