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


version = '1.2.1-kivy'
headers = {'User-Agent': ('Nesi/%s +https://github.com/EluOne/Nesi' % version)}

# Singularity Test Server
serverConn = 'Singularity'
rootUrl = 'https://api.testeveonline.com/'

# Tranquility Main Server
# serverConn = 'Tranquility'
# rootUrl = 'https://api.eveonline.com/'


# Establish some current time data for calculations later.
# Server Time is UTC so we will use that for now generated locally.
serverTime = datetime.datetime.utcnow().replace(microsecond=0)

# Client Time reported locally.
localTime = datetime.datetime.now().replace(microsecond=0)

# Defaults that will be replaced by the API returned data.
serverStatus = ['', '0', serverTime]

# Global variables to store the cacheUtil time and table rows.
jobsCachedUntil = serverTime
starbaseCachedUntil = serverTime

# This is where we are storing our API keys for now.
pilotRows = []
