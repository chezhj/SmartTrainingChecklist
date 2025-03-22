import requests
import xml.etree.ElementTree as ET


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

    def xml_url(self) -> str:
        """
        Generate the dynamic URL for fetching the SimBrief XML.
        """
        if not self.pilot_id:
            raise ValueError("Pilot ID is required to generate the XML URL.")
        return f"https://www.simbrief.com/api/xml.fetcher.php?userid={self.pilot_id}"

    def fetch_data(self):
        """
        Fetch and parse the SimBrief XML data.
        """
        if not self.pilot_id:
            self.error_message = "Pilot ID is required to fetch data."
            return

        try:
            response = requests.get(self.xml_url(), timeout=10)
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
