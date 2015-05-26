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
# Created: 09/05/15
# Modified: 26/05/15

from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

import config


class JobGrid(GridLayout):
    def __init__(self, **kwargs):
        super(JobGrid, self).__init__(**kwargs)
        self.bind(minimum_height=self.setter('height'))
        if config.jobRows:
            numItems = list(range(len(config.jobRows)))
            for r in numItems:
                self.add_widget(Label(font_size=12, id=str(config.jobRows[r].jobID), text=str(config.jobRows[r].completedStatus)))
                self.add_widget(Label(font_size=12, id=str(config.jobRows[r].jobID), text=str(config.activities[config.jobRows[r].activityID])))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installedItemTypeID)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installedInSolarSystemID)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installerID)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installTime)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].endProductionTime)))

    def add_row(self, completedStatus, activityID, installedItemTypeID, installedInSolarSystemID,
                installerID, installTime, endProductionTime):
        print('Adding Rows')
        self.add_widget(Label(font_size=12, text=str(completedStatus)))
        self.add_widget(Label(font_size=12, text=str(config.activities[activityID])))
        self.add_widget(Label(font_size=12, text=str(installedItemTypeID)))
        self.add_widget(Label(font_size=12, text=str(installedInSolarSystemID)))
        self.add_widget(Label(font_size=12, text=str(installerID)))
        self.add_widget(Label(font_size=12, text=str(installTime)))
        self.add_widget(Label(font_size=12, text=str(endProductionTime)))

    def update_rows(self):
        # At present clear the grid and start fresh.
        self.clear_widgets()
        if config.jobRows:
            numItems = list(range(len(config.jobRows)))
            for r in numItems:
                self.add_widget(Label(font_size=12, id=str(config.jobRows[r].jobID), text=str(config.jobRows[r].completedStatus)))
                self.add_widget(Label(font_size=12, id=str(config.jobRows[r].jobID), text=str(config.activities[config.jobRows[r].activityID])))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installedItemTypeID)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installedInSolarSystemID)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installerID)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].installTime)))
                self.add_widget(Label(font_size=12, text=str(config.jobRows[r].endProductionTime)))
