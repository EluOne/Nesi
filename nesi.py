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

from xml.dom.minidom import parseString
from ObjectListView import ObjectListView, ColumnDefn

import urllib
import urllib2
import httplib
import os.path
import pickle
import wx
import datetime
import time


# Establish some current time data for calculations later.
serverTime = datetime.datetime.utcnow().replace(microsecond=0) # Server Time is UTC so we will use that for now generated locally.
localTime = datetime.datetime.now().replace(microsecond=0) # Client Time reported locally.
serverStatus = ['', '0', serverTime] # A global variable to store the returned status.
jobsCachedUntil = serverTime # A global variable to store the cacheUtil time.
rows = []


class Job(object):
    def __init__(self, jobID, completedStatus, activityID, installedItemTypeID,
                 installedItemProductivityLevel, installedItemMaterialLevel, installerID,
                 runs, outputTypeID, installTime, endProductionTime):
        self.jobID = jobID
        self.completedStatus = completedStatus
        self.activityID = activityID
        self.installedItemTypeID = installedItemTypeID
        self.installedItemProductivityLevel = installedItemProductivityLevel
        self.installedItemMaterialLevel = installedItemMaterialLevel
        self.installerID = installerID
        self.runs = runs
        self.outputTypeID = outputTypeID
        self.installTime = datetime.datetime(*(time.strptime(installTime, "%Y-%m-%d %H:%M:%S")[0:6]))
        self.endProductionTime = datetime.datetime(*(time.strptime(endProductionTime, "%Y-%m-%d %H:%M:%S")[0:6]))
        if self.endProductionTime > serverTime:
            self.timeRemaining = self.endProductionTime - serverTime
            self.state = 'In Progress'
        else:
            self.timeRemaining = self.endProductionTime - serverTime
            self.state = 'Ready'

# S&I window shows: state, activity, type, location, jumps, installer, owner, install date, end date

#columns="jobID,assemblyLineID,containerID,installedItemID,installedItemLocationID,installedItemQuantity,installedItemProductivityLevel,
#installedItemMaterialLevel,installedItemLicensedProductionRunsRemaining,outputLocationID,installerID,runs,licensedProductionRuns,
#installedInSolarSystemID,containerLocationID,materialMultiplier,charMaterialMultiplier,timeMultiplier,charTimeMultiplier,
#installedItemTypeID,outputTypeID,containerTypeID,installedItemCopy,completed,completedSuccessfully,installedItemFlag,
#outputFlag,activityID,completedStatus,installTime,beginProductionTime,endProductionTime,pauseProductionTime"


def onError(error):
    dlg = wx.MessageDialog(self, 'An error has occured: ' + error, '', wx.OK | wx.ICON_ERROR)
    dlg.ShowModal() # Show it
    dlg.Destroy() # finally destroy it when finished.


def getServerStatus(args):
    if serverTime >= args[2]:
        status = []
        #Download the Account Industry Data from API server
        apiURL = 'https://api.eveonline.com/server/ServerStatus.xml.aspx/'

        try: # Try to connect to the API server
            target = urllib2.urlopen(apiURL) #download the file
            downloadedData = target.read() #convert to string
            target.close() #close file because we don't need it anymore

            XMLData = parseString(downloadedData)

            result = XMLData.getElementsByTagName('result')
            serveropen = result[0].getElementsByTagName("serverOpen")
            onlineplayers = result[0].getElementsByTagName("onlinePlayers")
            cacheuntil = XMLData.getElementsByTagName('cachedUntil')

            if (serveropen[0].firstChild.nodeValue):
                status.append("Tranquility Online")
            else:
                status.append("Server down.")

            status.append(onlineplayers[0].firstChild.nodeValue)
            cacheExpire = datetime.datetime(*(time.strptime((cacheuntil[0].firstChild.nodeValue), "%Y-%m-%d %H:%M:%S")[0:6]))
            status.append(cacheExpire)
        except urllib2.HTTPError, err:
            status.append('HTTP Error: ' + str(err.code)) # Server Status String
            status.append('0') # Players Online data 0 as no data
            status.append(serverTime) # Cache Until now as no data
            onError(status[0])
        except urllib2.URLError, err:
            status.append('Error Connecting to Tranquility: ' + str(err.reason)) # Server Status String
            status.append('0') # Players Online data 0 as no data
            status.append(serverTime) # Cache Until now as no data
            onError(status[0])
        except httplib.HTTPException, err:
            status.append('HTTP Exception') # Server Status String
            status.append('0') # Players Online data 0 as no data
            status.append(serverTime) # Cache Until now as no data
            onError(status[0])
        except Exception:
            import traceback
            status.append('Generic Exception: ' + traceback.format_exc()) # Server Status String
            status.append('0') # Players Online data 0 as no data
            status.append(serverTime) # Cache Until now as no data
            onError(status[0])

        return status
    else:
        print 'Not Contacting Server For Status'
        return args

def iid2name(ids): # Takes a list of typeIDs to query the api server.
    itemNames = {}

    if (os.path.isfile("items.cache")):
        itemsfile = open("items.cache",'r')
        itemNames = pickle.load(itemsfile)
        itemsfile.close()

    numItems = range(len(ids))
    print ids # Console debug

    for x in numItems:
        if ids[x] in itemNames:
            ids[x] = 'deleted'

    for y in ids[:]:
        if y == 'deleted':
            ids.remove(y)

    print ids # Console debug

    if ids != []: # We still have some character ids we don't know
        idList = ','.join(map(str, ids))

        #Download the TypeName Data from API server
        apiURL = 'https://api.eveonline.com/eve/TypeName.xml.aspx?ids=%s' % (idList)
        print apiURL # Console debug

        target = urllib2.urlopen(apiURL) #download the file
        downloadedData = target.read() #convert to string
        target.close() #close file because we don't need it anymore

        XMLData = parseString(downloadedData)
        dataNodes = XMLData.getElementsByTagName("row")

        for row in dataNodes:
            itemNames.update({int(row.getAttribute('typeID')) : str(row.getAttribute('typeName'))})

        # Save the data we have so we don't have to fetch it
        settingsfile = open("items.cache",'w')
        pickle.dump(itemNames,settingsfile)
        settingsfile.close()

# Fail returns id as item
#    numItems = range(len(ids))
#    for y in numItems:
#        itemNames.update({ids[y] : ids[y]})

    return itemNames


def cid2name(ids): # Takes a list of characterIDs to query the api server.
    pilotNames = {}

    if (os.path.isfile("character.cache")):
        charactersfile = open("character.cache",'r')
        pilotNames = pickle.load(charactersfile)
        charactersfile.close()

    numItems = range(len(ids))
    print ids # Console debug

    for x in numItems:
        if ids[x] in pilotNames:
            ids[x] = 'deleted'

    for y in ids[:]:
        if y == 'deleted':
            ids.remove(y)

    print ids # Console debug

    if ids != []: # We still have some character ids we don't know
        idList = ','.join(map(str, ids))

        #Download the Character Names from API server
        apiURL = 'https://api.eveonline.com/eve/CharacterName.xml.aspx?ids=%s' % (idList)
        print apiURL # Console debug

        target = urllib2.urlopen(apiURL) #download the file
        downloadedData = target.read() #convert to string
        target.close() #close file because we don't need it anymore

        XMLData = parseString(downloadedData)
        dataNodes = XMLData.getElementsByTagName("row")

        for row in dataNodes:
            pilotNames.update({int(row.getAttribute('characterID')) : str(row.getAttribute('name'))})

        # Save the data we have so we don't have to fetch it
        settingsfile = open("character.cache",'w')
        pickle.dump(pilotNames,settingsfile)
        settingsfile.close()

# Fail returns id as name
#    numItems = range(len(ids))
#    for y in numItems:
#        pilotNames.update({ids[y] : ids[y]})

    return pilotNames


def rowFormatter(listItem, row):
    if row.timeRemaining < datetime.timedelta(0):
        listItem.SetTextColour(wx.GREEN)

def activityConv(act):
    activities = {1 : 'Manufacturing', 2 : '2', 3 : 'Time Efficiency Research', 4 : 'Material Research', 5 : 'Copy', 6 : '6', 7 : '7', 8 : 'Invention'} # POS activities list.
    if act in activities:
        return activities[act]


class PreferencesDialog(wx.Dialog):
    def __init__(self):
        """A simple user preferences window"""
        wx.Dialog.__init__(self, None, wx.ID_ANY, 'Preferences', size=(400,150))

        self.cfg = wx.Config('nesi')
        if self.cfg.Exists('keyID'):
            keyID, vCode, characterID = self.cfg.Read('keyID'), self.cfg.Read('vCode'), self.cfg.Read('characterID')
        else:
            (keyID, vCode, characterID) = ('', '', '')

        prefsSizer = wx.GridBagSizer(5, 5)
        btnSizer = wx.StdDialogButtonSizer()
        mainSizer = wx.BoxSizer(wx.VERTICAL)

        prefsSizer.Add(wx.StaticText(self, -1, 'keyID: '), (0, 0), wx.DefaultSpan, wx.EXPAND)
        prefsSizer.Add(wx.StaticText(self, -1, 'vCode: '), (1, 0), wx.DefaultSpan, wx.EXPAND)
        prefsSizer.Add(wx.StaticText(self, -1, 'characterID: '), (2, 0), wx.DefaultSpan, wx.EXPAND)

        self.tc1 = wx.TextCtrl(self, -1, value=keyID, size=(300, -1))
        self.tc2 = wx.TextCtrl(self, -1, value=vCode, size=(300, -1))
        self.tc3 = wx.TextCtrl(self, -1, value=characterID, size=(300, -1))

        prefsSizer.Add(self.tc1, (0, 1), wx.DefaultSpan, wx.EXPAND)
        prefsSizer.Add(self.tc2, (1, 1), wx.DefaultSpan, wx.EXPAND)
        prefsSizer.Add(self.tc3, (2, 1), wx.DefaultSpan, wx.EXPAND)

        saveBtn = wx.Button(self, wx.ID_OK, label="Save")
        saveBtn.Bind(wx.EVT_BUTTON, self.onSave)
        btnSizer.AddButton(saveBtn)

        cancelBtn = wx.Button(self, wx.ID_CANCEL)
        btnSizer.AddButton(cancelBtn)
        btnSizer.Realize()

        mainSizer.Add(prefsSizer, 0, wx.ALL | wx.ALIGN_CENTER)
        mainSizer.Add(btnSizer, 0, wx.ALL | wx.ALIGN_CENTER)
        self.SetSizer(mainSizer)

    def onSave(self, event):
        self.cfg.Write("keyID", self.tc1.GetValue())
        self.cfg.Write("vCode", self.tc2.GetValue())
        self.cfg.Write("characterID", self.tc3.GetValue())
        self.EndModal(0)


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        """Our MainWindow layout"""
        wx.Frame.__init__(self, parent, title=title, size=(1024, 600))

        panel = wx.Panel(self, -1)
        panel.SetBackgroundColour(wx.NullColour) # Use system default colour

        self.statusbar = self.CreateStatusBar() # A Statusbar in the bottom of the window
        self.statusbar.SetStatusText('Welcome to Nesi')

        # Job Details box TODO
        self.detailBox = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(-1,-1))
#        self.detailBox.SetFont(wx.Font(9, wx.FONTFAMILY_DEFAULT,
#                                                   wx.FONTSTYLE_NORMAL,
#                                                   wx.FONTWEIGHT_NORMAL,
#                                                   False))

        # Setting up the menu.
        filemenu= wx.Menu()
#        menuRefresh= filemenu.Append(wx.ID_ANY, "&Refresh", " Refresh the list")
        menuConfig= filemenu.Append(wx.ID_ANY, "&Configure", " Configure Nesi") # TODO
        menuAbout= filemenu.Append(wx.ID_ABOUT, "&About", " Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT, "E&xit", " Terminate the program")

        # Creating the menu bar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "file menu" to the MenuBar.
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        toolbar = wx.ToolBar(self, -1)
#        self.tc = wx.TextCtrl(toolbar, -1, size=(100, -1))
        btn = wx.Button(toolbar, 1, 'Refresh', size=(64, 28))

#        toolbar.AddControl(self.tc)
#        toolbar.AddSeparator()
        toolbar.AddControl(btn)
        toolbar.Realize()
        self.SetToolBar(toolbar)

        self.myOlv = ObjectListView(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER)
        self.myOlv.rowFormatter = rowFormatter

        # Menu events.
        self.Bind(wx.EVT_MENU, self.onExit, menuExit)
        self.Bind(wx.EVT_MENU, self.onAbout, menuAbout)
        self.Bind(wx.EVT_BUTTON, self.onGetData, id=1)
        self.Bind(wx.EVT_MENU, self.onConfig, menuConfig) # TODO
        self.myOlv.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onItemSelected)

        self.myOlv.SetColumns([
            ColumnDefn("State", "left", 100, "state"),
            ColumnDefn("Activity", "left", 180, "activityID", stringConverter=activityConv),
            ColumnDefn("Type", "center", 300, "installedItemTypeID"),
            ColumnDefn("Installer", "center", 120, "installerID"),
            ColumnDefn("Install Date", "left", 145, "installTime"),
            ColumnDefn("End Date", "left", 145, "endProductionTime")
#            ColumnDefn("TTC", "left", 145, "timeRemaining")
        ])

 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.myOlv, 2, wx.ALL|wx.EXPAND, 4)
        sizer.Add(self.detailBox, 1, wx.EXPAND | wx.ALL, 1) #TODO
        self.SetSizer(sizer)


    def onGetData(self, event):
        """Event handler to fetch data from server"""
        global rows
        global serverStatus
        global jobsCachedUntil
        global serverTime

        serverTime = datetime.datetime.utcnow().replace(microsecond=0) # Update Server Time.

        self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Connecting to Tranquility...')
        serverStatus = getServerStatus(serverStatus) # Try the API server for current server status.

        if serverTime >= jobsCachedUntil:
            # Get user settings.
            cfg = wx.Config('nesi')
            if cfg.Exists('keyID'):
                keyID, vCode, characterID = cfg.Read('keyID'), cfg.Read('vCode'), cfg.Read('characterID')
            else:
                (keyID, vCode, characterID) = ('', '', '')

            #Download the Account Industry Data
            apiURL = 'http://api.eveonline.com/corp/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s' % (keyID, vCode, urllib.quote(characterID))
            print apiURL # Console debug

            target = urllib2.urlopen(apiURL) #download the file
            downloadedData = target.read() #convert to string
            target.close() #close file because we don't need it anymore:

            XMLData = parseString(downloadedData)
            dataNodes = XMLData.getElementsByTagName("row")

            cacheuntil = XMLData.getElementsByTagName('cachedUntil')
            cacheExpire = datetime.datetime(*(time.strptime((cacheuntil[0].firstChild.nodeValue), "%Y-%m-%d %H:%M:%S")[0:6]))
            jobsCachedUntil = cacheExpire

            rows = []
            itemIDs = []
            installerIDs = []
            for row in dataNodes:
                if row.getAttribute('completed') == '0': # Ignore Delivered Jobs
                    if int(row.getAttribute('installedItemTypeID')) not in itemIDs:
                        itemIDs.append(int(row.getAttribute('installedItemTypeID')))
                    if int(row.getAttribute('outputTypeID')) not in itemIDs:
                        itemIDs.append(int(row.getAttribute('outputTypeID')))
                    if int(row.getAttribute('installerID')) not in installerIDs:
                        installerIDs.append(int(row.getAttribute('installerID')))

            itemNames = iid2name(itemIDs)
            pilotNames = cid2name(installerIDs)

            for row in dataNodes:
                if row.getAttribute('completed') == '0': # Ignore Delivered Jobs
                    rows.append(Job(row.getAttribute('jobID'),
                                    row.getAttribute('completedStatus'),
                                    int(row.getAttribute('activityID')), #Leave as int for ease in later clauses
                                    itemNames[int(row.getAttribute('installedItemTypeID'))],
                                    int(row.getAttribute('installedItemProductivityLevel')),
                                    int(row.getAttribute('installedItemMaterialLevel')),
                                    pilotNames[int(row.getAttribute('installerID'))],
                                    int(row.getAttribute('runs')),
                                    itemNames[int(row.getAttribute('outputTypeID'))],
                                    row.getAttribute('installTime'),
                                    row.getAttribute('endProductionTime')))

#columns=",assemblyLineID,containerID,,installedItemLocationID,installedItemQuantity,,
#,installedItemLicensedProductionRunsRemaining,outputLocationID,,,licensedProductionRuns,
#installedInSolarSystemID,containerLocationID,materialMultiplier,charMaterialMultiplier,timeMultiplier,charTimeMultiplier,
#,,containerTypeID,installedItemCopy,completed,completedSuccessfully,installedItemFlag,
#outputFlag,,completedStatus,,beginProductionTime,,pauseProductionTime"
            self.myOlv.SetObjects(rows)
        else:
            numItems = range(len(rows))
            for r in numItems:
                if rows[r].endProductionTime > serverTime:
                    rows[r].timeRemaining = rows[r].endProductionTime - serverTime
                    rows[r].state = 'In Progress'
                else:
                    rows[r].timeRemaining = rows[r].endProductionTime - serverTime
                    rows[r].state = 'Ready'
            self.myOlv.RefreshObjects(rows)
            print 'Not Contacting Server, Cache Not Expired'

        self.statusbar.SetStatusText(serverStatus[0] + ' - ' + serverStatus[1]
                                     + ' Players Online - EvE Time: ' + str(serverTime)
                                     + ' - API Cached Until: ' + str(jobsCachedUntil))


    def onItemSelected(self, event):
        """Handle showing details for item select from list"""
        currentItem = self.myOlv[event.GetIndex()]

        details = ''
        if currentItem.timeRemaining < datetime.timedelta(0):
            details = 'Ready'
        else:
            details = str(currentItem.timeRemaining)

#    activities = {1 : 'Manufacturing', 2 : '2', 3 : 'Time Efficiency Research', 4 : 'Material Research', 5 : 'Copy', 6 : '6', 7 : '7', 8 : 'Invention'} # POS activities list.
        if currentItem.activityID == 1: # Manufacturing
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        elif currentItem.activityID == 2:
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        elif currentItem.activityID == 3: # Time Efficiency Research
            details = ('TTC: %s\nInstall PE: %s\nOutput PE %s\n1 unit of %s\n' % (details, currentItem.installedItemProductivityLevel, (currentItem.installedItemProductivityLevel + currentItem.runs), currentItem.outputTypeID))
        elif currentItem.activityID == 4: # Material Research
            details = ('TTC: %s\nInstall ME: %s\nOutput ME %s\n1 unit of %s\n' % (details, currentItem.installedItemMaterialLevel, (currentItem.installedItemMaterialLevel + currentItem.runs), currentItem.outputTypeID))
        if currentItem.activityID == 5: # Manufacturing
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        if currentItem.activityID == 6: # Manufacturing
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        if currentItem.activityID == 7: # Manufacturing
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        if currentItem.activityID == 8: # Manufacturing
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))

        self.detailBox.SetValue(details)


    def onConfig(self, event):
        # Open the config frame for user.
        dlg = PreferencesDialog()
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.


    def onAbout(self, event):
        description = """A tool to let you see your EvE Online science and industry job queues while out of game."""

        licence = """This program is free software: you can redistribute it and/or modify
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

        #info.SetIcon(wx.Icon('hunter.png', wx.BITMAP_TYPE_PNG))
        info.SetName('Nova Echo Science & Industry')
        info.SetVersion('0.0.1')
        info.SetDescription(description)
        info.SetCopyright('(C) 2013 Tim Cumming')
        info.SetWebSite('https://github.com/EluOne/Nesi')
        info.SetLicence(licence)
        #info.AddDeveloper('Tim Cumming')
        #info.AddDocWriter('Tim Cumming')
        #info.AddArtist('Tim Cumming')
        #info.AddTranslator('Tim Cumming')

        wx.AboutBox(info)


    def onExit(self, event):
        dlg = wx.MessageDialog(self, 'Are you sure to quit Nesi?', 'Please Confirm', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.Close(True)



if __name__ == '__main__':
    app = wx.App(0)
    frame = MainWindow(None, "Nesi")
    app.SetTopWindow(frame)
    frame.Show()
    app.MainLoop()
