__author__ = 'Matt'
from lxml import html
import sys, getopt
import requests
import logging
import re
import json
# import urllib2
from urllib.error import URLError
from datetime import datetime, timezone
import time
from logging.handlers import RotatingFileHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

dirname = os.path.dirname(__file__)
# filename = os.path.join(dirname, 'relative/path/to/file/you/want')

log = logging.getLogger()


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
# log.addHandler(stderr_handler)

'''
Worked on in summer of 2015.
Accesses solar array and scrapes values from the web GUI, then throws them onto a Google Sheet where the values can be
handled. Will be run as a CRON job.

This could probably be compacted and made substantially neater. Especially by having the program itself run every 30
minutes, rather than constantly.

'''

number_pattern = re.compile(r"([\d.]+)")


def cur_time(format):
    if format == "s":  # Time
        current_time = str((datetime.time(datetime.now())))
        current_time = current_time[0:8]
    elif format == "f":  # Date & Time
        current_time = str(((datetime.now())))
        current_time = current_time[0:18]
    else:
        current_time = str(((datetime.now())))
        current_time = current_time[0:18]
        # I know this is lazy but I'll do it anyway
    return current_time


time_now = cur_time("s")
date_now = cur_time("f")

# a = Astral()

# with open("locale_info.json", "r") as f:
#     locale = json.load(f)

u_tm = datetime.utcfromtimestamp(0)
l_tm = datetime.fromtimestamp(0)
l_tz = timezone(l_tm - u_tm)

# city = a[locale["city_name"]]
# a.solar_depression = "civil"
# sun =

# Google Spreadsheet stuff. I could store things locally but this will make things at least a bit easier.
log.info("PySolar v.0.0")
log.info("[%s] Initializing..." % cur_time("f"))
#print "Connecting to Drive..."

# Drive init
# json_key = json.load(open())
scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]
with open(os.path.join(dirname, "config.json"), "r") as raw_config_json:
    config_json = json.load(raw_config_json)

creds_path = config_json["service_account_json"]
sheet_url = config_json["chart_url"]

json_path = os.path.join(dirname, creds_path)
credentials = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
# credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_url(sheet_url)
worksheet = sh.get_worksheet(0)
last_pos = worksheet.acell('F1').value

times_run = 0
ip_address = "192.168.1.22"
# ip_address_last_digit = 22  ## Reminder: Assign it a static IP


def cur_time(format):
    if format == "s":  # Time
        current_time = str(datetime.time(datetime.now()))
        current_time = current_time[0:8]
    elif format == "f":  # Date & Time
        current_time = str(datetime.now())
        current_time = current_time[0:18]
    else:
        current_time = str(datetime.now())
        current_time = current_time[0:18]
        # I know this is lazy but I'll do it anyway
    return current_time


time_now = cur_time("s")
date_now = cur_time("f")


def internet_on():
    log.info("Determining connection to the internet...")
    try:
        response = requests.get('http://google.com', timeout=1)
        log.info("Connected successfully")
        return True
    except URLError as err:
        log.info("Error: Could not connect")
        raise
    return False


def local_internet_on(ip):
    log.info("Determining connection to solar system...")
    try:
        response = requests.get('http://%s' % ip, timeout=10)
        log.info("Connected successfully")
        return response.status_code == 200
    except URLError as err:
        log.exception("Error: Can't connect to the solar array. Check the POE connection, or the status on the box.")
        raise
    return False


apache_address = "127.0.0.1:8000"


def apache_status():
    log.info("Determining webserver status...")
    try:
        response = requests.get('apache_address', timeout=1)
        log.info("Connected successfully")
        return True
    except URLError as err:
        log.info("Error: Could not connect")
        pass
    return False


def init():
    log.info("[%s]Starting..." % date_now)
    debug_loop()
    if get_mi_status == 0:  # Should adjust this so it doesn't screw up at night
        waitloop(0)
    elif get_mi_status != 0:  # If MIs are active already, jump right in.
        waitloop(-1)
    else:
        log.info("[%s]Something isn't right, can't get status of solar array. Quitting." % cur_time("f"))
        # Add something to open the webserver again, retrieve local IP address,
        #


#    next_sunset = home.previous_setting(ephem.Sun)
#    next_sunrise = home.previous_rising(ephem.Sun)


def get_data_today(verbose):  # Get today's total usage in kWh
    page = requests.get('http://%s/production' % ip_address)  # Pull the webpage
    tree = html.fromstring(page.text)
    data = tree.xpath("/html/body/div[1]/table/tr[3]/td[2]/text()")  # Grab the value
    if verbose:
        log.info("Total power supplied today:", data[0])

    match = number_pattern.findall(data[0])
    try:
        data_float = float(match[0])
    except ValueError:
        log.exception("Couldn't convert to float")
        return 0
    # cur_kw = float(data[0].strip().rstrip(" kW"))

    if "kW" in data[0]:
        data_float *= 1000

    energy_Wh = int(data_float)  # Convert it to the base unit, watt hours, to make math easier
    return energy_Wh


def get_mi_status(verbose):  # Boolean
    if verbose:
        log.info("Determining current solar cell status...")
    page = requests.get('http://%s/home' % ip_address)
    tree = html.fromstring(page.text)
    data = tree.xpath("/html/body/table/tr/td[2]/table/tr[5]/td[2]/text()")
    mi_online = int(data[0])
    # Note: I had to remove tbody from xpath Chrome gave me, and add '/text()' after it.
    if verbose:
        log.info("%s out of 24 microinverters online" % mi_online)
    return mi_online


def get_current_w():
    page = requests.get("http://%s/production" % ip_address)
    tree = html.fromstring(page.text)
    data = tree.xpath("/html/body/div[1]/table/tr[2]/td[2]/text()")
    match = number_pattern.findall(data[0])
    try:
        data_float = float(match[0])
    except ValueError:
        log.exception("Couldn't convert to float")
        return 0
    # cur_kw = float(data[0].strip().rstrip(" kW"))

    if "kW" in data[0]:
        data_float *= 1000  # Convert it to watts
    return data_float


def debug_loop():
    global ip_address  # oof
    # Try to see if the IP address has been changed
    local_ip_works = False
    try:
        local_ip_works = local_internet_on(ip_address)
    except:
        log.exception("Error occurred when connecting to local page")
    if not local_ip_works:
        ip_address = worksheet.acell("J2").value
        local_internet_on(ip_address)  # If this crashes out it's fine
    internet_on()  # This, however, needs to work
    get_data_today(False)
    get_mi_status(True)


def waitloop(iteration):  # 0 = sunrise wait, 1 = main loop, 2 = shutting down, -1 = jump to daytime mode
    time4 = cur_time("s")
    then = datetime.now()
    # current_day = datetime.now(l_tz)
    if iteration == 0:
        log.info("[%s]Waiting for sunrise..." % cur_time("f"))
        sc_active = False
        while not sc_active:
            if get_mi_status(False) > 0:  # Check to see if at least one photoreceptor is active
                iteration = 1
                sc_active = True
                return sc_active
            else:
                time.sleep(600)  # Otherwise, wait for 5 minutes and then check again.
        waitloop(1)
    elif iteration == 1:
        log.info("[%s] Solar cells reporting activity, starting up." % date_now)
        runningloop(False)
        # Here is where the publishing function will go. Will need to check status of solar panels.
    elif iteration == 2:
        log.info("[%s] Solar cells inactive. Shutting down." % date_now)
        # Here is where either a SystemExit will go or something more controlled. Also needs to check status.
        raise SystemExit()
    elif iteration == -1:
        log.info("Jumping right to daytime mode")
        runningloop(False)
    else:
        log.info("Something isn't right, you shouldn't see this.")


"""
The webserver that I'm going to get running is probably going to be an Apache server, because it looks like it might
just be easier to implement. There will probably be zero communication between the webserver and python (except maybe
to check status). as most data will be retrieved by Google Docs. Maybe I could implement this a little nicer at some
future point in time.


Otherwise, what seems to work pretty well is just pushing the data to Google Docs and handling the data there.
"""


def runningloop(debug):  # Main loop that runs and reports to the webserver [which I'll still need to get running.]
    # log.info("[%s} Starting Apache Server..." % date_now)
    # subprocess.call(['C:\\Temp\\a b c\\Notepad.exe', 'C:\\test.txt']) # Set this up on the raspi
    # log.info("Webserver started at %s" % apache_address)
    log.info("Setting things up with Google Docs...")
    log.info("Everything is ready, will now wait until sunset.")
    # working_cell = (last_pos)
    last_pos = worksheet.acell('F1').value
    sunset = False
    last_data = 0
    data = 0
    cur_data = 0
    n = 5
    first_loop = True
    # for _ in range(5): # Probably going to change this, this is like this for debugging only
    while not sunset:
        try:
            mi_online = get_mi_status(False)
            cur_kw_generation = get_current_w()
            # if 0 <= mi_online <= 24:
            #   log.info("Note: Microinverters are not fully active, shutdown soon.")
            if mi_online == 0:
                sunset = True
            if first_loop:
                cur_data = get_data_today(False)
            if not first_loop:  # Don't subtract the value if it's the first time looping.
                # last_data = worksheet.acell("B" + last_pos).value
                cur_data = get_data_today(False)
                # cur_data = int(data) - int(last_data)
            # cur_data /= 1000           # Too lazy to implement floats rn
            # last_pos = worksheet.acell('F1').value
            cur_pos = str(int(last_pos) + 1)
            cur_cell = "B" + "%s" % cur_pos
            ts_cell = "A" + "%s" % cur_pos
            mi_cell = "C" + "%s" % cur_pos
            kw_cell = "D" + "%s" % cur_pos
            worksheet.update_acell(cur_cell, cur_data)
            worksheet.update_acell(ts_cell, cur_time("f"))
            worksheet.update_acell(mi_cell, mi_online)
            worksheet.update_acell(kw_cell, cur_kw_generation)
            worksheet.update_acell("F1", cur_pos)
            last_pos = cur_pos
            first_loop = False
            log.info("[%s] Data written to Docs: %s mW today" % (cur_time("f"), get_data_today(False)))
        except Exception:
            log.exception("Something failed while running the main loop")
        finally:
            # Worth noting the system seems to update the web interface about every 10 minutes or so
            if not sunset:
                time.sleep(600)

    log.info("[%s] Zero microinverters online. Preparing for night." % cur_time("f"))
    waitloop(2)


"""
I'm going to want to add a CROM job on the raspi that starts at 5:30 or something and ends at a reasonable time
around sunset. Will probably end when the microinverter status drops, ephem sunset matches datetime.now(), or just
at some basic time.
"""

if __name__ == '__main__':
    # init()
    debug_loop()
    waitloop(0)
    # if (get_mi_status()) == 0:
    runningloop(False)
