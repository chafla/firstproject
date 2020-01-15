import datetime
import json
import logging
import gspread
from requests import get
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
        self._worksheet = self._sh.get_worksheet(0)

        self.ts_col = "A"

        self.ext_ip_cell = "K2"
        self.int_ip_cell = "L2"

    @property
    def gc(self) -> gspread.Client:
        if self._credentials.access_token_expired:
            self._gc.login()
        return self._gc

    @property
    def worksheet(self) -> gspread.Worksheet:
        """Use a property to make sure that we refresh our access token if needed"""
        if self._credentials.access_token_expired:
            self._gc.login()
        return self._worksheet

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

    def write_cell(self, rowcol: str, value):
        """
        Write a value to a cell
        :param rowcol: Rowcol value, like A5 or BA3
        :param value: Value to write
        """
        self.worksheet.update_acell(rowcol, value)

    def update_row(self, data: dict, ts_col="A"):
        """
        Update a full row of data.
        Extra data can be added through kwargs like
        kwargs = {
            "A": 3,
            "B": 4
        },

        where key is the column and the value is the data to place there.
        The data will be placed at the next active column.

        Do not fill in A, as that will be used for a timestamp.

        """

        # TODO Update this so that we can pass in a dictionary (or kwargs) with a column and data
        timestamp_dt = datetime.datetime.now()
        timestamp_str = timestamp_dt.strftime(ts_format)
        # Increment the current position by 1
        cur_pos = int(self.cur_pos)
        self.cur_pos = str(cur_pos + 1)

        pos = str(self.cur_pos)

        self.worksheet.update_acell(ts_col + pos, timestamp_str)

        for col, value in data.items():
            self.worksheet.update_acell(col + pos, value)
