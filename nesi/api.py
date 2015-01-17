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
# Created: 13/01/13
# Modified: 17/01/15

import datetime
import time

from kivy.network.urlrequest import UrlRequest

from xml.dom.minidom import parseString

import config


def getServerStatus(args, serverTime, target):
    # Only query the server if the cache time has expired.
    if serverTime >= args[2]:
        # Download the Account Industry Data from API server
        apiURL = config.rootUrl + 'server/ServerStatus.xml.aspx/'

        def server_status(self, result):
            status = []
            XMLData = parseString(result)

            result = XMLData.getElementsByTagName('result')
            serveropen = result[0].getElementsByTagName('serverOpen')
            onlineplayers = result[0].getElementsByTagName('onlinePlayers')
            cacheuntil = XMLData.getElementsByTagName('cachedUntil')

            if (serveropen[0].firstChild.nodeValue):
                status.append('Tranquility Online')
                server = config.serverConn + ' Online'
            else:
                status.append('Server down.')
                server = config.serverConn + ' Down'

            status.append(onlineplayers[0].firstChild.nodeValue)

            players = (onlineplayers[0].firstChild.nodeValue)
            cacheExpire = datetime.datetime(*(time.strptime((cacheuntil[0].firstChild.nodeValue), '%Y-%m-%d %H:%M:%S')[0:6]))
            status.append(cacheExpire)

            config.serverStatus = status

            target.server = str(server)
            target.players = str(players)
            target.serverTime = str(config.serverTime)
            target.jobsCachedUntil = str(cacheExpire)

        def server_error(request, error):
            # TODO: Add a call to the popup() widget style
            status = [('Error Connecting to Tranquility: ' + str(error)), '0', serverTime]
            # config.serverStatus = status

            print(status)

        UrlRequest(apiURL, on_success=server_status, on_error=server_error, req_headers=config.headers)
