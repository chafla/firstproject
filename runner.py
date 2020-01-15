import datetime
import os
import time
from enum import Enum
import logging

from src.sheet_manager import SheetReader
from src.solar_reader import SolarReader
from src.weather import WeatherData

log = logging.getLogger()


class State(Enum):
    SUNRISE_WAIT = 0
    SYS_ONLINE = 1
    SUNSET = 2


class SolarData:
    def __init__(self, sheet_reader: SheetReader, solar_reader: SolarReader, weather_reader: WeatherData):
        self.sheet_reader = sheet_reader
        self.solar_reader = solar_reader
        self.weather_reader = weather_reader

        self.state = State.SUNRISE_WAIT

        self.wh_col = "B"
        self.mi_col = "C"
        self.cur_kw_col = "D"
        self.weather_col = "E"

        self.ext_ip_cell = "K2"

    def wait_on_sunrise(self):
        log.info("Waiting for sunrise...")
        while not self.solar_reader.is_online():
            # Check every 10 minutes to see if the solar system is online.
            time.sleep(600)

    @staticmethod
    def is_past_noon():
        dt = datetime.datetime.now()

        return dt.hour > 12

    def main_loop(self):
        """
        Main running loop.

        Every 10 minutes, the system will get the current status of the solar cells and
        log it to the google spreadsheet.
        If the number of microinverters drops to 0 (meaning sunset has happened), it exits out.
        """

        # The solar panels keep exiting early: my suspicions are that it falls out early for sunset due to initial
        # variances in voltages causing mi to drop below 0 after initializing.
        # Once we detect some activity, stay up until at least the afternoon

        log.info("Entering main loop")
        while self.solar_reader.is_online() or not self.is_past_noon():
            if not self.is_past_noon() and not self.solar_reader.is_online():
                log.error("Solar system shows as offline yet it is still morning.")
            try:
                cur_wh = self.solar_reader.get_wh_production()
                cur_mis = self.solar_reader.get_mi_online()
                cur_watts = self.solar_reader.get_current_watt_production()

                # Fill each data element in piecewise.
                # Timestamp is handled within the function
                self.sheet_reader.update_row({
                    self.wh_col: cur_wh,
                    self.mi_col: cur_mis,
                    self.cur_kw_col: cur_watts,
                })

                log.info("Data written to Docs.")

                self.sheet_reader.log_ip_address(self.ext_ip_cell)

                # Try to log the weather. Run this separately so that a weather API error doesn't kill everything else
                self.sheet_reader.update_row({
                    self.weather_col: self.weather_reader.get_cloud_levels()
                })

            except Exception:
                log.exception("An exception occurred in the main loop.")
            finally:
                time.sleep(600)

        log.info("Solar system is offline. Signing off for the night.")

    def run(self):
        """Start up the system."""
        log.info("Started, initializing...")

        # Check to see if the system is online. If it is, then we'll start right up.

        if self.solar_reader.is_online():
            log.info("Solar system online on startup.")
            self.main_loop()

        # otherwise, if 0 microinverters are online, it's either day or night.
        # if it's nighttime, we'll kill the program and let cron revive it tomorrow.
        # otherwise, we'll waitloop until the sun rises.

        else:

            if not self.is_past_noon():
                self.wait_on_sunrise()
                log.info("Microinverters have started, seems like sunrise. Main loop starting.")
                self.main_loop()
            else:
                log.warning("Program was started after sunset. Shutting down.")

        log.info("Run call ending, program terminating.")


if __name__ == '__main__':
    # TODO Convert some of these into command line args
    dirname = os.path.join(os.path.dirname(__file__), "config.json")
    sheet_reader = SheetReader()
    solar_reader = SolarReader("enphase", "192.168.1")
    weather = WeatherData()

    solar_runner = SolarData(sheet_reader, solar_reader, weather)
    solar_runner.run()
