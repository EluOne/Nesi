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
# Created: 21/04/13

import os.path
import pickle
import datetime
import time
import math

import wx

import urllib2
import httplib
import traceback
import sqlite3 as lite

from xml.dom.minidom import parseString
from ObjectListView import ObjectListView, ColumnDefn, GroupListView

import config

from common.classes import Character, Job, Starbase, Materials, MlAnalysis
from common.api import onError, getServerStatus, id2location, id2name

from gui.preferencesDialog import PreferencesDialog


# Defaults that will be replaced by the API returned data.
serverStatus = ['', '0', config.serverTime]
starbaseCachedUntil = config.serverTime  # This needs to be moved to the global module so it can be reset by the prefs dialog.

jobRows = []
starbaseRows = []

# These will be the lists for the ui choices on the manufacturing tab.
bpoList = []
installList = []

# Lets try to load up our API keys from the ini file.
# This requires the Pilot class to work.
if (os.path.isfile('nesi.ini')):
    iniFile = open('nesi.ini', 'r')
    config.pilotRows = pickle.load(iniFile)
    iniFile.close()


class AutoComboBox(wx.ComboBox):  # FIXME: Why is this broken on Windoze?
    def __init__(self, parent, value, choices=[], style=0, **par):
        wx.ComboBox.__init__(self, parent, wx.ID_ANY, value, style=style | wx.CB_DROPDOWN, choices=choices, **par)
        self.choices = choices
        self.Bind(wx.EVT_CHAR, self.EvtChar)
        self.Bind(wx.EVT_TEXT, self.EvtText)

    def EvtChar(self, event):
        event.Skip()

    def EvtText(self, event):
        currentText = str(event.GetString()).lower()
        found = False
        newChoices = []

        if len(currentText) == 0:
            self.Clear()
            self.AppendItems(self.choices)

        for choice in self.choices:
            # Check entered text at start and within string of choices.
            if (choice.lower().find(currentText) > 0) or (choice.lower().startswith(currentText)):
                newChoices.append(choice)
                found = True

        if found:
            self.Clear()
            self.AppendItems(newChoices)
        else:
            event.Skip()


# The functions below are for OjectListView output formatting.


def jobRowFormatter(listItem, row):  # Formatter for ObjectListView, will turn completed jobs green.
    if row.timeRemaining < datetime.timedelta(0):
        listItem.SetTextColour((0, 192, 0))


def activityConv(act):
    activities = {1: 'Manufacturing', 2: 'Technological research', 3: 'Time Efficiency Research', 4: 'Material Research',
                    5: 'Copy', 6: 'Duplicating', 7: 'Reverse Engineering', 8: 'Invention'}  # POS activities list.
    if act in activities:
        return activities[act]
    else:
        return act


def stateConv(state):
    states = {0: 'Unanchored', 1: 'Anchored / Offline', 2: 'Onlining', 3: 'Reinforced', 4: 'Online'}  # POS state list.
    if state in states:
        return states[state]
    else:
        return state


def datetimeConv(timeStr):
    # Trim the seconds off the display date time same as client. As we want to store the exact time for calcs.
    return str(timeStr)[:-3]


def humanFriendly(value):
    # '{:,}'.format(value) Uses the Format Specification Mini-Language to produce more human friendly output.
    return '{:,}'.format(int(value))


class MainWindow(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MainWindow.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        self.fileMenu = wx.Menu()
        self.menuAbout = wx.MenuItem(self.fileMenu, wx.ID_ABOUT, "&About", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuAbout)
        self.menuConfig = wx.MenuItem(self.fileMenu, wx.ID_PREFERENCES, "&Configure", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuConfig)
        self.menuExit = wx.MenuItem(self.fileMenu, wx.ID_EXIT, "E&xit", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuExit)
        self.frame_menubar.Append(self.fileMenu, "File")
        self.SetMenuBar(self.frame_menubar)
        # Menu Bar end

        self.statusbar = self.CreateStatusBar(1, 0)
        self.bitmap_1 = wx.StaticBitmap(self, -1, wx.Bitmap("images/nesi.png", wx.BITMAP_TYPE_ANY))
        self.label_1 = wx.StaticText(self, -1, "Nova Echo Science and Industry")
        self.mainNotebook = wx.Notebook(self, -1, style=0)

        # Job tab widgets
        self.notebookJobPane = wx.Panel(self.mainNotebook, -1)
        self.jobBtn = wx.Button(self.notebookJobPane, -1, "Get Jobs")
        self.jobList = ObjectListView(self.notebookJobPane, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.jobDetailBox = wx.TextCtrl(self.notebookJobPane, -1, "", style=wx.TE_MULTILINE)

        # Starbases (POS) tab widgets
        self.notebookStarbasePane = wx.Panel(self.mainNotebook, -1)
        self.starbaseBtn = wx.Button(self.notebookStarbasePane, -1, "Refresh")
        self.starbaseList = ObjectListView(self.notebookStarbasePane, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.starbaseDetailBox = wx.TextCtrl(self.notebookStarbasePane, -1, "", style=wx.TE_MULTILINE)

        # Manufacturing tab initialisation and widgets
        if bpoList == [] and installList == []:  # Build a list of all blueprints and facilities from the static data dump.
            try:
                con = lite.connect('static.db')

                with con:
                    cur = con.cursor()
                    statement = """SELECT r.blueprintTypeID, r.productTypeID, t.typeName, r.wasteFactor, r.productionTime, r.productivityModifier
                                FROM invblueprinttypes AS r INNER JOIN invTypes AS t ON r.blueprintTypeID = t.typeID ORDER BY t.typeName;"""
                    cur.execute(statement)

                    rows = cur.fetchall()

                    for row in rows:
                        # blueprintTypeID, productTypeID, typeName, wasteFactor, productionTime, productivityModifier
                        bpoList.append([int(row[0]), int(row[1]), str(row[2]), int(row[3]), int(row[4]), int(row[5])])

                    cur = con.cursor()
                    statement = """SELECT assemblyLineTypeID, assemblyLineTypeName, baseTimeMultiplier, baseMaterialMultiplier
                                FROM ramassemblylinetypes WHERE activityId = 1;"""
                    cur.execute(statement)

                    rows = cur.fetchall()

                    for row in rows:
                        # assemblyLineTypeID, assemblyLineTypeName, baseTimeMultiplier, baseMaterialMultiplier
                        installList.append([int(row[0]), str(row[1]), float(row[2]), float(row[3])])

            except lite.Error as err:
                error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
                onError(error)
            finally:
                if con:
                    con.close()

        # Append both lists to their respective selection boxes.
        choices = [""]
        for i in range(len(bpoList)):
            choices.append(str(bpoList[i][2]))

        installChoices = []
        for i in range(len(installList)):
            installChoices.append(str(installList[i][1]))

        pilotChoices = []
        for i in range(len(config.pilotRows)):
            # The pilot might be in more than one api key, but not all may have skills lists.
            if (config.pilotRows[i].characterName not in pilotChoices) and (config.pilotRows[i].skills != {}):
                pilotChoices.append(str(config.pilotRows[i].characterName))

        self.notebookManufacturingPane = wx.Panel(self.mainNotebook, wx.ID_ANY)
        self.pilotChoice = wx.Choice(self.notebookManufacturingPane, wx.ID_ANY, choices=pilotChoices)
        self.peLabel = wx.StaticText(self.notebookManufacturingPane, wx.ID_ANY, ("Material Efficiency"))  # Renamed in Rubicon 1.1
        self.manufactPESpinCtrl = wx.SpinCtrl(self.notebookManufacturingPane, wx.ID_ANY, "0", min=0, max=5)  # Pilot Production Efficiency Skill
        self.indLabel = wx.StaticText(self.notebookManufacturingPane, wx.ID_ANY, ("Industry"))
        self.manufactIndSpinCtrl = wx.SpinCtrl(self.notebookManufacturingPane, wx.ID_ANY, "0", min=0, max=5)  # Pilot Industry Skill
        self.pilotSizer_staticbox = wx.StaticBox(self.notebookManufacturingPane, wx.ID_ANY, ("Pilot"))

        # The AutoComboBox custom class is currently broken on the windows platform.
        if 'wxMSW' in wx.PlatformInfo:
            self.bpoSelector = wx.ComboBox(self.notebookManufacturingPane, wx.ID_ANY, choices=choices)
        else:
            self.bpoSelector = AutoComboBox(self.notebookManufacturingPane, "", choices, style=wx.CB_DROPDOWN)

        self.mlLabel = wx.StaticText(self.notebookManufacturingPane, wx.ID_ANY, ("ML"))
        self.manufactMLSpinCtrl = wx.SpinCtrl(self.notebookManufacturingPane, wx.ID_ANY, "", min=-10, max=5000)
        self.plLabel = wx.StaticText(self.notebookManufacturingPane, wx.ID_ANY, ("PL"))
        self.manufactPLSpinCtrl = wx.SpinCtrl(self.notebookManufacturingPane, wx.ID_ANY, "", min=-10, max=5000)
        self.qtyLabel = wx.StaticText(self.notebookManufacturingPane, wx.ID_ANY, ("Runs"))
        self.manufactQtySpinCtrl = wx.SpinCtrl(self.notebookManufacturingPane, wx.ID_ANY, "1", min=1, max=10000)
        self.bpoSizer_staticbox = wx.StaticBox(self.notebookManufacturingPane, wx.ID_ANY, ("Blueprint"))

        # The AutoComboBox custom class is currently broken on the windows platform.
        if 'wxMSW' in wx.PlatformInfo:
            self.installChoice = wx.ComboBox(self.notebookManufacturingPane, wx.ID_ANY, choices=installChoices)
        else:
            self.installChoice = AutoComboBox(self.notebookManufacturingPane, "", installChoices, style=wx.CB_DROPDOWN)

        self.outputLabel = wx.StaticText(self.notebookManufacturingPane, wx.ID_ANY, ("Production Time"))
        self.outputTimeTextCtrl = wx.TextCtrl(self.notebookManufacturingPane, wx.ID_ANY, "")
        self.installSizer_staticbox = wx.StaticBox(self.notebookManufacturingPane, wx.ID_ANY, ("Installation"))
        self.mlAnalysisList = ObjectListView(self.notebookManufacturingPane, wx.ID_ANY, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.meAnalysisSizer_staticbox = wx.StaticBox(self.notebookManufacturingPane, wx.ID_ANY, ("Material Level Analysis"))
        self.bpoBtn = wx.Button(self.notebookManufacturingPane, wx.ID_ANY, ("Calculate"))
        self.manufactureList = GroupListView(self.notebookManufacturingPane, wx.ID_ANY, style=wx.LC_REPORT | wx.SUNKEN_BORDER)

        self.onSelectPilot(0)  # Call pilot selection to auto set skill based SpinCtrls

        self.Bind(wx.EVT_MENU, self.onAbout, self.menuAbout)
        self.Bind(wx.EVT_MENU, self.onConfig, self.menuConfig)
        self.Bind(wx.EVT_MENU, self.onExit, self.menuExit)

        self.Bind(wx.EVT_BUTTON, self.onGetJobs, self.jobBtn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onJobSelect, self.jobList)

        self.Bind(wx.EVT_BUTTON, self.onGetStarbases, self.starbaseBtn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onStarbaseSelect, self.starbaseList)

        self.Bind(wx.EVT_CHOICE, self.onSelectPilot, self.pilotChoice)
        self.Bind(wx.EVT_BUTTON, self.onBpoSelect, self.bpoBtn)  # Do the same as the combo selection.

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MainWindow.__set_properties
        self.SetTitle('Nesi')
        self.SetSize((1024, 600))
        self.SetBackgroundColour(wx.NullColour)  # Use system default colour
        self.bitmap_1.SetMinSize((64, 64))
        self.label_1.SetFont(wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        # end wxGlade

        self.statusbar.SetStatusText('Welcome to Nesi - Idle')

        # Jobs Notebook page
        # In game: Click "Get Jobs" to fetch jobs with current filters
        self.jobList.SetEmptyListMsg('Click \"Get Jobs\" to fetch jobs')
        self.jobList.SetFont(wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.jobDetailBox.SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))

        self.jobList.rowFormatter = jobRowFormatter
        self.jobList.SetColumns([
            ColumnDefn('State', 'left', 75, 'state'),
            ColumnDefn('Activity', 'left', 145, 'activityID', stringConverter=activityConv),
            ColumnDefn('Type', 'left', 250, 'installedItemTypeID'),
            ColumnDefn('Location', 'left', 150, 'outputLocationID'),
            ColumnDefn('Installer', 'left', 150, 'installerID'),
            ColumnDefn('Install Date', 'center', 110, 'installTime', stringConverter=datetimeConv),
            ColumnDefn('End Date', 'center', 110, 'endProductionTime', stringConverter=datetimeConv)
        ])

        # Starbase Notebook page
        self.starbaseList.SetEmptyListMsg('Click \"Refresh\" to get POS status\nThis requires a corporation API Key')
        self.starbaseList.SetFont(wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        self.starbaseDetailBox.SetFont(wx.Font(10, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))

        self.starbaseList.SetColumns([
            ColumnDefn('System', 'center', 220, 'locationID'),
            ColumnDefn('Moon', 'center', 220, 'moonID'),
            ColumnDefn('Type', 'left', 200, 'typeStr'),
            ColumnDefn('State', 'center', 130, 'state', stringConverter=stateConv),
            ColumnDefn('State From', 'center', 110, 'stateTimestamp', stringConverter=datetimeConv),
            ColumnDefn('Online Since / At', 'center', 110, 'onlineTimestamp', stringConverter=datetimeConv)
            #ColumnDefn('Standing Owner ID', 'left', 140, 'standingOwnerID')
        ])

        # Manufacturing Notebook page
        self.bpoSelector.SetSelection(0)

        self.mlAnalysisList.SetEmptyListMsg('Select a BPO from the\ndrop down above start')
        self.mlAnalysisList.SetFont(wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))

        self.mlAnalysisList.SetColumns([
            ColumnDefn('Item', 'left', 245, 'item'),
            ColumnDefn('Waste Eliminated at ML:', 'center', 245, 'perfect', stringConverter=humanFriendly),
        ])

        self.manufactureList.SetEmptyListMsg('Select a BPO from the\ndrop down on left to start')
        self.manufactureList.SetFont(wx.Font(9, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))

        self.manufactureList.SetColumns([
            ColumnDefn('Item', 'left', 200, 'item'),
            ColumnDefn('Quantity', 'center', 100, 'quantity', stringConverter=humanFriendly),
            ColumnDefn('Dmg/Job', 'center', 80, 'damage'),
            ColumnDefn('Waste', 'center', 100, 'waste'),
            ColumnDefn('Category', 'left', 100, 'category')
        ])
        self.manufactureList.SetSortColumn(self.manufactureList.columns[5])

        self.installChoice.SetSelection(0)
        self.outputTimeTextCtrl.SetMinSize((200, 21))

    def __do_layout(self):
        # begin wxGlade: MainWindow.__do_layout
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        manufactureSizer = wx.BoxSizer(wx.HORIZONTAL)
        manufactureSelectionSizer = wx.BoxSizer(wx.VERTICAL)
        self.meAnalysisSizer_staticbox.Lower()
        meAnalysisSizer = wx.StaticBoxSizer(self.meAnalysisSizer_staticbox, wx.VERTICAL)
        self.installSizer_staticbox.Lower()
        installSizer = wx.StaticBoxSizer(self.installSizer_staticbox, wx.VERTICAL)
        outputSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.bpoSizer_staticbox.Lower()
        bpoSizer = wx.StaticBoxSizer(self.bpoSizer_staticbox, wx.VERTICAL)
        bpoStatsSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.pilotSizer_staticbox.Lower()
        pilotSizer = wx.StaticBoxSizer(self.pilotSizer_staticbox, wx.VERTICAL)
        pilotSkillSizer = wx.BoxSizer(wx.HORIZONTAL)
        starbaseSizer = wx.BoxSizer(wx.VERTICAL)
        jobSizer = wx.BoxSizer(wx.VERTICAL)
        headerSizer = wx.BoxSizer(wx.HORIZONTAL)
        headerSizer.Add(self.bitmap_1, 0, wx.FIXED_MINSIZE, 0)
        headerSizer.Add(self.label_1, 0, wx.ALIGN_CENTER_VERTICAL | wx.FIXED_MINSIZE, 0)
        mainSizer.Add(headerSizer, 0, 0, 0)

        jobSizer.Add(self.jobBtn, 0, wx.ALIGN_RIGHT | wx.ADJUST_MINSIZE, 0)
        jobSizer.Add(self.jobList, 3, wx.EXPAND, 0)
        jobSizer.Add(self.jobDetailBox, 1, wx.EXPAND, 0)
        self.notebookJobPane.SetSizer(jobSizer)

        starbaseSizer.Add(self.starbaseBtn, 0, wx.ALIGN_RIGHT | wx.ADJUST_MINSIZE, 0)
        starbaseSizer.Add(self.starbaseList, 3, wx.EXPAND, 0)
        starbaseSizer.Add(self.starbaseDetailBox, 1, wx.EXPAND, 0)
        self.notebookStarbasePane.SetSizer(starbaseSizer)

        pilotSizer.Add(self.pilotChoice, 0, wx.ADJUST_MINSIZE, 0)
        pilotSkillSizer.Add(self.peLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        pilotSkillSizer.Add(self.manufactPESpinCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        pilotSkillSizer.Add(self.indLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        pilotSkillSizer.Add(self.manufactIndSpinCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        pilotSizer.Add(pilotSkillSizer, 1, wx.ALIGN_CENTER_HORIZONTAL, 0)
        manufactureSelectionSizer.Add(pilotSizer, 1, wx.EXPAND, 0)
        bpoSizer.Add(self.bpoSelector, 0, wx.ADJUST_MINSIZE, 0)
        bpoStatsSizer.Add(self.mlLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        bpoStatsSizer.Add(self.manufactMLSpinCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        bpoStatsSizer.Add(self.plLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        bpoStatsSizer.Add(self.manufactPLSpinCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        bpoStatsSizer.Add(self.qtyLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        bpoStatsSizer.Add(self.manufactQtySpinCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        bpoSizer.Add(bpoStatsSizer, 1, wx.ALIGN_CENTER_HORIZONTAL, 0)
        manufactureSelectionSizer.Add(bpoSizer, 1, wx.EXPAND, 0)
        installSizer.Add(self.installChoice, 0, wx.ADJUST_MINSIZE, 0)
        outputSizer.Add(self.outputLabel, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        outputSizer.Add(self.outputTimeTextCtrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ADJUST_MINSIZE, 0)
        installSizer.Add(outputSizer, 1, wx.ALIGN_CENTER_HORIZONTAL, 0)
        manufactureSelectionSizer.Add(installSizer, 1, wx.EXPAND, 0)
        meAnalysisSizer.Add(self.mlAnalysisList, 3, wx.EXPAND, 0)
        manufactureSelectionSizer.Add(meAnalysisSizer, 3, wx.EXPAND, 0)
        manufactureSelectionSizer.Add(self.bpoBtn, 0, wx.ALIGN_RIGHT | wx.ADJUST_MINSIZE, 0)
        manufactureSizer.Add(manufactureSelectionSizer, 1, wx.EXPAND, 0)
        manufactureSizer.Add(self.manufactureList, 1, wx.EXPAND, 0)
        self.notebookManufacturingPane.SetSizer(manufactureSizer)

        self.mainNotebook.AddPage(self.notebookJobPane, ("Jobs"))
        self.mainNotebook.AddPage(self.notebookStarbasePane, ("Starbases"))
        self.mainNotebook.AddPage(self.notebookManufacturingPane, ("Manufacturing"))
        mainSizer.Add(self.mainNotebook, 1, wx.EXPAND, 0)
        self.SetSizer(mainSizer)
        self.Layout()
        # end wxGlade

    def onGetJobs(self, event):
        """Event handler to fetch job data from server"""
        global jobRows
        global serverStatus

        timingMsg = 'Using Local Cache'
        config.serverTime = datetime.datetime.utcnow().replace(microsecond=0)  # Update Server Time.
        # Inform the user what we are doing.
        self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Connecting to Tranquility...')
        serverStatus = getServerStatus(serverStatus, config.serverTime)  # Try the API server for current server status.

        if serverStatus[0] == 'Tranquility Online':  # Status has returned a value other than online, so why continue?
            if config.serverTime >= config.jobsCachedUntil:
                # Start the clock.
                t = time.clock()
                tempJobRows = []
                if config.pilotRows != []:  # Make sure we have keys in the config
                    # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                    numPilotRows = list(range(len(config.pilotRows)))
                    for x in numPilotRows:  # Iterate over all of the keys and character ids in config
                        #Download the Account Industry Data
                        keyOK = 1  # Set key check to OK test below changes if expired
                        if config.pilotRows[x].keyExpires != 'Never':
                            if config.pilotRows[x].keyExpires < config.serverTime:
                                keyOK = 0
                                error = ('KeyID ' + config.pilotRows[x].keyID + ' has Expired')
                                onError(error)

                        if keyOK == 1:
                            if config.pilotRows[x].keyType == 'Corporation':
                                baseUrl = 'https://api.eveonline.com/corp/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s'
                            else:  # Should be an account key
                                baseUrl = 'https://api.eveonline.com/char/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s'

                            apiURL = baseUrl % (config.pilotRows[x].keyID, config.pilotRows[x].vCode, config.pilotRows[x].characterID)
                            # print(apiURL)  # Console debug

                            try:  # Try to connect to the API server
                                target = urllib2.urlopen(apiURL)  # download the file
                                downloadedData = target.read()  # convert to string
                                target.close()  # close file because we don't need it anymore:

                                XMLData = parseString(downloadedData)
                                dataNodes = XMLData.getElementsByTagName("row")

                                cacheuntil = XMLData.getElementsByTagName('cachedUntil')
                                cacheExpire = datetime.datetime(*(time.strptime((cacheuntil[0].firstChild.nodeValue), "%Y-%m-%d %H:%M:%S")[0:6]))
                                config.jobsCachedUntil = cacheExpire

                                itemIDs = []
                                installerIDs = []
                                locationIDs = []
                                for row in dataNodes:
                                    if row.getAttribute('completed') == '0':  # Ignore Delivered Jobs
                                        if int(row.getAttribute('installedItemTypeID')) not in itemIDs:
                                            itemIDs.append(int(row.getAttribute('installedItemTypeID')))
                                        if int(row.getAttribute('outputTypeID')) not in itemIDs:
                                            itemIDs.append(int(row.getAttribute('outputTypeID')))
                                        if int(row.getAttribute('installerID')) not in installerIDs:
                                            installerIDs.append(int(row.getAttribute('installerID')))
                                        if int(row.getAttribute('outputLocationID')) not in locationIDs:
                                            locationIDs.append(int(row.getAttribute('outputLocationID')))
                                        if int(row.getAttribute('installedInSolarSystemID')) not in locationIDs:
                                            locationIDs.append(int(row.getAttribute('installedInSolarSystemID')))

                                itemNames = id2name('item', itemIDs)
                                pilotNames = id2name('character', installerIDs)
                                locationNames = id2location(x, locationIDs, config.pilotRows)

                                for row in dataNodes:
                                    if row.getAttribute('completed') == '0':  # Ignore Delivered Jobs
                                        tempJobRows.append(Job(row.getAttribute('jobID'),
                                                        row.getAttribute('completedStatus'),
                                                        int(row.getAttribute('activityID')),  # Leave as int for clauses
                                                        itemNames[int(row.getAttribute('installedItemTypeID'))],
                                                        int(row.getAttribute('installedItemProductivityLevel')),
                                                        int(row.getAttribute('installedItemMaterialLevel')),
                                                        locationNames[int(row.getAttribute('outputLocationID'))],
                                                        locationNames[int(row.getAttribute('installedInSolarSystemID'))],
                                                        pilotNames[int(row.getAttribute('installerID'))],
                                                        int(row.getAttribute('runs')),
                                                        row.getAttribute('outputTypeID'),
                                                        row.getAttribute('installTime'),
                                                        row.getAttribute('endProductionTime')))

                                    # This is what is left from the API:
                                    #columns="assemblyLineID,containerID,installedItemLocationID,installedItemQuantity,
                                    #installedItemLicensedProductionRunsRemaining,outputLocationID,licensedProductionRuns,
                                    #installedInSolarSystemID,containerLocationID,materialMultiplier,charMaterialMultiplier,
                                    #timeMultiplier,charTimeMultiplier,containerTypeID,installedItemCopy,completed,
                                    #completedSuccessfully,installedItemFlag,outputFlag,completedStatus,beginProductionTime,
                                    #pauseProductionTime"

                            except urllib2.HTTPError as err:
                                error = ('HTTP Error: ' + str(err.code))  # Server Status String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                            except urllib2.URLError as err:
                                error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Server Status String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                            except httplib.HTTPException as err:
                                error = ('HTTP Exception')  # Server Status String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                            except Exception:
                                error = ('Generic Exception: ' + traceback.format_exc())  # Server Status String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                    if tempJobRows != []:
                        jobRows = tempJobRows[:]
                    self.jobList.SetObjects(jobRows)
                    timingMsg = 'Updated in: %0.2f ms' % (((time.clock() - t) * 1000))
                else:
                    onError('Please open Config to enter a valid API key')
            else:
                numItems = list(range(len(jobRows)))
                for r in numItems:
                    if jobRows[r].endProductionTime > config.serverTime:
                        jobRows[r].timeRemaining = jobRows[r].endProductionTime - config.serverTime
                        jobRows[r].state = 'In Progress'
                    else:
                        jobRows[r].timeRemaining = jobRows[r].endProductionTime - config.serverTime
                        jobRows[r].state = 'Ready'
                self.jobList.RefreshObjects(jobRows)
                # print('Not Contacting Server, Cache Not Expired')

            self.statusbar.SetStatusText(serverStatus[0] + ' - ' + serverStatus[1]
                                         + ' Players Online - EvE Time: ' + str(config.serverTime)
                                         + ' - API Cached Until: ' + str(config.jobsCachedUntil)
                                         + ' - ' + timingMsg)
        else:
            self.statusbar.SetStatusText('Welcome to Nesi - ' + serverStatus[0])

    def onJobSelect(self, event):
        """Handle showing details for item select from list"""
        currentItem = self.jobList[event.GetIndex()]

        if currentItem.timeRemaining < datetime.timedelta(0):
            details = 'TTC: Ready\n'
        else:
            human = str(currentItem.timeRemaining).split(':')  # Lets split the delta into a nice list for formatting.
            details = ('TTC: %s Hours %s Minutes %s Seconds\n' % (human[0], human[1], human[2]))

        ids = [int(currentItem.outputTypeID)]
        itemNames = id2name('item', ids)
        location = ('Output Location: %s - %s' % (currentItem.outputLocationID, currentItem.installedInSolarSystemID))

#       activities = {1: 'Manufacturing', 2: 'Technological research', 3: 'Time Efficiency Research', 4: 'Material Research',
#                    5: 'Copy', 6: 'Duplicating', 7: 'Reverse Engineering', 8: 'Invention'}  # POS activities list.
        if currentItem.activityID == 1:  # Manufacturing
            try:
                con = lite.connect('static.db')

                with con:
                    cur = con.cursor()
                    statement = "SELECT portionSize FROM invtypes WHERE typeID = '" + currentItem.outputTypeID + "'"
                    cur.execute(statement)

                    row = cur.fetchone()
                    details = ('%s%s\nOutput Type: %s x %s\n' %
                               (details, location, (int(currentItem.runs) * int(row[0])), itemNames[int(currentItem.outputTypeID)]))

            except lite.Error as err:
                error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
                onError(error)
                details = ('%s%s\nOutput Type: %s runs of %s\n' %
                           (details, location, currentItem.runs, itemNames[int(currentItem.outputTypeID)]))
            finally:
                if con:
                    con.close()
        elif currentItem.activityID == 2:  # Technological research
            details = ('%s%s x %s\n' % (details, currentItem.runs, itemNames[int(currentItem.outputTypeID)]))
        elif currentItem.activityID == 3:  # Time Efficiency Research
            details = ('%sInstall PE: %s\nEnd PE: %s\n%s\nOutput Type: 1 unit of %s\n' %
                (details, currentItem.installedItemProductivityLevel,
                (currentItem.installedItemProductivityLevel + currentItem.runs), location, itemNames[int(currentItem.outputTypeID)]))
        elif currentItem.activityID == 4:  # Material Research
            details = ('%sInstall ME: %s\nEnd ME: %s\n%s\nOutput Type: 1 unit of %s\n' %
                (details, currentItem.installedItemMaterialLevel,
                (currentItem.installedItemMaterialLevel + currentItem.runs), location, itemNames[int(currentItem.outputTypeID)]))
        elif currentItem.activityID == 5:  # Copy
            details = ('%s%s\nOutput Type: %s x %s\n' % (details, location, currentItem.runs, itemNames[int(currentItem.outputTypeID)]))
        elif currentItem.activityID == 6:  # Duplicating
            details = ('%s%s\nOutput Type: %s x %s\n' % (details, location, currentItem.runs, itemNames[int(currentItem.outputTypeID)]))
        elif currentItem.activityID == 7:  # Reverse Engineering
            details = ('%s%s\nOutput Type: %s x %s\n' % (details, location, currentItem.runs, itemNames[int(currentItem.outputTypeID)]))
        elif currentItem.activityID == 8:  # Invention
            details = ('%s%s\nOutput Type: %s x %s\n' % (details, location, currentItem.runs, itemNames[int(currentItem.outputTypeID)]))
        else:  # Fall back unknown activity
            details = ('%s%s\nOutput Type: %s runs of %s\n' % (details, location, currentItem.runs, itemNames[int(currentItem.outputTypeID)]))

        self.jobDetailBox.SetValue(details)

    def onGetStarbases(self, event):  # wxGlade: MainWindow.<event_handler>
        """Event handler to fetch starbase data from server"""
        global starbaseRows
        global serverStatus
        global starbaseCachedUntil

        timingMsg = 'Using Local Cache'
        config.serverTime = datetime.datetime.utcnow().replace(microsecond=0)  # Update Server Time.
        # Inform the user what we are doing.
        self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Connecting to Tranquility...')
        serverStatus = getServerStatus(serverStatus, config.serverTime)  # Try the API server for current server status.

        if serverStatus[0] == 'Tranquility Online':  # Status has returned a value other than online, so why continue?
            if config.serverTime >= starbaseCachedUntil:
                # Start the clock.
                t = time.clock()
                tempStarbaseRows = []
                if config.pilotRows != []:  # Make sure we have keys in the config
                    # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                    numPilotRows = list(range(len(config.pilotRows)))
                    for x in numPilotRows:  # Iterate over all of the keys and character ids in config
                        #Download the Account Starbase Data
                        keyOK = 1  # Set key check to OK test below changes if expired
                        if config.pilotRows[x].keyExpires != 'Never':
                            if config.pilotRows[x].keyExpires < config.serverTime:
                                keyOK = 0
                                error = ('KeyID ' + config.pilotRows[x].keyID + ' has Expired')
                                onError(error)

                        if keyOK == 1 and config.pilotRows[x].keyType == 'Corporation':
                            baseUrl = 'https://api.eveonline.com/corp/StarbaseList.xml.aspx?keyID=%s&vCode=%s'
                            apiURL = baseUrl % (config.pilotRows[x].keyID, config.pilotRows[x].vCode)
                            # print(apiURL)  # Console debug

                            try:  # Try to connect to the API server
                                target = urllib2.urlopen(apiURL)  # download the file
                                downloadedData = target.read()  # convert to string
                                target.close()  # close file because we don't need it anymore:

                                XMLData = parseString(downloadedData)
                                starbaseNodes = XMLData.getElementsByTagName("row")

                                cacheuntil = XMLData.getElementsByTagName('cachedUntil')
                                cacheExpire = datetime.datetime(*(time.strptime((cacheuntil[0].firstChild.nodeValue), "%Y-%m-%d %H:%M:%S")[0:6]))
                                starbaseCachedUntil = cacheExpire

                                for row in starbaseNodes:
                                    itemIDs = []
                                    locationIDs = []

                                    if int(row.getAttribute('typeID')) not in itemIDs:
                                        itemIDs.append(int(row.getAttribute('typeID')))

                                    baseUrl = 'https://api.eveonline.com/corp/StarbaseDetail.xml.aspx?keyID=%s&vCode=%s&itemID=%s'
                                    apiURL = baseUrl % (config.pilotRows[x].keyID, config.pilotRows[x].vCode, row.getAttribute('itemID'))
                                    # print(apiURL)  # Console debug

                                    try:  # Try to connect to the API server
                                        target = urllib2.urlopen(apiURL)  # download the file
                                        downloadedData = target.read()  # convert to string
                                        target.close()  # close file because we don't need it anymore:

                                        XMLData = parseString(downloadedData)
                                        starbaseDetailNodes = XMLData.getElementsByTagName("row")

                                        fuel = []
                                        for entry in starbaseDetailNodes:
                                            if int(entry.getAttribute('typeID')) not in itemIDs:
                                                itemIDs.append(int(entry.getAttribute('typeID')))
                                            fuel.append(int(entry.getAttribute('typeID')))
                                            fuel.append(int(entry.getAttribute('quantity')))

                                        if int(row.getAttribute('locationID')) not in locationIDs:
                                            locationIDs.append(int(row.getAttribute('locationID')))
                                        if int(row.getAttribute('moonID')) not in locationIDs:
                                            locationIDs.append(int(row.getAttribute('moonID')))

                                        itemNames = id2name('item', itemIDs)
                                        locationNames = id2location(x, locationIDs, config.pilotRows)

                                        tempStarbaseRows.append(Starbase(row.getAttribute('itemID'),
                                                        int(row.getAttribute('typeID')),
                                                        itemNames[int(row.getAttribute('typeID'))],
                                                        locationNames[int(row.getAttribute('locationID'))],
                                                        locationNames[int(row.getAttribute('moonID'))],
                                                        int(row.getAttribute('state')),
                                                        row.getAttribute('stateTimestamp'),
                                                        row.getAttribute('onlineTimestamp'),
                                                        fuel,
                                                        row.getAttribute('standingOwnerID')))

                                    # itemID,typeID,locationID,moonID,state,stateTimestamp,onlineTimestamp,standingOwnerID

                                    except urllib2.HTTPError as err:
                                        error = ('HTTP Error: %s %s' % (str(err.code), str(err.reason)))  # Error String
                                        self.statusbar.SetStatusText(error)
                                        onError(error)
                                    except urllib2.URLError as err:
                                        error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Server Status String
                                        self.statusbar.SetStatusText(error)
                                        onError(error)
                                    except httplib.HTTPException as err:
                                        error = ('HTTP Exception')  # Server Status String
                                        self.statusbar.SetStatusText(error)
                                        onError(error)
                                    except Exception:
                                        error = ('Generic Exception: ' + traceback.format_exc())  # Server Status String
                                        self.statusbar.SetStatusText(error)
                                        onError(error)

                            except urllib2.HTTPError as err:
                                error = ('HTTP Error: %s %s' % (str(err.code), str(err.reason)))  # Error String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                            except urllib2.URLError as err:
                                error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Server Status String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                            except httplib.HTTPException as err:
                                error = ('HTTP Exception')  # Server Status String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                            except Exception:
                                error = ('Generic Exception: ' + traceback.format_exc())  # Server Status String
                                self.statusbar.SetStatusText(error)
                                onError(error)
                    if tempStarbaseRows != []:
                        starbaseRows = tempStarbaseRows[:]
                    self.starbaseList.SetObjects(starbaseRows)
                    timingMsg = 'Updated in: %0.2f ms' % (((time.clock() - t) * 1000))
                else:
                    onError('Please open Config to enter a valid API key')
            else:
                self.starbaseList.RefreshObjects(jobRows)
                # print('Not Contacting Server, Cache Not Expired')

            self.statusbar.SetStatusText(serverStatus[0] + ' - ' + serverStatus[1]
                                         + ' Players Online - EvE Time: ' + str(config.serverTime)
                                         + ' - API Cached Until: ' + str(config.jobsCachedUntil)
                                         + ' - ' + timingMsg)
        else:
            self.statusbar.SetStatusText('Welcome to Nesi - ' + serverStatus[0])

    def onStarbaseSelect(self, event):  # wxGlade: MainWindow.<event_handler>
        """Handle showing details for item select from list"""
        currentItem = self.starbaseList[event.GetIndex()]

        details = ''
        fuelTypes = list(currentItem.fuel[::2])
        fuelQtys = list(currentItem.fuel[1::2])

        itemIDs = []
        fuelConsumption = {}

        if currentItem.typeID != '':  # We have a control tower id to work with
            try:
                con = lite.connect('static.db')

                with con:
                    cur = con.cursor()
                    #invcontroltowerresources (controlTowerTypeID,resourceTypeID,purpose,quantity,minSecurityLevel,factionID)
                    statement = "SELECT resourceTypeID, quantity FROM invcontroltowerresources WHERE controlTowerTypeID = ('" + str(currentItem.typeID) + "')"
                    cur.execute(statement)

                    rows = cur.fetchall()

                    for row in rows:
                        fuelConsumption.update({int(row[0]): int(row[1])})

            except lite.Error as err:
                error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
                onError(error)
            finally:
                if con:
                    con.close()

        for x in fuelTypes:
            itemIDs.append(x)

        itemNames = id2name('item', itemIDs)

        for x in range(len(fuelTypes)):  # Iterate over the returned fuel rows and format nicely. We are only really interested in days and whole hours.
            fuelTime = float(fuelQtys[x]) / float(fuelConsumption[int(fuelTypes[x])])
            fuelDays = int(fuelTime) / 24
            fuelHours = int(fuelTime) % 24

            details = ('%s%s x %s -' % (details, itemNames[int(fuelTypes[x])], fuelQtys[x]))

            if fuelDays == 1:
                details = ('%s %s Day' % (details, fuelDays))
            else:
                details = ('%s %s Days' % (details, fuelDays))

            if fuelHours == 1:
                details = ('%s %s Hour\n' % (details, fuelHours))
            else:
                details = ('%s %s Hours\n' % (details, fuelHours))

        self.starbaseDetailBox.SetValue(details)

    def onSelectPilot(self, event):
        currentSelection = self.pilotChoice.GetCurrentSelection()
        currentPilot = self.pilotChoice.GetString(currentSelection)
        #print(currentPilot)
        industrylvl = 0
        productionlvl = 0

        # skills 3380 = Industry, 3388 = Production Efficiency
        for i in range(len(config.pilotRows)):
            if (config.pilotRows[i].characterName == currentPilot) and (config.pilotRows[i].skills != {}):
                if 3380 in config.pilotRows[i].skills:
                    industrylvl = config.pilotRows[i].skills[3380]
                if 3388 in config.pilotRows[i].skills:
                    productionlvl = config.pilotRows[i].skills[3388]
                #print(industrylvl, productionlvl)

        self.manufactIndSpinCtrl.SetValue(industrylvl)
        self.manufactPESpinCtrl.SetValue(productionlvl)

    def onBpoSelect(self, event):
        """Handle showing details for item select from list"""
        tempManufacterRows = []
        tempMaterialLevelRows = []
        manufactureQty = self.manufactQtySpinCtrl.GetValue()
        maxME = 0

        # assemblyLineTypeID, assemblyLineTypeName, baseTimeMultiplier, baseMaterialMultiplier
        currentInstall = self.installChoice.GetCurrentSelection()
        installMaterialModifier = installList[currentInstall][3]

        currentItem = self.bpoSelector.GetValue()

        for i in range(len(bpoList)):
            if bpoList[i][2] == currentItem:
                itemID = i

        #bpoList[itemID][0 - Blueprint ID, 1 - Produced Item ID, 2 - Blueprint Name, 3 - Base Waste Factor]
        #print(bpoList[itemID][:])

        if currentItem >= 0:
            # Base materials from item in db using output item ID
            baseQuery = """SELECT t.typeName, m.quantity FROM invTypeMaterials AS m
                        INNER JOIN invTypes AS t ON m.materialTypeID = t.typeID WHERE m.typeID = """ + str(bpoList[itemID][1])

            # Extra materials from blueprint in db excluding skills using blueprint ID
            extraQuery = """SELECT t.typeName, r.quantity, r.damagePerJob, recycle, r.requiredTypeID FROM ramTypeRequirements AS r
                        INNER JOIN invTypes AS t ON r.requiredTypeID = t.typeID
                        INNER JOIN invGroups AS g ON t.groupID = g.groupID
                        WHERE r.typeID = """ + str(bpoList[itemID][0]) + """-- Blueprint ID
                        AND r.activityID = 1 -- Manufacturing
                        AND g.categoryID != 16"""

            # Skills from blueprint ID in db
            skillsQuery = """SELECT t.typeName, r.quantity FROM ramTypeRequirements AS r
                        INNER JOIN invTypes AS t ON r.requiredTypeID = t.typeID
                        INNER JOIN invGroups AS g ON t.groupID = g.groupID
                        WHERE r.typeID = """ + str(bpoList[itemID][0]) + """ -- Blueprint ID
                        AND r.activityID = 1 -- Manufacturing
                        AND g.categoryID = 16"""

            try:
                con = lite.connect('static.db')

                with con:
                    cur = con.cursor()

                    rawMaterials = {}
                    extraMaterials = {}
                    recycleItems = {}
                    skills = {}

                    cur.execute(baseQuery)  # Fetch Base Materials

                    baseRows = cur.fetchall()
                    #print((len(rows)))
                    for row in baseRows:
                        rawMaterials[str(row[0])] = int(row[1])

                    cur.execute(extraQuery)  # Fetch Extra Items

                    extraRows = cur.fetchall()
                    #print((len(rows)))
                    for row in extraRows:
                        extraMaterials[str(row[0])] = round((int(row[1]) * manufactureQty * installMaterialModifier), 0)
                        # Build a list of materials recovered from the items marked as recycled.
                        if row[3] == 1:  # Item to be recycled
                            # Recycled materials from ID of item to be reprocessed.
                            recycleQuery = """SELECT t.typeName, m.quantity FROM invTypeMaterials AS m INNER JOIN invTypes AS t
                                        ON m.materialTypeID = t.typeID WHERE m.typeID = """ + str(row[4])

                            cur.execute(recycleQuery)  # Fetch Skills

                            recycleRows = cur.fetchall()
                            #print((len(rows)))
                            for row in recycleRows:
                                recycleItems[str(row[0])] = int(row[1])

                    cur.execute(skillsQuery)  # Fetch Skills

                    skillRows = cur.fetchall()
                    #print((len(rows)))
                    for row in skillRows:
                        skills[str(row[0])] = int(row[1])

                # We need to deduct the items marked as recycled from the base materials.
                for key in recycleItems.keys():
                    if key in rawMaterials:
                        rawMaterials[key] = max(0, (rawMaterials[key] - recycleItems[key]))

                # We apply ME waste (by the percentage mentioned in invBlueprintTypes) and Production Efficiency waste.
                baseWasteFactor = float(bpoList[itemID][3])
                productionEfficiency = float(self.manufactPESpinCtrl.GetValue())  # The production efficiency skill of the pilot.

                for key in rawMaterials.keys():
                    if int(rawMaterials[key]) > 0:
                        materialAmount = float(rawMaterials[key])
                        materialLevel = float(self.manufactMLSpinCtrl.GetValue())  # The ME/ML of the researched blueprint.

                        # ME waste:
                        if materialLevel >= 0:
                            waste = round((materialAmount * (baseWasteFactor / 100) * (1 / (materialLevel + 1))), 2)
                        else:
                            waste = round((materialAmount * (baseWasteFactor / 100) * (1 - materialLevel)), 2)

                        perfectME = int(math.floor(0.02 * baseWasteFactor * materialAmount))

                        tempMaterialLevelRows.append(MlAnalysis(str(key), str(perfectME)))  # Have to send as a string else a zero value won't display.

                        if perfectME > maxME:
                            maxME = int(perfectME)

                        # Production efficiency waste:
                        peWaste = round((((25 - (5 * productionEfficiency)) * materialAmount) / 100), 2)

                        totalWaste = round((waste + peWaste), 0)  # We don't want any partial amounts here.
                        totalMaterials = round(((materialAmount + totalWaste) * manufactureQty * installMaterialModifier), 0)
                        if (perfectME > materialLevel) and (totalWaste > 0):
                            percentWaste = totalWaste * (100 / float(materialAmount))
                        else:
                            percentWaste = 0

                        #print(key, perfectME, waste, peWaste, materialAmount, (materialAmount + waste + peWaste), percentWaste, baseWasteFactor)

                        # Build the list to be displayed. This is where we round to the nearest interger so the calcs all work.
                        tempManufacterRows.append(Materials(str(key), int(totalMaterials), ' Raw Materials', '100%', str(round(percentWaste, 3)) + '%'))

                for key in extraMaterials.keys():
                    tempManufacterRows.append(Materials(str(key), int(extraMaterials[key]), 'Extra Materials', '', ''))

                for key in skills.keys():
                    tempManufacterRows.append(Materials(str(key), int(skills[key]), 'Skills', '', ''))

            except lite.Error as err:
                error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
                onError(error)
            finally:
                if con:
                    con.close()

            if tempMaterialLevelRows != []:
                materialLevelRows = tempMaterialLevelRows[:]
            self.mlAnalysisList.SetObjects(materialLevelRows)

            if tempManufacterRows != []:
                manufactureRows = tempManufacterRows[:]
            self.manufactureList.SetObjects(manufactureRows)

            # Production time calculations
            baseProductionTime = float(bpoList[itemID][4])
            productivityModifier = float(bpoList[itemID][5])
            industrySkill = self.manufactIndSpinCtrl.GetValue()  # The industrial skill of the pilot.
            productionLevel = float(self.manufactPLSpinCtrl.GetValue())  # The PE/PL of the researched blueprint.

            implantModifier = 1  # TODO: Will have to be pulled from the API see skillCheck() in api.py

            # assemblyLineTypeID, assemblyLineTypeName, baseTimeMultiplier, baseMaterialMultiplier
            installTimeModifier = installList[currentInstall][2]

            produtionTimeModifier = ((1 - (0.04 * industrySkill)) * implantModifier * installTimeModifier)

            if productionEfficiency >= 0:
                productionTime = (baseProductionTime * (1 - (productivityModifier / baseProductionTime) * (productionLevel / (1 + productionLevel))) * produtionTimeModifier) * manufactureQty
            else:
                productionTime = (baseProductionTime * (1 - (productivityModifier / baseProductionTime) * (productionLevel - 1)) * produtionTimeModifier) * manufactureQty

            #print(productionTime)
            self.outputTimeTextCtrl.SetValue(str(datetime.timedelta(seconds=round(productionTime, 0))))

            self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Perfect ME: ' + str(maxME))  # I'll find a better home for this number soon.

    def onConfig(self, event):
        # Open the config frame for user.
        dlg = PreferencesDialog(None)
        dlg.ShowModal()  # Show it
        dlg.Destroy()  # finally destroy it when finished.

    def onAbout(self, event):
        description = """A tool designed initially for our corporate industrialists to
enable them to see their EvE Online Science and Industry job queues while out of game.

Later expanded upon to cover POS status and manufacturing job calculations.

If you like my work please consider an ISK donation to Elusive One.

All EVE-Online related materials are property of CCP hf."""

        licence = """NESI is released under GNU GPLv3:

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""

        info = wx.AboutDialogInfo()

        info.SetIcon(wx.Icon('images/nesi.png', wx.BITMAP_TYPE_PNG))
        info.SetName('Nova Echo Science & Industry')
        info.SetVersion('1.2.0-alpha2')
        info.SetDescription(description)
        #info.SetCopyright('(C) 2013 Tim Cumming')
        info.SetWebSite('https://github.com/EluOne/Nesi')
        info.SetLicence(licence)
        info.AddDeveloper('Tim Cumming aka Elusive One')
        #info.AddDocWriter('')
        #info.AddArtist('')
        #info.AddTranslator('')

        wx.AboutBox(info)

    def onExit(self, event):
        dlg = wx.MessageDialog(self, 'Are you sure to quit Nesi?', 'Please Confirm',
                                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.Close(True)

# end of class MainWindow


class MyApp(wx.App):
    def OnInit(self):
        frame = MainWindow(None, -1, '')
        self.SetTopWindow(frame)
        frame.Center()
        frame.Show()
        return 1

# end of class MyApp

if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()
