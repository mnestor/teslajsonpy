import calendar
import datetime
import json
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from teslajsonpy.Exceptions import TeslaException


class ConnectionTeslaFi(object):
    """Connection to Tesla Motors API"""

    def __init__(self, token, miles=False, rated=False):
        """Initialize connection object"""
        self.user_agent = 'Model S 2.1.79 (SM-G900V; Android REL 4.4.4; en_US'
        self.baseurl = 'https://www.teslafi.com/feed.php'
        self.token = token
        self._miles = miles
        self._rated = rated

    def get(self, command=""):
        """Utility command to get data from API"""
        wrap = False
        if command == 'vehicles':
            command = 'lastGoodTemp'
            wrap = True
        elif command == 'command/charge_max_range':
            command = 'set_charge_limit&charge_limit_soc=100'
        elif command == 'command/charge_standard':
            command = 'set_charge_limit&charge_limit_soc=80'

        if command == 'set_temps':
            return {'response': {'result': False}}

        data = self.__open(command, {'User-Agent': self.user_agent})

        # munge the data to fit tesla.com data
        for key, value in data.items():
            if key.endswith('_tempF') or key.endswith('_settingF'):
                data[key] = int(data[key])
            elif key.endswith('_temp') or key.endswith('_setting'):
                # temps in C have decimal
                data[key] = float(data[key])
            elif key.startswith('odometer'):
                # odometer && odometerF are floats
                data[key] = float(data[key])
            elif key in (
                    'id',
                    'vehicle_id',
                    'charge_current_request',
                    'charge_limit_soc',
                    'charger_power',
                    'charger_pilot_current',
                    'charger_actual_current',
                    'battery_current',
                    'usable_battery_level',
                    'charge_limit_soc_std',
                    'battery_level',
                    'max_range_charge_counter',
                    'charge_limit_soc_max',
                    'charger_voltage',
                    'charge_current_request_max',
                    'charge_limit_soc_min',
                    'heading',
                    'gps_as_of',
                    'seat_heater_rear_left_back',
                    'seat_heater_rear_right_back',
                    'fan_status',
                    'sun_roof_installed',
                    'ft',
                    'seat_type'
            ):
                if data[key] != '':
                    data[key] = int(data[key])
            elif key in (
                'time_to_full_charge',
                'battery_range',
                'charge_energy_added',
                'ideal_battery_range',
                'est_battery_range',
                'charge_rate',
                'charge_miles_added_ideal',
                'charge_miles_added_rated',
                'longitude',
                'latitude',
                'driver_temp_setting'
            ):
                data[key] = float(data[key])
            elif value in ('False', 'True'):
                data[key] = value == 'True'

        if self._miles:
            data['gui_distance_units'] = 'mi/hr'
        if self._rated:
            data['gui_range_display'] = 'Rated'

        if wrap:
            data = [data]

        return {'response': data}

    def post(self, command, data={}):
        return self.get(command)

    def __sethead(self, access_token):
        pass

    def __open(self, command, headers={}, data=None, baseurl=""):
        """Raw urlopen command"""
        data = {
            'token': self.token,
            'command': command
        }
        url = "%s?%s" % (self.baseurl, urlencode(data))
        req = Request(url, headers=headers)
        opener = build_opener()

        try:
            resp = opener.open(req)
            charset = resp.info().get('charset', 'utf-8')
            data = json.loads(resp.read().decode(charset))
            opener.close()
            return data
        except HTTPError as e:
            print(e)
            if e.code == 408:
                return False
            else:
                raise TeslaException(e.code)


class ConnectionTesla(object):
    """Connection to Tesla Motors API"""

    def __init__(self, email, password):
        """Initialize connection object"""
        self.user_agent = 'Model S 2.1.79 (SM-G900V; Android REL 4.4.4; en_US'
        self.client_id = "81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384"
        self.client_secret = "c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3"
        self.baseurl = 'https://owner-api.teslamotors.com'
        self.api = '/api/1/'
        self.oauth = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "email": email,
            "password": password}
        self.expiration = 0

    def get(self, command):
        """Utility command to get data from API"""
        return self.post(command, None)

    def post(self, command, data={}):
        """Utility command to post data to API"""
        now = calendar.timegm(datetime.datetime.now().timetuple())
        if now > self.expiration:
            auth = self.__open("/oauth/token", data=self.oauth)
            self.__sethead(auth['access_token'])
        return self.__open("%s%s" % (self.api, command), headers=self.head, data=data)

    def __sethead(self, access_token):
        """Set HTTP header"""
        self.access_token = access_token
        now = calendar.timegm(datetime.datetime.now().timetuple())
        self.expiration = now + 1800
        self.head = {"Authorization": "Bearer %s" % access_token,
                     "User-Agent": self.user_agent
                     }

    def __open(self, url, headers={}, data=None, baseurl=""):
        """Raw urlopen command"""
        if not baseurl:
            baseurl = self.baseurl
        req = Request("%s%s" % (baseurl, url), headers=headers)
        try:
            req.data = urlencode(data).encode('utf-8')
        except TypeError:
            pass
        opener = build_opener()

        try:
            resp = opener.open(req)
            charset = resp.info().get('charset', 'utf-8')
            data = json.loads(resp.read().decode(charset))
            opener.close()
            return data
        except HTTPError as e:
            if e.code == 408:
                return False
            else:
                raise TeslaException(e.code)
