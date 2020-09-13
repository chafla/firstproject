import datetime
import os
import sys
import time
from enum import Enum
import logging
from logging.handlers import RotatingFileHandler

import requests
import argparse

from src.sheet_manager import SheetReader
from src.solar_reader import SolarReader
from src.weather import WeatherData
from src.csv_writer import CSVWriter

log = logging.getLogger()

dirname = os.path.dirname(__file__)

handler = RotatingFileHandler(os.path.join(dirname, "pysolar.log"), mode='a', maxBytes=5*1024*1024,
                              backupCount=2, encoding="utf-8", delay=0)
log.setLevel(logging.INFO)
# handler = logging.FileHandler(filename=os.path.join(dirname, "pysolar.log"), encoding='utf-8', mode='a')
formatter = logging.Formatter("{asctime} - {levelname} - {message}", style="{")
stdout_handler = logging.StreamHandler(sys.stdout)
# stderr_handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(formatter)
stdout_handler.setFormatter(formatter)
# stderr_handler.setFormatter(formatter)
log.addHandler(handler)
log.addHandler(stdout_handler)

log = logging.getLogger()


class State(Enum):
    SUNRISE_WAIT = 0
    SYS_ONLINE = 1
    SUNSET = 2


class SolarData:
    def __init__(self, sheet_reader: SheetReader, solar_reader: SolarReader, weather_reader: WeatherData,
                 csv_path: str = None):
        """
        Create a new solar processor class.
        :param sheet_reader: Sheet reader responsible for processing the excel sheet
        :param solar_reader: Solar reader responsible for parsing/accessing the solar panel web ui
        :param weather_reader:
        :param csv_path:
        """
        self.sheet_reader = sheet_reader
        self.solar_reader = solar_reader
        self.weather_reader = weather_reader

        self.db_fields = ["timestamp", "wh", "mi_online", "cur_kw_output", "cloud_cover"]

        self.database_writer = CSVWriter(csv_path, self.db_fields)

        self.state = State.SUNRISE_WAIT

        self.wh_col = "B"
        self.mi_col = "C"
        self.cur_kw_col = "D"
        self.weather_col = "E"

        self.ext_ip_cell = "K2"

        self._prev_ip = None

    @property
    def _ip_address(self):
        ext_ip = requests.get("https://api.ipify.org").text
        if ext_ip != self._prev_ip:
            log.info("IP address has changed to {}".format(ext_ip))
        self._prev_ip = ext_ip
        return ext_ip

    # def log_ip_address(self):
    #     """
    #     Log our internal and external IP address to the sheet
    #     """
    #
    #     ip = self._ip_address
    #     if self._prev_ip != ip:
    #         self.worksheet.update_acell(cell, ip)
    #         log.info("IP address updated to {}".format(ip))
    #         self._prev_ip = ip
    #

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
                cloud_cover = self.weather_reader.get_cloud_levels()

                # Fill each data element in piecewise.
                # Timestamp is handled within the function
                self.sheet_reader.update_row({
                    self.wh_col: cur_wh,
                    self.mi_col: cur_mis,
                    self.cur_kw_col: cur_watts,
                    self.weather_col: cloud_cover
                })

                csv_row_data = {
                    "timestamp": time.time(),
                    "wh": cur_wh,
                    "mi_online": cur_mis,
                    "cur_kw_output": cur_watts,
                    "cloud_cover": cloud_cover
                }

                self.database_writer.write_row(csv_row_data)

                log.info("Data written to Docs.")

                # Take note of our IP address as well
                self.sheet_reader.write_cell(self.ext_ip_cell, self._ip_address)

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

    parser = argparse.ArgumentParser(description="Track solar panel data over an extended period of time.")
    parser.add_argument("-c", "--config", help="Location of the json config file",
                        type=str, default=os.path.join(os.path.dirname(__file__), "config.json"))

    parser.add_argument("-a", "--address", help="Base address range to search for solar panels (xxx.xxx.xxx, "
                                                "leaving out the last field)",
                        type=str, default="192.168.1")

    parser.add_argument("-o", "--output", help="Path to the output .csv file",
                        type=str, default="output.csv")

    args = parser.parse_args()

    # TODO Convert some of these into command line args
    sheet_reader = SheetReader()
    solar_reader = SolarReader("enphase", args.address)
    weather = WeatherData()

    solar_runner = SolarData(sheet_reader, solar_reader, weather, args.output)
    solar_runner.run()
