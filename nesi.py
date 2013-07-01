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

import urllib2
import httplib
import os.path
import pickle
import wx
import datetime
import time


# Establish some current time data for calculations later.
# Server Time is UTC so we will use that for now generated locally.
serverTime = datetime.datetime.utcnow().replace(microsecond=0)
# Client Time reported locally.
localTime = datetime.datetime.now().replace(microsecond=0)
# A global variable to store the returned status.
serverStatus = ['', '0', serverTime]
# A global variable to store the cacheUtil time.
jobsCachedUntil = serverTime
jobRows = []
# This is where we are storing our API keys for now.
pilotRows = []


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
        self.installTime = datetime.datetime(*(time.strptime(installTime, '%Y-%m-%d %H:%M:%S')[0:6]))
        self.endProductionTime = datetime.datetime(*(time.strptime(endProductionTime, '%Y-%m-%d %H:%M:%S')[0:6]))
        if self.endProductionTime > serverTime:
            self.timeRemaining = self.endProductionTime - serverTime
            self.state = 'In Progress'
        else:
            self.timeRemaining = self.endProductionTime - serverTime
            self.state = 'Ready'

# S&I window shows: state, activity, type, location, jumps, installer, owner, install date, end date
# This is what the API returns:
#columns="jobID,assemblyLineID,containerID,installedItemID,installedItemLocationID,installedItemQuantity
#installedItemProductivityLevel,installedItemMaterialLevel,installedItemLicensedProductionRunsRemaining,
#outputLocationID,installerID,runs,licensedProductionRuns,installedInSolarSystemID,containerLocationID,
#materialMultiplier,charMaterialMultiplier,timeMultiplier,charTimeMultiplier,installedItemTypeID,outputTypeID,
#containerTypeID,installedItemCopy,completed,completedSuccessfully,installedItemFlag,outputFlag,activityID,
#completedStatus,installTime,beginProductionTime,endProductionTime,pauseProductionTime"


class Character(object):
    def __init__(self, keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, isActive):
        self.keyID = keyID
        self.vCode = vCode
        self.characterID = characterID
        self.characterName = characterName
        self.corporationID = corporationID
        self.corporationName = corporationName
        self.keyType = keyType
        self.keyExpires = datetime.datetime(*(time.strptime(keyExpires, '%Y-%m-%d %H:%M:%S')[0:6]))
        self.isActive = isActive


# Lets try to load up our API keys from the config file.
# This requires the above classes to work.
if (os.path.isfile('nesi.ini')):
    iniFile = open('nesi.ini', 'r')
    pilotRows = pickle.load(iniFile)
    iniFile.close()


def onError(error):
    dlg = wx.MessageDialog(None, 'An error has occured:\n' + error, '', wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()  # Show it
    dlg.Destroy()  # finally destroy it when finished.


def apiCheck(keyID, vCode):
    pilots = []
    baseUrl = 'https://api.eveonline.com/account/APIKeyInfo.xml.aspx?keyID=%s&vCode=%s'
    apiURL = baseUrl % (keyID, vCode)
    print(apiURL)  # Console debug

    try:  # Try to connect to the API server
        target = urllib2.urlopen(apiURL)  # download the file
        downloadedData = target.read()  # convert to string
        target.close()  # close file because we don't need it anymore:

        XMLData = parseString(downloadedData)
        key = XMLData.getElementsByTagName('key')
        keyInfo = {'accessMask': key[0].getAttribute('accessMask'),
                   'type': key[0].getAttribute('type'),
                   'expires': key[0].getAttribute('expires')}

        dataNodes = XMLData.getElementsByTagName('row')

        for row in dataNodes:
            pilots.append([keyID, vCode,
                            row.getAttribute('characterID'),
                            row.getAttribute('characterName'),
                            row.getAttribute('corporationID'),
                            row.getAttribute('corporationName'),
                            keyInfo['type'], keyInfo['expires']
                            ])

    except urllib2.HTTPError as err:
        error = ('HTTP Error: ' + str(err.code))  # Error String
        onError(error)
    except urllib2.URLError as err:
        error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
        onError(error)
    except httplib.HTTPException as err:
        error = ('HTTP Exception')  # Error String
        onError(error)
    except Exception:
        import traceback
        error = ('Generic Exception: ' + traceback.format_exc())  # Error String
        onError(error)

    return pilots


def getServerStatus(args):
    if serverTime >= args[2]:
        status = []
        #Download the Account Industry Data from API server
        apiURL = 'https://api.eveonline.com/server/ServerStatus.xml.aspx/'

        try:  # Try to connect to the API server
            target = urllib2.urlopen(apiURL)  # download the file
            downloadedData = target.read()  # convert to string
            target.close()  # close file because we don't need it anymore

            XMLData = parseString(downloadedData)

            result = XMLData.getElementsByTagName('result')
            serveropen = result[0].getElementsByTagName('serverOpen')
            onlineplayers = result[0].getElementsByTagName('onlinePlayers')
            cacheuntil = XMLData.getElementsByTagName('cachedUntil')

            if (serveropen[0].firstChild.nodeValue):
                status.append('Tranquility Online')
            else:
                status.append('Server down.')

            status.append(onlineplayers[0].firstChild.nodeValue)
            cacheExpire = datetime.datetime(*(time.strptime((cacheuntil[0].firstChild.nodeValue), '%Y-%m-%d %H:%M:%S')[0:6]))
            status.append(cacheExpire)
        except urllib2.HTTPError as err:
            # HTTP Error String, Players Online data 0 as no data, Cache Until now as no data
            status = [('HTTP Error: ' + str(err.code)), '0', serverTime]
            onError(status[0])
        except urllib2.URLError as err:
            # Error Connection String, Players Online data 0 as no data, Cache Until now as no data
            status = [('Error Connecting to Tranquility: ' + str(err.reason)), '0', serverTime]
            onError(status[0])
        except httplib.HTTPException as err:
            # HTTP Exception String, Players Online data 0 as no data, Cache Until now as no data
            status = [('HTTP Exception'), '0', serverTime]
            onError(status[0])
        except Exception:
            import traceback
            # Exception String, Players Online data 0 as no data, Cache Until now as no data
            status = [('Generic Exception: ' + traceback.format_exc()), '0', serverTime]
            onError(status[0])

        return status
    else:
        print('Not Contacting Server For Status')
        return args


def id2name(idType, ids):  # Takes a list of typeIDs to query the api server.
    typeNames = {}
    if idType == 'item':
        cacheFile = 'items.cache'
        baseUrl = 'https://api.eveonline.com/eve/TypeName.xml.aspx?ids=%s'
        key = 'typeID'
        value = 'typeName'
    elif idType == 'character':
        cacheFile = 'character.cache'
        baseUrl = 'https://api.eveonline.com/eve/CharacterName.xml.aspx?ids=%s'
        key = 'characterID'
        value = 'name'

    if (os.path.isfile(cacheFile)):
        typeFile = open(cacheFile, 'r')
        typeNames = pickle.load(typeFile)
        typeFile.close()

    numItems = list(range(len(ids)))
    print(ids)  # Console debug

    for x in numItems:
        if ids[x] in typeNames:
            ids[x] = 'deleted'

    for y in ids[:]:
        if y == 'deleted':
            ids.remove(y)

    print(ids)  # Console debug

    if ids != []:  # We still have some ids we don't know
        idList = ','.join(map(str, ids))
        numItems = range(len(ids)) # Used later if we have a protocol fail.

        #Download the TypeName Data from API server
        apiURL = baseUrl % (idList)
        print(apiURL)  # Console debug

        try:  # Try to connect to the API server
            target = urllib2.urlopen(apiURL)  # download the file
            downloadedData = target.read()  # convert to string
            target.close()  # close file because we don't need it anymore

            XMLData = parseString(downloadedData)
            dataNodes = XMLData.getElementsByTagName('row')

            for row in dataNodes:
                typeNames.update({int(row.getAttribute(key)): str(row.getAttribute(value))})

            # Save the data we have so we don't have to fetch it
            typeFile = open(cacheFile, 'w')
            pickle.dump(typeNames, typeFile)
            typeFile.close()
        except urllib2.HTTPError as err:
            error = ('HTTP Error: ' + str(err.code))  # Error String
            for y in numItems:
                typeNames.update({ids[y] : ids[y]})
            onError('self', error)
        except urllib2.URLError as err:
            error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
            for y in numItems:
                typeNames.update({ids[y] : ids[y]})
            onError('self', error)
        except httplib.HTTPException as err:
            error = ('HTTP Exception')  # Error String
            for y in numItems:
                typeNames.update({ids[y] : ids[y]})
            onError('self', error)
        except Exception:
            import traceback
            error = ('Generic Exception: ' + traceback.format_exc())  # Error String
            for y in numItems:
                typeNames.update({ids[y] : ids[y]})
            onError('self', error)

    return typeNames


def rowFormatter(listItem, row):  # Formatter for ObjectListView, will turn completed jobs green.
    if row.timeRemaining < datetime.timedelta(0):
        listItem.SetTextColour(wx.GREEN)


def apiRowFormatter(listItem, row):  # Formatter for ObjectListView, will turn completed jobs green.
    if row.keyExpires < serverTime:
        listItem.SetTextColour(wx.RED)


def activityConv(act):
    activities = {1: 'Manufacturing', 2: '2', 3: 'Time Efficiency Research', 4: 'Material Research',
                    5: 'Copy', 6: '6', 7: '7', 8: 'Invention'}  # POS activities list.
    if act in activities:
        return activities[act]
    else:
        return act


class PreferencesDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: PreferenceDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.label_4 = wx.StaticText(self, -1, "Key ID:")
        self.keyIDTextCtrl = wx.TextCtrl(self, -1, "")
        self.label_5 = wx.StaticText(self, -1, "vCode:")
        self.vCodeTextCtrl = wx.TextCtrl(self, -1, "")
        self.addBtn = wx.Button(self, -1, "+")
        self.charList = ObjectListView(self, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL)
        self.saveBtn = wx.Button(self, -1, "Save")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.saveBtn.Bind(wx.EVT_BUTTON, self.onSave)
        self.addBtn.Bind(wx.EVT_BUTTON, self.onAdd)

    def __set_properties(self):
        global pilotRows

        # begin wxGlade: PreferenceDialog.__set_properties
        self.SetTitle("Preferences")
        self.SetSize((750, 300))
        self.keyIDTextCtrl.SetMinSize((120, 21))
        self.vCodeTextCtrl.SetMinSize((300, 21))
        self.addBtn.SetMinSize((27, 27))
        self.saveBtn.SetDefault()
        # end wxGlade
        self.charList.SetEmptyListMsg('Fill in boxes above and\n click + to add pilots')

        self.charList.rowFormatter = apiRowFormatter
        self.charList.SetColumns([
            ColumnDefn('keyID', 'left', 80, 'keyID'),
            ColumnDefn('Key Type', 'left', 90, 'keyType'),
            ColumnDefn('Character Name', 'left', 200, 'characterName'),
            ColumnDefn('Corporation', 'left', 225, 'corporationName'),
            ColumnDefn('Expires', 'left', 150, 'keyExpires')
        ])

        self.charList.SetObjects(pilotRows)

    def __do_layout(self):
        # begin wxGlade: PreferenceDialog.__do_layout
        sizer_3 = wx.BoxSizer(wx.VERTICAL)
        sizer_4 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_5.Add(self.label_4, 0, wx.ALIGN_CENTER_VERTICAL|wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.keyIDTextCtrl, 0, wx.ALIGN_CENTER_VERTICAL|wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.label_5, 0, wx.ALIGN_CENTER_VERTICAL|wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.vCodeTextCtrl, 0, wx.ALIGN_CENTER_VERTICAL|wx.ADJUST_MINSIZE, 0)
        sizer_5.Add(self.addBtn, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_CENTER_VERTICAL|wx.ADJUST_MINSIZE, 0)
        sizer_3.Add(sizer_5, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 0)
        sizer_3.Add(self.charList, 3, wx.EXPAND, 0)
        sizer_4.Add(self.cancelBtn, 0, wx.ADJUST_MINSIZE, 0)
        sizer_4.Add(self.saveBtn, 0, wx.ADJUST_MINSIZE, 0)
        sizer_3.Add(sizer_4, 1, wx.ALL|wx.ALIGN_CENTER_HORIZONTAL, 0)
        self.SetSizer(sizer_3)
        self.Layout()
        # end wxGlade

    def onAdd(self, event):
        global pilotRows

        numPilotRows = list(range(len(pilotRows)))
        keyID, vCode = (self.keyIDTextCtrl.GetValue(), self.vCodeTextCtrl.GetValue())

        if (keyID != '') or (vCode != ''):  # Check neither field was left blank.
            for x in numPilotRows:
                if (self.keyIDTextCtrl.GetValue() == pilotRows[x].keyID) and (self.vCodeTextCtrl.GetValue() == pilotRows[x].vCode):
                    keyID, vCode = ('', '')  # We already have this key so null it so next check fails

            if (keyID != '') and (vCode != ''):
                pilots = apiCheck(keyID, vCode)

                print(pilots)  # Console debug

                if pilots != []:
                    for row in pilots:
                        # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, isActive
                        pilotRows.append(Character(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], 0))

        self.charList.SetObjects(pilotRows)

    def onSave(self, event):
        if pilotRows != []:
            iniFile = open('nesi.ini', 'w')
            pickle.dump(pilotRows, iniFile)
            iniFile.close()
        self.EndModal(0)

# end of class PreferencesDialog


class MainWindow(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: MainWindow.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.bitmap_1 = wx.StaticBitmap(self, -1, wx.Bitmap('images/nesi.png', wx.BITMAP_TYPE_PNG))
        self.label_1 = wx.StaticText(self, -1, 'Science and Industry')
        self.myOlv = ObjectListView(self, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.detailBox = wx.TextCtrl(self, -1, '', style=wx.TE_MULTILINE)
        self.btn = wx.Button(self, -1, 'Get Jobs')

        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        self.fileMenu = wx.Menu()
        self.menuAbout = wx.MenuItem(self.fileMenu, wx.NewId(), '&About', '', wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuAbout)
        self.menuConfig = wx.MenuItem(self.fileMenu, wx.NewId(), '&Configure', '', wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuConfig)
        self.menuExit = wx.MenuItem(self.fileMenu, wx.NewId(), 'E&xit', '', wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuExit)
        self.frame_menubar.Append(self.fileMenu, 'File')
        self.SetMenuBar(self.frame_menubar)
        # Menu Bar end
        self.statusbar = self.CreateStatusBar(1, 0)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.onGetData, self.btn)
        self.Bind(wx.EVT_MENU, self.onAbout, self.menuAbout)
        self.Bind(wx.EVT_MENU, self.onConfig, self.menuConfig)
        self.Bind(wx.EVT_MENU, self.onExit, self.menuExit)
        # end wxGlade

        self.myOlv.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onItemSelected)

    def __set_properties(self):
        # begin wxGlade: MainWindow.__set_properties
        self.SetTitle('Nesi')
        self.SetSize((1024, 600))
        self.bitmap_1.SetMinSize((64, 64))
        self.label_1.SetFont(wx.Font(18, wx.DEFAULT, wx.NORMAL, wx.NORMAL, 0, ""))
        # end wxGlade

        self.statusbar.SetStatusText('Welcome to Nesi - Idle')

        # In game: Click "Get Jobs" to fetch jobs with current filters
        self.myOlv.SetEmptyListMsg('Click \"Get Jobs\" to fetch jobs')

        self.myOlv.rowFormatter = rowFormatter
        self.myOlv.SetColumns([
            ColumnDefn('State', 'left', 100, 'state'),
            ColumnDefn('Activity', 'left', 180, 'activityID', stringConverter=activityConv),
            ColumnDefn('Type', 'center', 300, 'installedItemTypeID'),
            ColumnDefn('Installer', 'center', 120, 'installerID'),
            ColumnDefn('Install Date', 'left', 145, 'installTime'),
            ColumnDefn('End Date', 'left', 145, 'endProductionTime')
        ])

    def __do_layout(self):
        # begin wxGlade: MainWindow.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.bitmap_1, 0, wx.FIXED_MINSIZE, 0)
        sizer_2.Add(self.label_1, 0, wx.ALIGN_CENTER_VERTICAL | wx.FIXED_MINSIZE, 0)
        sizer_1.Add(sizer_2, 0, 0, 0)
        sizer_1.Add(self.btn, 0, wx.ALIGN_RIGHT | wx.ADJUST_MINSIZE, 0)
        sizer_1.Add(self.myOlv, 3, wx.EXPAND, 0)
        sizer_1.Add(self.detailBox, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def onGetData(self, event):
        """Event handler to fetch data from server"""
        global jobRows
        global serverStatus
        global jobsCachedUntil
        global serverTime

        serverTime = datetime.datetime.utcnow().replace(microsecond=0)  # Update Server Time.
        # Inform the user what we are doing.
        self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Connecting to Tranquility...')
        serverStatus = getServerStatus(serverStatus)  # Try the API server for current server status.

        if serverStatus[0] == 'Tranquility Online':  # Status has returned a value other than online, so why continue?
            if serverTime >= jobsCachedUntil:
                # Get user settings.
                if pilotRows != []:  # Make sure we have keys in the config
                    # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, isActive
                    #(keyID, vCode, characterID) = (pilotRows[0].keyID, pilotRows[0].vCode, pilotRows[0].characterID)
                    numPilotRows = list(range(len(pilotRows)))
                    for x in numPilotRows:  # Iterate over all of the keys and character ids in config
                        #Download the Account Industry Data
                        if pilotRows[x].keyType == 'Corporation':
                            baseUrl = 'https://api.eveonline.com/corp/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s'
                        else:  # Should be an account key
                            baseUrl = 'https://api.eveonline.com/char/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s'

                        apiURL = baseUrl % (pilotRows[x].keyID, pilotRows[x].vCode, pilotRows[x].characterID)
                        print(apiURL)  # Console debug

                        try:  # Try to connect to the API server
                            target = urllib2.urlopen(apiURL)  # download the file
                            downloadedData = target.read()  # convert to string
                            target.close()  # close file because we don't need it anymore:

                            XMLData = parseString(downloadedData)
                            dataNodes = XMLData.getElementsByTagName("row")

                            cacheuntil = XMLData.getElementsByTagName('cachedUntil')
                            cacheExpire = datetime.datetime(*(time.strptime((cacheuntil[0].firstChild.nodeValue), "%Y-%m-%d %H:%M:%S")[0:6]))
                            jobsCachedUntil = cacheExpire

                            itemIDs = []
                            installerIDs = []
                            for row in dataNodes:
                                if row.getAttribute('completed') == '0':  # Ignore Delivered Jobs
                                    if int(row.getAttribute('installedItemTypeID')) not in itemIDs:
                                        itemIDs.append(int(row.getAttribute('installedItemTypeID')))
                                    if int(row.getAttribute('outputTypeID')) not in itemIDs:
                                        itemIDs.append(int(row.getAttribute('outputTypeID')))
                                    if int(row.getAttribute('installerID')) not in installerIDs:
                                        installerIDs.append(int(row.getAttribute('installerID')))

                            itemNames = id2name('item', itemIDs)
                            pilotNames = id2name('character', installerIDs)

                            for row in dataNodes:
                                if row.getAttribute('completed') == '0':  # Ignore Delivered Jobs
                                    jobRows.append(Job(row.getAttribute('jobID'),
                                                    row.getAttribute('completedStatus'),
                                                    int(row.getAttribute('activityID')),  # Leave as int for clauses
                                                    itemNames[int(row.getAttribute('installedItemTypeID'))],
                                                    int(row.getAttribute('installedItemProductivityLevel')),
                                                    int(row.getAttribute('installedItemMaterialLevel')),
                                                    pilotNames[int(row.getAttribute('installerID'))],
                                                    int(row.getAttribute('runs')),
                                                    itemNames[int(row.getAttribute('outputTypeID'))],
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
                            import traceback
                            error = ('Generic Exception: ' + traceback.format_exc())  # Server Status String
                            self.statusbar.SetStatusText(error)
                            onError(error)
                    self.myOlv.SetObjects(jobRows)
                else:
                    onError(self, 'Please open config to enter a valid API key')
            else:
                numItems = list(range(len(jobRows)))
                for r in numItems:
                    if jobRows[r].endProductionTime > serverTime:
                        jobRows[r].timeRemaining = jobRows[r].endProductionTime - serverTime
                        jobRows[r].state = 'In Progress'
                    else:
                        jobRows[r].timeRemaining = jobRows[r].endProductionTime - serverTime
                        jobRows[r].state = 'Ready'
                self.myOlv.RefreshObjects(jobRows)
                print('Not Contacting Server, Cache Not Expired')

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

#       activities = {1 : 'Manufacturing', 2 : '2', 3 : 'Time Efficiency Research', 4 : 'Material Research',
#                     5 : 'Copy', 6 : '6', 7 : '7', 8 : 'Invention'} # POS activities list.
        if currentItem.activityID == 1:  # Manufacturing
            details = ('TTC: %s\n%s runs of %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        elif currentItem.activityID == 2:  # FIXME
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        elif currentItem.activityID == 3:  # Time Efficiency Research
            details = ('TTC: %s\nInstall PE: %s\nOutput PE %s\n1 unit of %s\n' %
                (details, currentItem.installedItemProductivityLevel,
                (currentItem.installedItemProductivityLevel + currentItem.runs), currentItem.outputTypeID))
        elif currentItem.activityID == 4:  # Material Research
            details = ('TTC: %s\nInstall ME: %s\nOutput ME %s\n1 unit of %s\n' %
                (details, currentItem.installedItemMaterialLevel,
                (currentItem.installedItemMaterialLevel + currentItem.runs), currentItem.outputTypeID))
        elif currentItem.activityID == 5:  # Copy
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        elif currentItem.activityID == 6:  # FIXME
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        elif currentItem.activityID == 7:  # FIXME
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        elif currentItem.activityID == 8:  # Invention
            details = ('TTC: %s\n%s x %s\n' % (details, currentItem.runs, currentItem.outputTypeID))
        else:  # Fall back unknown activity
            details = ('TTC: %s\n%s runs of %s\n' % (details, currentItem.runs, currentItem.outputTypeID))

        self.detailBox.SetValue(details)

    def onConfig(self, event):
        # Open the config frame for user.
        dlg = PreferencesDialog(None, -1, '')
        dlg.ShowModal()  # Show it
        dlg.Destroy()  # finally destroy it when finished.

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

        info.SetIcon(wx.Icon('images/nesi.png', wx.BITMAP_TYPE_PNG))
        info.SetName('Nova Echo Science & Industry')
        info.SetVersion('0.0.1')
        info.SetDescription(description)
        info.SetCopyright('(C) 2013 Tim Cumming')
        info.SetWebSite('https://github.com/EluOne/Nesi')
        info.SetLicence(licence)
        info.AddDeveloper('Tim Cumming aka Elusive One')
        #info.AddDocWriter('Tim Cumming')
        #info.AddArtist('Tim Cumming')
        #info.AddTranslator('Tim Cumming')

        wx.AboutBox(info)

    def onExit(self, event):
        dlg = wx.MessageDialog(self, 'Are you sure to quit Nesi?', 'Please Confirm',
                                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.Close(True)

# end of class MainWindow


class MyApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        frame = MainWindow(None, -1, '')
        self.SetTopWindow(frame)
        frame.Show()
        return 1

# end of class MyApp

if __name__ == '__main__':
    app = MyApp(0)
    app.MainLoop()
