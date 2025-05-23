"""
This module provides the SimBrief class for fetching and parsing SimBrief flight plan data in
XML format.
Classes:
    SimBrief: Handles retrieval and parsing of SimBrief XML data for a given pilot ID,
    extracting relevant flight information such as origin, elevation, runway, temperature,
    altimeter, flap setting, and bleed setting.
Dependencies:
    - xml.etree.ElementTree for XML parsing
    - requests for HTTP requests
    - django.conf.settings for configuration
Usage:
    Instantiate the SimBrief class with a pilot ID, then call fetch_data() to retrieve and
    parse the flight plan data. Extracted information is available as instance attributes.
"""

import xml.etree.ElementTree as ET
import requests
from django.conf import settings as conf_settings


class SimBrief:
    """
    A class to fetch and parse SimBrief flight plan data.
    """

    def __init__(self, pilot_id=None):
        self.pilot_id = pilot_id
        self.origin = None
        self.elevation = None
        self.temperature = None
        self.runway = None
        self.rwy_length = None
        self.altimeter = None
        self.flap_setting = None
        self.bleed_setting = None
        self.error_message = None
        self.mock_token = None

    def xml_url(self) -> str:
        """
        Generate the dynamic URL for fetching the SimBrief XML.
        """
        if not self.pilot_id:
            raise ValueError("Pilot ID is required to generate the XML URL.")

        simbrief_url = getattr(conf_settings, "SIMBRIEF_URL", None)
        self.mock_token = getattr(conf_settings, "MOCK_TOKEN", None)

        # self.mock_token = getattr(conf_settings, "X-Auth-Token", None)

        if not simbrief_url:  # This should be defined in your settings
            raise ValueError("No SIMBRIEF_URL found in settings.")

        # Add the pilot ID to the URL
        simbrief_url = simbrief_url + self.pilot_id
        return simbrief_url

    def fetch_data(self):
        """
        Fetch and parse the SimBrief XML data.
        """
        if not self.pilot_id:
            self.error_message = "Pilot ID is required to fetch data."
            return

        try:
            url = self.xml_url()
            headers = {}
            if self.mock_token:
                headers = {"X-Auth-Token": self.mock_token}
            # Make the GET request with headers
            response = requests.get(url, headers=headers, timeout=10)

            response.raise_for_status()  # Raise an error for HTTP issues
            self.parse_xml(response.content)
        except requests.RequestException as e:
            self.error_message = f"Error fetching SimBrief data: {e}"
            print(f"Error fetching SimBrief data: {e}")
        except ET.ParseError as e:
            self.error_message = f"Error parsing SimBrief XML: {e}"
            print(f"Error parsing SimBrief XML: {e}")

    def parse_xml(self, xml_data):
        """
        Parse the XML data to extract relevant information.
        """
        root = ET.fromstring(xml_data)

        self.origin = root.findtext("origin/icao_code")  # Departure airport
        self.elevation = root.findtext("origin/elevation") + " ft"
        self.runway = root.findtext("origin/plan_rwy")  # Departure runway
        self.temperature = (
            root.findtext("tlr/takeoff/conditions/temperature") + "°C"
        )  # Temperature
        self.altimeter = root.findtext("tlr/takeoff/conditions/altimeter")

        # Find the runway with the matching identifier and extract its length
        self.rwy_length = None
        for runway in root.findall("tlr/takeoff/runway"):
            identifier = runway.findtext("identifier")
            if identifier == self.runway:
                self.rwy_length = runway.findtext("length") + " ft"
                self.flap_setting = runway.findtext("flap_setting")
                self.bleed_setting = runway.findtext("bleed_setting")
                break
