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
# Created: 01/02/15
# Modified: 02/03/15

import datetime

from nesi.error import onError

import config


# Adjust the local reported UTC time to compensate for the calculated clock drift.
def updateCurrentTime():
    if config.offset == '-':
        config.serverTime = datetime.datetime.utcnow().replace(microsecond=0) - config.clockDrift
    else:
        config.serverTime = datetime.datetime.utcnow().replace(microsecond=0) + config.clockDrift

    # Debug output:
    print('Offset: %s%s Adjusted Time: %s' % (config.offset, config.clockDrift, config.serverTime))


# Make sure the time on our device is correct and warn if incorrect.
def checkClockDrift(serCurrentTime):
    # As the serverTime in config may have been adjusted to compensate for the previous offset calc
    # we will get the current time reported from the device in UTC to recalculate.
    localUtcTime = datetime.datetime.utcnow().replace(microsecond=0)

    if serCurrentTime > localUtcTime:
        # Device clock is behind so we will add the difference.
        config.clockDrift = serCurrentTime - localUtcTime
        config.offset = '+'
    else:
        # Device clock in ahead so we will deduct the difference.
        config.clockDrift = localUtcTime - serCurrentTime
        config.offset = '-'

    # Debug output if greater than 0 difference.
    if config.clockDrift > datetime.timedelta(0):
        print('Clock Drift:\nServer Reports: %s\nDevice Reports: %s' % (str(serCurrentTime), str(localUtcTime)))

    # Warn the user if the clock drift is significant. (Set to 5 minutes)
    if config.clockDrift > datetime.timedelta(minutes=5):
        driftWarn = 'Warning Device Clock Drift:\nServer Reports: %s\nDevice Reports: %s' % (str(serCurrentTime), str(localUtcTime))
        onError(driftWarn)


# Used in id2location to check for 32bit numbers
def is32(n):
    try:
        bitstring = bin(n)
    except (TypeError, ValueError):
        return False

    if len(bin(n)[2:]) <= 32:
        return True
    else:
        return False
