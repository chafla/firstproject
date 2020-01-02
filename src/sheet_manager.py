import datetime
import json
import os
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials

ts_format = "%m/%d/%Y %H:%M:%S"

log = logging.getLogger()


class SheetReader:
    """
    Reads and writes the google sheet that we'll be using.
    Requires a config.json file to be in the running directory.
    """

    def __init__(self, config_path: str = "config.json"):
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        with open(config_path, "r") as raw_config_json:
            config_json = json.load(raw_config_json)

        creds_path = config_json["service_account_json"]
        sheet_url = config_json["chart_url"]

        self._credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_path, self.scope)
        # credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
        self._gc = gspread.authorize(self._credentials)
        self._sh = self._gc.open_by_url(sheet_url)
        self.worksheet = self._sh.get_worksheet(0)

        self.ts_col = "A"
        self.wh_col = "B"
        self.mi_col = "C"
        self.cur_kw_col = "D"

    @property
    def gc(self):
        if self._credentials.access_token_expired:
            self._gc.login()
        return self._gc

    @property
    def cur_pos(self):
        """
        Represents the row that we have last edited. Stored on the sheet as a cell.
        """
        # TODO Add a routine to create this whole document, including setting a base for this value
        return self.worksheet.acell('F1').value

    @cur_pos.setter
    def cur_pos(self, value):
        self.worksheet.update_acell("F1", value)

    def update_row(self, watt_hours, mi_online, cur_generation):
        """Update a full row of data."""
        # TODO Update this so that we can pass in a dictionary (or kwargs) with a column and data
        timestamp_dt = datetime.datetime.now()
        timestamp_str = timestamp_dt.strftime(ts_format)
        # Increment the current position by 1
        cur_pos = int(self.cur_pos)
        self.cur_pos = str(cur_pos + 1)

        pos = str(self.cur_pos)

        self.worksheet.update_acell(self.ts_col + pos, timestamp_str)

        self.worksheet.update_acell(self.wh_col + pos, watt_hours)
        self.worksheet.update_acell(self.mi_col + pos, mi_online)
        self.worksheet.update_acell(self.cur_kw_col + pos, cur_generation)

        log.info("Data written to Docs: %s mW today" % watt_hours)


