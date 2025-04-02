"""Development settings file"""

# pylint: disable=unused-wildcard-import,wildcard-import
from .base import *


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-ky_2(^&n3xfwf-jadnm(m^ti9ybjb43%k6%m!&ek9(_s!gx^m_"


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["espresso", "localhost"]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"

STATIC_ROOT = "./checklist/static/"

# SIMBRIEF_URL = "https://www.simbrief.com/api/xml.fetcher.php?userid="
SIMBRIEF_URL = (
    "https://my-simbrief-mock.wiremockapi.cloud//simbrief/get_plan.php?userid="
)
