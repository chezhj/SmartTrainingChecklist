import os
import sys


sys.path.insert(0, os.path.dirname(__file__))

environ = os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "SmartTrainingChecklist.settings"
)

from SmartTrainingChecklist.wsgi import app

application = app
