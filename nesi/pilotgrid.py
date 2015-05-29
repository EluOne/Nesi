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
# Created: 29/05/15
# Modified: 29/05/15

from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

import config


class PilotGrid(GridLayout):
    def __init__(self, **kwargs):
        # Display the current data on first load from the config json files.
        super(PilotGrid, self).__init__(**kwargs)
        self.bind(minimum_height=self.setter('height'))
        if config.pilotRows:
            numItems = list(range(len(config.pilotRows)))
            for r in numItems:
                self.add_widget(Label(font_size='12sp', id=str(config.pilotRows[r].characterID), text=str(config.pilotRows[r].characterName)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].corporationName)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].keyID)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].keyType)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].keyExpires)))

    def add_row(self, characterID, characterName, corporationName, keyID, keyType, keyExpires):
        # Add a row to the existing parent without clearing the current widgets.
        print('Adding Rows')
        self.add_widget(Label(font_size='12sp', id=str(characterID), text=str(characterName)))
        self.add_widget(Label(font_size='12sp', text=str(corporationName)))
        self.add_widget(Label(font_size='12sp', text=str(keyID)))
        self.add_widget(Label(font_size='12sp', text=str(keyType)))
        self.add_widget(Label(font_size='12sp', text=str(keyExpires)))

    def update_rows(self):
        # At present clear the grid and start fresh.
        self.clear_widgets()
        if config.jobRows:
            numItems = list(range(len(config.jobRows)))
            for r in numItems:
                self.add_widget(Label(font_size='12sp', id=str(config.pilotRows[r].characterID), text=str(config.pilotRows[r].characterName)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].corporationName)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].keyID)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].keyType)))
                self.add_widget(Label(font_size='12sp', text=str(config.pilotRows[r].keyExpires)))
