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
# Modified: 19/03/15

import datetime
import time

from kivy.storage.jsonstore import JsonStore

from nesi.classes import Server, Character, Job

from nesi.api import apiCheck


# These are the headers sent with our http requests to be nice to CCP if they need to contact us.
version = '1.2.1-kivy'
headers = {'User-Agent': ('Nesi/%s +https://github.com/EluOne/Nesi' % version)}

# Static sqlLite data dump
staticDB = '../static.db'


# Account for device clock drift in our time calculations.
# nesi.functions.checkClockDrift will compare the server time vs the device reported UTC time.
offset = '-'
clockDrift = datetime.timedelta(0)

# Establish some current time data for calculations later.
# Server Time is UTC so we will use that for now generated locally.
serverTime = datetime.datetime.utcnow().replace(microsecond=0)

# Client Time reported locally.
localTime = datetime.datetime.now().replace(microsecond=0)


# Cache Files
jobCache = JsonStore('jobs.json')
pilotCache = JsonStore('pilots.json')
statusCache = JsonStore('server.json')


# Server connection objects can be reused for each connection point
# to the api as each one may have a different cache timer.
# Server(serverName, serverAddress, serverStatus, serverPlayers, datetime.datetime(cacheExpire), serverPing)
if statusCache.exists('server'):
    print('Server Status Already Exists:', statusCache.get('server'))

    # This possibly needs moving/redesign
    if (statusCache.get('server')['name']) == 'Tranquility':
        apiURL = 'https://api.eveonline.com/'
    elif (statusCache.get('server')['name']) == 'Singularity':
        apiURL = 'https://api.testeveonline.com/'
    else:
        apiURL = ''

    serverConn = Server(statusCache.get('server')['name'], apiURL, statusCache.get('server')['status'], statusCache.get('server')['players'],
                        datetime.datetime(*(time.strptime((statusCache.get('server')['cacheExpires']), '%Y-%m-%d %H:%M:%S')[0:6])),
                        statusCache.get('server')['ping'])
else:
    # Provide a default here.
    # Singularity Test Server:
    # serverConn = Server('Singularity', 'https://api.testeveonline.com/', 'Unknown', 0, serverTime, 0)
    # Tranquility Main Server:
    serverConn = Server('Tranquility', 'https://api.eveonline.com/', 'Unknown', 0, serverTime, 0)


# Dictionaries for POS status conversions.
activities = {1: 'Manufacturing', 2: 'Technological research', 3: 'Time Efficiency Research', 4: 'Material Research',
              5: 'Copy', 6: 'Duplicating', 7: 'Reverse Engineering', 8: 'Invention'}  # POS activities list.

states = {0: 'Unanchored', 1: 'Anchored / Offline', 2: 'Onlining', 3: 'Reinforced', 4: 'Online'}  # POS state list.


# API End Points
# Returns a list of all outpost and POS industrial facilities your corporation owns. (cache: 1 hour)
corpFacilities = 'corp/Facilities.xml.aspx'

# Returns a list of running and completed jobs for your corporation, up to 90 days or 10000 rows. (cache: 6 hours)
corpIndustryHistory = 'corp/IndustryJobsHistory.xml.aspx'

# Returns a list of running and completed jobs for your character, up to 90 days or 10000 rows. (cache: 6 hours)
charIndustryHistory = 'char/IndustryJobsHistory.xml.aspx'

# Returns a list of running jobs for your corporation, up to 90 days or 10000 rows. (cache: 15 minutes)
corpIndustry = 'corp/IndustryJobs.xml.aspx'

# Returns a list of running jobs for your character, up to 90 days or 10000 rows. (cache: 15 minutes)
charIndustry = 'char/IndustryJobs.xml.aspx'


# Defaults that will be replaced by the API returned data.
# ['Server Online', Players, Cache Expire]
# serverStatus = ['', '0', serverTime]

# Global variables to store the cacheUtil time and table rows.
jobsCachedUntil = serverTime
starbaseCachedUntil = serverTime


# This is where we are storing our API keys.
pilotRows = []

if pilotCache.count() > 0:
    print('Character Data Already Exists:')
    for key in pilotCache:
        print(key)  # Using characterID as key
        print(pilotCache.get(key)['characterName'])
        # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
        pilotRows.append(Character(pilotCache.get(key)['keyID'], pilotCache.get(key)['vCode'],
                                   pilotCache.get(key)['characterID'], pilotCache.get(key)['characterName'],
                                   pilotCache.get(key)['corporationID'], pilotCache.get(key)['corporationName'],
                                   pilotCache.get(key)['keyType'], pilotCache.get(key)['keyExpires'],
                                   pilotCache.get(key)['skills'], pilotCache.get(key)['isActive']))
else:
    print('Key to be removed when we have a preference dialog working. Leave array empty')
    # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
    keyID = '368187'
    vCode = 'lbT36nQrx1up6gvYqdGtdHrR6IfTvFncubFFBD9U6ZszIIqNMtXSV2l13Xxv6jXL'
    if (keyID != '') and (vCode != ''):
        pilots = apiCheck(keyID, vCode)
    # pilotRows = []


# Job data storage.
jobRows = []

if jobCache.count() > 0:
    print('Job Data Already Exists:')
    for key in jobCache:
        print(key)  # Using characterID as key
        print(jobCache.get(key)['characterName'])
        # jobID, completedStatus, activityID, installedItemTypeID, outputLocationID,
        # installedInSolarSystemID, installerID, runs, outputTypeID, installTime, endProductionTime
        jobRows.append(Job(jobCache.get(key)['jobID'], jobCache.get(key)['status'],
                           jobCache.get(key)['activityID'], jobCache.get(key)['blueprintTypeName'],
                           jobCache.get(key)['outputLocationID'], jobCache.get(key)['solarSystemName'],
                           jobCache.get(key)['installerName'], jobCache.get(key)['runs'],
                           jobCache.get(key)['productTypeName'], jobCache.get(key)['startDate'],
                           jobCache.get(key)['endDate']))
    jobsCachedUntil = datetime.datetime(*(time.strptime((statusCache.get('jobs')['cacheExpires']), '%Y-%m-%d %H:%M:%S')[0:6]))
else:
    print('No Job data set cache to Expired.')
    jobsCachedUntil = serverTime
