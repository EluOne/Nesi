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
# Created: 22/05/15
# Modified: 22/05/15

from kivy.uix.tabbedpanel import TabbedPanelItem

import config
from nesi.api import getServerStatus
from nesi.functions import updateCurrentTime


class StarbasesTab(TabbedPanelItem):
    def fetch_starbases(self):
        print('fetch_starbases called')

        # Update the config.serverTime to now.
        updateCurrentTime()

        # getServerStatus(config.serverStatus, config.serverTime, self.status_bar)
        getServerStatus(config.serverConn.svrCacheExpire, config.serverTime, self.status_bar)

        # getJobs(self.status_bar)

        # self.job_grid.update_rows()
