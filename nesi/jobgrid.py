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
# Modified: 31/05/15

from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

import config


class JobGrid(GridLayout):
    def __init__(self, **kwargs):
        # Display the current data on first load from the config json files.
        super(JobGrid, self).__init__(**kwargs)
        self.bind(minimum_height=self.setter('height'))
        if config.jobRows:
            numItems = list(range(len(config.jobRows)))
            for r in numItems:
                # self.add_widget(Label(font_size='12sp', id=str(config.jobRows[r].jobID), text=str(config.jobRows[r].completedStatus)))
                self.add_widget(Label(font_size='12sp', id=str(config.jobRows[r].jobID), text=str(config.jobRows[r].state)))
                self.add_widget(Label(font_size='12sp', text=str(config.activities[config.jobRows[r].activityID])))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installedItemTypeID)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installedInSolarSystemID)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installerID)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installTime)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].endProductionTime)))

    def add_row(self, state, activityID, installedItemTypeID, installedInSolarSystemID,
                installerID, installTime, endProductionTime):
        # Add a row to the existing parent without clearing the current widgets.
        print('Adding Rows')
        self.add_widget(Label(font_size='12sp', text=str(state)))
        self.add_widget(Label(font_size='12sp', text=str(config.activities[activityID])))
        self.add_widget(Label(font_size='12sp', text=str(installedItemTypeID)))
        self.add_widget(Label(font_size='12sp', text=str(installedInSolarSystemID)))
        self.add_widget(Label(font_size='12sp', text=str(installerID)))
        self.add_widget(Label(font_size='12sp', text=str(installTime)))
        self.add_widget(Label(font_size='12sp', text=str(endProductionTime)))

    def update_rows(self):
        # At present clear the grid and start fresh.
        self.clear_widgets()
        if config.jobRows:
            numItems = list(range(len(config.jobRows)))
            for r in numItems:
                # self.add_widget(Label(font_size='12sp', id=str(config.jobRows[r].jobID), text=str(config.jobRows[r].completedStatus)))
                self.add_widget(Label(font_size='12sp', id=str(config.jobRows[r].jobID), text=str(config.jobRows[r].state)))
                self.add_widget(Label(font_size='12sp', text=str(config.activities[config.jobRows[r].activityID])))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installedItemTypeID)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installedInSolarSystemID)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installerID)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].installTime)))
                self.add_widget(Label(font_size='12sp', text=str(config.jobRows[r].endProductionTime)))
