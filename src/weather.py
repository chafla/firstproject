import json
import requests


class WeatherAPIError(BaseException):
    """
    Error thrown if we don't have a successful API request
    """
    def __init__(self, message: str, api_resp: dict = None):
        super(WeatherAPIError, self).__init__(message)
        self.api_resp = api_resp


class WeatherData:
    """
    Class to interface with openweathermap in order to get some details that we can
    pair up against our solar data (as a curiosity).

    All we really care about is how cloudy the area is.
    """

    def __init__(self, config_fp: str = "config.json"):
        with open(config_fp, "r") as raw_config_json:
            config_json = json.load(raw_config_json)

        self._api_key = config_json["weather_api_key"]
        self._city_id = config_json["weather_city_id"]

    def _get_current_weather_data(self) -> dict:
        """
        Get weather data from our API at city_id.
        :return: Weather data json response
        """
        url_base = "http://api.openweathermap.org/data/2.5/weather?id={}&APPID={}"
        resp = requests.get(url_base.format(self._city_id, self._api_key))

        json_resp = json.loads(resp.text)

        if resp.status_code != 200:
            raise WeatherAPIError("Status code {} returned in api request".format(resp.status_code),
                                  json_resp)
        else:
            return json_resp

    def get_cloud_levels(self) -> float:
        """
        Get the cloud levels (float percentage out of 1) at the location specified in the class.

        :return: Cloud levels out of 1, or -1 if an error occurred.
        """
        weather = self._get_current_weather_data()

        try:
            cloud_data = weather["clouds"]["all"]
        except KeyError as e:
            raise WeatherAPIError("Couldn't read cloud data") from e

        cloud_data = int(cloud_data) / 100

        return cloud_data
