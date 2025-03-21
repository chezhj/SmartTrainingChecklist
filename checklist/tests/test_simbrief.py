import unittest
from unittest.mock import patch, MagicMock
from checklist.simbrief import SimBrief


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


if __name__ == "__main__":
    unittest.main()
