#!/usr/bin/python
"""Nova Echo Science & Industry"""
# Copyright (C) 2015  Tim Cumming
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
# Created: 16/01/15
# Modified: 31/05/15

from kivy.properties import StringProperty
from kivy.uix.gridlayout import GridLayout


class StatusBar(GridLayout):
    server = StringProperty('Not Connected')
    players = StringProperty('0')
    serverTime = StringProperty('No Data')
    jobsCachedUntil = StringProperty('No Data')
    state = StringProperty('Idle')
