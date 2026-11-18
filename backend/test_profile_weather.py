import unittest
from unittest.mock import patch
from services.weather_service import profile_weather


class WeatherQuestions(unittest.TestCase):
    @patch("services.weather_service._fetch_weather")
    def test_profile_question(self, fetch):
        fetch.return_value = dict(city="Orai", temp=21, description="clear", humidity=55,
                                  wind_speed=2, rain=0, forecast="18:00: clear")
        result = profile_weather("hows the weather for wheat", "Orai", "wheat")
        fetch.assert_called_once_with("Orai")
        self.assertIn("21°C", result["response"])
        self.assertIn("grain filling", result["response"])

    @patch("services.weather_service._fetch_weather", return_value=None)
    def test_unavailable_and_other_location(self, fetch):
        self.assertNotIn("photo", profile_weather("weather?", "Orai", "wheat")["response"])
        self.assertIsNone(profile_weather("weather in Pune", "Orai", "wheat"))
