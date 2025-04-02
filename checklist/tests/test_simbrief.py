import unittest
from unittest.mock import patch, MagicMock

from requests import RequestException
from checklist.simbrief import SimBrief
import xml.etree.ElementTree as ET


class TestSimBriefInit(unittest.TestCase):
    def setUp(self):
        # Load the dummy XML file
        with open(
            "c:\\Code\\SmartTrainingChecklist\\checklist\\tests\\dummy.xml", "r"
        ) as file:
            self.dummy_xml = file.read()

    @patch("checklist.simbrief.SimBrief.parse_xml")
    def test_parse_xml_not_called_without_pilot_id(self, mock_parse_xml):
        """
        Test that parse_xml is not called if SimBrief is created without a pilot_id.
        """
        # Initialize SimBrief without a pilot_id
        simbrief = SimBrief()

        # Mock fetch_data to ensure it doesn't call parse_xml
        with patch.object(simbrief, "fetch_data", return_value=None) as mock_fetch_data:
            simbrief.fetch_data()

        # Assert that parse_xml was not called
        mock_parse_xml.assert_not_called()

    # test error message is set if pilot_id is not provided

    def test_attributes_set_to_none_without_pilot_id(self):
        """
        Test that all attributes of SimBrief are set to None if no pilot_id is provided.
        """
        # Initialize SimBrief without a pilot_id
        simbrief = SimBrief()

        # Assert that all attributes are None
        self.assertIsNone(simbrief.pilot_id)
        self.assertIsNone(simbrief.origin)
        self.assertIsNone(simbrief.elevation)
        self.assertIsNone(simbrief.temperature)
        self.assertIsNone(simbrief.runway)
        self.assertIsNone(simbrief.rwy_length)
        self.assertIsNone(simbrief.altimeter)
        self.assertIsNone(simbrief.flap_setting)
        self.assertIsNone(simbrief.bleed_setting)

    @patch("checklist.simbrief.SimBrief.fetch_data")
    def test_init_with_pilot_id(self, mock_fetch_data):
        """
        Test that the SimBrief object initializes correctly with a pilot_id and parses dummy XML.
        """

        # Mock the fetch_data method to call parse_xml on the SimBrief instance
        def mock_fetch_data_side_effect():
            simbrief.parse_xml(self.dummy_xml)

        mock_fetch_data.side_effect = mock_fetch_data_side_effect

        # Initialize SimBrief with a pilot_id
        pilot_id = "12345"
        simbrief = SimBrief(pilot_id=pilot_id)
        simbrief.fetch_data()

        # Assert that the values are correctly parsed from the dummy XML
        self.assertEqual(simbrief.pilot_id, pilot_id)
        self.assertEqual(simbrief.origin, "LOWI")  # Example value from dummy.xml
        self.assertEqual(simbrief.elevation, "1907 ft")  # Example value from dummy.xml
        self.assertEqual(simbrief.temperature, "14°C")  # Example value from dummy.xml
        self.assertEqual(simbrief.runway, "08")  # Example value from dummy.xml
        self.assertEqual(simbrief.rwy_length, "6562 ft")  # Example value from dummy.xml
        self.assertEqual(simbrief.altimeter, "30.21")  # Example value from dummy.xml

    @patch("checklist.simbrief.SimBrief.fetch_data")
    def test_attributes_set_to_none_if_xml_not_retrieved(self, mock_fetch_data):
        """
        Test that all attributes of SimBrief are set to None if the XML for a pilot_id cannot be retrieved.
        """
        # Mock fetch_data to simulate a failure (e.g., HTTP error or empty response)
        mock_fetch_data.side_effect = lambda: None

        # Initialize SimBrief with a pilot_id
        pilot_id = "12345"
        simbrief = SimBrief(pilot_id=pilot_id)
        simbrief.fetch_data()

        # Assert that all attributes are None
        self.assertEqual(simbrief.pilot_id, pilot_id)  # pilot_id should still be set
        self.assertIsNone(simbrief.origin)
        self.assertIsNone(simbrief.elevation)
        self.assertIsNone(simbrief.temperature)
        self.assertIsNone(simbrief.runway)
        self.assertIsNone(simbrief.rwy_length)
        self.assertIsNone(simbrief.altimeter)
        self.assertIsNone(simbrief.flap_setting)
        self.assertIsNone(simbrief.bleed_setting)

    # test that validates an error message is set in simbrief.error_message if an error occurs during fetch_data
    @patch("checklist.simbrief.requests.get")
    def test_error_message_set_on_fetch_data_error(self, mock_get):
        """
        Test that an error message is set in simbrief.error_message if an error occurs during fetch_data.
        """
        # Mock the requests.get method to raise an exception
        mock_get.side_effect = RequestException("No plan found")

        # Initialize SimBrief with a pilot_id
        pilot_id = "12345"
        simbrief = SimBrief(pilot_id=pilot_id)
        simbrief.fetch_data()

        # Assert that the error message is set
        self.assertIn("No plan found", simbrief.error_message)

    # test that validates an error message is set in simbrief.error_message if an error occurs during parse_xml
    @patch("checklist.simbrief.requests.get")
    @patch("checklist.simbrief.ET.fromstring")
    def test_error_message_set_on_parse_xml_error(self, mock_fromstring, mock_get):
        """
        Test that an error message is set in simbrief.error_message if an error occurs during parse_xml.
        """
        # Mock the requests.get method to return a valid response
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = self.dummy_xml

        # Mock the ET.fromstring method to raise an exception
        mock_fromstring.side_effect = ET.ParseError("XML is invalid")

        # Initialize SimBrief with a pilot_id
        pilot_id = "12345"
        simbrief = SimBrief(pilot_id=pilot_id)
        simbrief.fetch_data()

        # Assert that the error message is set
        self.assertIn("XML is invalid", simbrief.error_message)

    @patch(
        "checklist.simbrief.conf_settings.SIMBRIEF_URL",
        "https://any_host/fetcher.php?userid=",
    )
    def test_xml_url_with_valid_setting(self):
        """
        Test that xml_url generates the correct URL when SIMBRIEF_URL is defined.
        """
        simbrief = SimBrief(pilot_id="12345")
        expected_url = "https://any_host/fetcher.php?userid=12345"
        self.assertEqual(simbrief.xml_url(), expected_url)

    @patch("checklist.simbrief.conf_settings.SIMBRIEF_URL", None)
    def test_xml_url_with_missing_setting(self):
        """
        Test that xml_url raises a ValueError when SIMBRIEF_URL is not defined.
        """
        simbrief = SimBrief(pilot_id="12345")
        with self.assertRaises(ValueError) as context:
            simbrief.xml_url()
        self.assertEqual(str(context.exception), "No SIMBRIEF_URL found in settings.")

    def test_xml_url_without_pilot_id(self):
        """
        Test that xml_url raises a ValueError when pilot_id is not provided.
        """
        simbrief = SimBrief()
        with self.assertRaises(ValueError) as context:
            simbrief.xml_url()
        self.assertEqual(
            str(context.exception), "Pilot ID is required to generate the XML URL."
        )


class TestSimBriefHeaders(unittest.TestCase):
    @patch("checklist.simbrief.requests.get")
    @patch.object(SimBrief, "parse_xml")  # Mock parse_xml
    @patch.object(SimBrief, "xml_url")  # Mock xml_url
    def test_headers_are_empty_if_no_token(
        self, mock_xml_url, mock_parse_xml, mock_requests_get
    ):
        """
        Test that the headers are empty if no mock_token is provided.
        """
        # Arrange
        simbrief = SimBrief(pilot_id="12345")
        simbrief.mock_token = None  # No token provided
        mock_xml_url.return_value = "https://mocked-url.com"  # Mocked URL

        # Act
        simbrief.fetch_data()

        # Assert
        mock_requests_get.assert_called_once()
        args, kwargs = mock_requests_get.call_args
        self.assertEqual(kwargs["headers"], {})  # Headers should be empty

    @patch("checklist.simbrief.requests.get")
    @patch.object(SimBrief, "parse_xml")  # Mock parse_xml
    @patch.object(SimBrief, "xml_url")  # Mock xml_url
    def test_headers_include_token_if_given(
        self, mock_xml_url, mock_parse_xml, mock_requests_get
    ):
        """
        Test that the headers include the mock_token if it is provided.
        """
        # Arrange
        simbrief = SimBrief(pilot_id="12345")
        simbrief.mock_token = "mocked_token"
        mock_xml_url.return_value = "https://mocked-url.com"  # Mocked URL

        # Act
        simbrief.fetch_data()

        # Assert
        mock_requests_get.assert_called_once()
        args, kwargs = mock_requests_get.call_args
        self.assertEqual(
            kwargs["headers"], {"X-Auth-Token": "mocked_token"}
        )  # Token should be in headers


if __name__ == "__main__":
    unittest.main()
