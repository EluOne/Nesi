#!/usr/bin/python
"""Nova Echo Science & Industry"""
# Copyright (C) 2013  Tim Cumming
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Tim Cumming aka Elusive One
# Created: 29/12/13
# Modified: 17/01/15

import datetime
from nesi.classes import Server


# These are the headers sent with our http requests to be nice to CCP if they need to contact us.
version = '1.2.1-kivy'
headers = {'User-Agent': ('Nesi/%s +https://github.com/EluOne/Nesi' % version)}

# Static sqlLite data dump
staticDB = '../static.db'

# Cache Files
# TODO: change to JSON files
characterCache = '../character.cache'

# Account for device clock drift in our time calculations.
# nesi.functions.checkClockDrift will compare the server time vs the device reported UTC time.
offset = '-'
clockDrift = datetime.timedelta(0)

# Establish some current time data for calculations later.
# Server Time is UTC so we will use that for now generated locally.
serverTime = datetime.datetime.utcnow().replace(microsecond=0)

# Client Time reported locally.
localTime = datetime.datetime.now().replace(microsecond=0)


# Server connection objects can be reused for each connection point
# to the api as each one may have a different cache timer.
# Server(serverName, serverAddress, serverStatus, serverPlayers, cacheExpire)

# Singularity Test Server
serverConn = Server('Singularity', 'https://api.testeveonline.com/', 'Unknown', 0, serverTime)

# Tranquility Main Server
# serverConn = Server('Tranquility', 'https://api.eveonline.com/', 'Unknown', 0, serverTime)


# Defaults that will be replaced by the API returned data.
# ['Server Online', Players, Cache Expire]
# serverStatus = ['', '0', serverTime]

# Global variables to store the cacheUtil time and table rows.
jobsCachedUntil = serverTime
starbaseCachedUntil = serverTime

# This is where we are storing our API keys for now.
pilotRows = []
