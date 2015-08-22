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

from kivy.uix.screenmanager import Screen

import config

from nesi.classes import Character
from nesi.api import apiCheck


class Pilots(Screen):
    def __init__(self, **kwargs):
        # Get the current data on first load from the config json files.
        super(Pilots, self).__init__(**kwargs)
        self.tempPilotRows = config.pilotRows[:]

    def onAdd(self):
        print('onAdd Called')
        numPilotRows = list(range(len(self.tempPilotRows)))
        keyID, vCode = (self.keyID.text, self.vCode.text)
        print(keyID, vCode)

        if (keyID != '') or (vCode != ''):  # Check neither field was left blank.
            for x in numPilotRows:
                if (self.keyID.text == self.tempPilotRows[x].keyID) and (self.vCode.text == self.tempPilotRows[x].vCode):
                    keyID, vCode = ('', '')  # We already have this key so null it so next check fails

            if (keyID != '') and (vCode != ''):
                pilots = apiCheck(keyID, vCode)

                print(pilots)  # Console debug

                if pilots != []:
                    for row in pilots:
                        # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                        self.tempPilotRows.append(Character(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], 0))

        # Update the list on screen.
        # self.charList.SetObjects(self.tempPilotRows)

    def onRefresh(self):
        self.refreshPilotRows = []
        numPilotRows = list(range(len(self.tempPilotRows)))

        for x in numPilotRows:
            if (self.tempPilotRows[x].keyID) and (self.tempPilotRows[x].vCode):
                if x > 0 and (self.tempPilotRows[x].keyID == self.tempPilotRows[x - 1].keyID):
                    keyID, vCode = ('', '')  # We already have this key so null it so next check fails
                else:
                    keyID, vCode = (self.tempPilotRows[x].keyID, self.tempPilotRows[x].vCode)

            if (keyID != '') and (vCode != ''):
                pilots = apiCheck(keyID, vCode)

                # print(pilots)  # Console debug

                if pilots != []:
                    for row in pilots:
                        # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                        self.refreshPilotRows.append(Character(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], 0))

        self.tempPilotRows = self.refreshPilotRows
        # Update the list on screen.
        # self.charList.SetObjects(self.tempPilotRows)

    def onDelete(self):
        numPilotRows = list(range(len(self.tempPilotRows)))

        for x in self.charList.GetSelectedObjects():
            # print(x.keyID, x.characterID)

            for y in numPilotRows:
                if (x.keyID == self.tempPilotRows[y].keyID) and (x.characterID == self.tempPilotRows[y].characterID):
                    self.tempPilotRows[y] = 'deleted'

            for z in self.tempPilotRows[:]:
                if z == 'deleted':
                    self.tempPilotRows.remove(z)

        # Update the list on screen.
        # self.charList.SetObjects(self.tempPilotRows)

    def onSave(self):
        config.pilotRows = self.tempPilotRows[:]
        # Lets reset the cache time as we have updated the api keys.
        config.jobsCachedUntil = config.serverTime
        config.starbaseCachedUntil = config.serverTime
        # Clear the JSON file and refill with current data.
        config.pilotCache.clear()
        if config.pilotRows != []:
            for row in config.pilotRows:
                # Add the rows to the pilotCache JSON file using characterID as key.
                # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                # config.pilotCache.put(row[2], keyID=row[0], vCode=row[1], characterID=row[2], characterName=row[3],
                #                      corporationID=row[4], corporationName=row[5], keyType=row[6], keyExpires=row[7],
                #                      skills=row[8], isActive=0)
                config.pilotCache.put(row.characterID, keyID=row.keyID, vCode=row.vCode, characterID=row.characterID,
                                      characterName=row.characterName, corporationID=row.corporationID,
                                      corporationName=row.corporationName, keyType=row.keyType, keyExpires=str(row.keyExpires),
                                      skills=row.skills, isActive=row.isActive)
        self.manager.current = 'nesi_screen'
