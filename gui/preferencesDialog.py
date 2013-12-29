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

import wx
import pickle

from ObjectListView import ColumnDefn, GroupListView

import config
from common.classes import Character
from common.api import apiCheck


def apiRowFormatter(listItem, row):  # Formatter for GroupListView, will turn expired api keys red.
    if row.keyExpires != 'Never':
        if row.keyExpires < config.serverTime:
            listItem.SetTextColour(wx.RED)


def apiGroupKeyConverter(groupKey):
    # Convert the given group key (which is a date) into a representation string
    return 'API Key: %s' % (groupKey)


class PreferencesDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, size=wx.DefaultSize, style=wx.DEFAULT_DIALOG_STYLE)
        self.SetTitle("Nesi - Preferences")

        self.label_4 = wx.StaticText(self, -1, "Key ID:")
        self.keyIDTextCtrl = wx.TextCtrl(self, -1, "")
        self.label_5 = wx.StaticText(self, -1, "vCode:")
        self.vCodeTextCtrl = wx.TextCtrl(self, -1, "")
        self.addBtn = wx.Button(self, wx.ID_ADD, "")
        self.charList = GroupListView(self, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL)
        self.deleteBtn = wx.Button(self, wx.ID_DELETE)
        self.refreshBtn = wx.Button(self, wx.ID_REFRESH)
        self.saveBtn = wx.Button(self, wx.ID_SAVE)

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.saveBtn.Bind(wx.EVT_BUTTON, self.onSave)
        self.addBtn.Bind(wx.EVT_BUTTON, self.onAdd)
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.onDelete)
        self.refreshBtn.Bind(wx.EVT_BUTTON, self.onRefresh)

    def __set_properties(self):
        # begin wxGlade: PreferenceDialog.__set_properties
        self.SetTitle("Preferences")
        self.SetSize((750, 300))
        self.keyIDTextCtrl.SetMinSize((120, 21))
        self.vCodeTextCtrl.SetMinSize((300, 21))
        self.saveBtn.SetDefault()
        # end wxGlade
        self.charList.SetEmptyListMsg('Fill in boxes above and\n click + to add pilots')

        self.charList.SetFont(wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))

        self.charList.rowFormatter = apiRowFormatter
        self.charList.SetColumns([
            ColumnDefn('Character Name', 'left', 170, 'characterName'),
            ColumnDefn('Corporation', 'left', 225, 'corporationName'),
            ColumnDefn('API Key', 'left', 80, 'keyID', groupKeyConverter=apiGroupKeyConverter),
            ColumnDefn('Key Type', 'left', 90, 'keyType'),
            ColumnDefn('Expires', 'left', 150, 'keyExpires')
        ])
        self.charList.SetSortColumn(self.charList.columns[3])
        self.tempPilotRows = config.pilotRows[:]
        self.charList.SetObjects(self.tempPilotRows)

    def __do_layout(self):
        # begin wxGlade: PreferenceDialog.__do_layout
        prefSizer = wx.BoxSizer(wx.VERTICAL)
        prefBtnSizer = wx.BoxSizer(wx.HORIZONTAL)
        prefAddSizer = wx.BoxSizer(wx.HORIZONTAL)
        prefAddSizer.Add(self.label_4, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        prefAddSizer.Add(self.keyIDTextCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        prefAddSizer.Add(self.label_5, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        prefAddSizer.Add(self.vCodeTextCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        prefAddSizer.Add(self.addBtn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        prefSizer.Add(prefAddSizer, 1, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 0)
        prefSizer.Add(self.charList, 3, wx.EXPAND, 0)
        prefBtnSizer.Add(self.cancelBtn, 0, wx.ADJUST_MINSIZE, 0)
        prefBtnSizer.Add(self.deleteBtn, 0, wx.ADJUST_MINSIZE, 0)
        prefBtnSizer.Add(self.refreshBtn, 0, wx.ADJUST_MINSIZE, 0)
        prefBtnSizer.Add(self.saveBtn, 0, wx.ADJUST_MINSIZE, 0)
        prefSizer.Add(prefBtnSizer, 1, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL, 0)
        self.SetSizer(prefSizer)
        self.Layout()
        # end wxGlade

    def onAdd(self, event):
        numPilotRows = list(range(len(self.tempPilotRows)))
        keyID, vCode = (self.keyIDTextCtrl.GetValue(), self.vCodeTextCtrl.GetValue())

        if (keyID != '') or (vCode != ''):  # Check neither field was left blank.
            for x in numPilotRows:
                if (self.keyIDTextCtrl.GetValue() == self.tempPilotRows[x].keyID) and (self.vCodeTextCtrl.GetValue() == self.tempPilotRows[x].vCode):
                    keyID, vCode = ('', '')  # We already have this key so null it so next check fails

            if (keyID != '') and (vCode != ''):
                pilots = apiCheck(keyID, vCode)

                # print(pilots)  # Console debug

                if pilots != []:
                    for row in pilots:
                        # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                        self.tempPilotRows.append(Character(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], 0))

        self.charList.SetObjects(self.tempPilotRows)

    def onRefresh(self, event):
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
        self.charList.SetObjects(self.tempPilotRows)

    def onDelete(self, event):
        numPilotRows = list(range(len(self.tempPilotRows)))

        for x in self.charList.GetSelectedObjects():
            # print(x.keyID, x.characterID)

            for y in numPilotRows:
                if (x.keyID == self.tempPilotRows[y].keyID) and (x.characterID == self.tempPilotRows[y].characterID):
                    self.tempPilotRows[y] = 'deleted'

            for z in self.tempPilotRows[:]:
                if z == 'deleted':
                    self.tempPilotRows.remove(z)

        self.charList.SetObjects(self.tempPilotRows)

    def onSave(self, event):
        config.pilotRows = self.tempPilotRows[:]
        config.jobsCachedUntil = config.serverTime  # Lets reset the cache time as we have updated the api keys.
        if config.pilotRows != []:
            iniFile = open('nesi.ini', 'w')
            pickle.dump(config.pilotRows, iniFile)
            iniFile.close()
        self.EndModal(0)
