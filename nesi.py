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
from ObjectListView import ObjectListView, ColumnDefn, GroupListView
from time import clock

import sqlite3 as lite
import urllib2
import httplib
import os.path
import pickle
import wx
import datetime
import time
import traceback


# Establish some current time data for calculations later.
# Server Time is UTC so we will use that for now generated locally.
serverTime = datetime.datetime.utcnow().replace(microsecond=0)
# Client Time reported locally.
localTime = datetime.datetime.now().replace(microsecond=0)
# A global variable to store the returned status.
serverStatus = ['', '0', serverTime]
# A global variables to store the cacheUtil time and table rows.
jobsCachedUntil = serverTime
jobRows = []
starbaseCachedUntil = serverTime
starbaseRows = []
# This is where we are storing our API keys for now.
pilotRows = []


class Job(object):
    def __init__(self, jobID, completedStatus, activityID, installedItemTypeID,
                 installedItemProductivityLevel, installedItemMaterialLevel, outputLocationID,
                 installedInSolarSystemID, installerID, runs, outputTypeID, installTime, endProductionTime):
        self.jobID = jobID
        self.completedStatus = completedStatus
        self.activityID = activityID
        self.installedItemTypeID = installedItemTypeID
        self.installedItemProductivityLevel = installedItemProductivityLevel
        self.installedItemMaterialLevel = installedItemMaterialLevel
        self.outputLocationID = outputLocationID
        self.installedInSolarSystemID = installedInSolarSystemID
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


class Starbase(object):
    def __init__(self, itemID, typeID, typeStr, locationID, moonID, state, stateTimestamp, onlineTimestamp,
                 #fuelBlocks, blockQty, charters, charterQty, stront, strontQty, standingOwnerID):
                 fuel, standingOwnerID):
        self.itemID = itemID
        self.typeID = typeID
        self.typeStr = typeStr
        self.locationID = locationID
        self.moonID = moonID  # if unanchored moonID will be 0
        self.state = state
        # If anchored but offline there will be no time data
        if stateTimestamp == '':
            self.stateTimestamp = 'Offline'
        else:
            self.stateTimestamp = datetime.datetime(*(time.strptime(stateTimestamp, '%Y-%m-%d %H:%M:%S')[0:6]))
        # if unanchored there will be a stateTimestamp but no onlineTimestamp
        if onlineTimestamp == '':
            self.onlineTimestamp = 'No Data'
        else:
            self.onlineTimestamp = datetime.datetime(*(time.strptime(onlineTimestamp, '%Y-%m-%d %H:%M:%S')[0:6]))
        self.fuel = fuel
        self.standingOwnerID = standingOwnerID


class Character(object):
    def __init__(self, keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, isActive):
        self.keyID = keyID
        self.vCode = vCode
        self.characterID = characterID
        self.characterName = characterName
        self.corporationID = corporationID
        self.corporationName = corporationName
        self.keyType = keyType
        if keyExpires == '':  # API Server returns blank field for keys that have no expiry date set.
            self.keyExpires = 'Never'
        else:
            self.keyExpires = datetime.datetime(*(time.strptime(keyExpires, '%Y-%m-%d %H:%M:%S')[0:6]))
        self.isActive = isActive


# Lets try to load up our API keys from the config file.
# This requires the above classes to work.
if (os.path.isfile('nesi.ini')):
    iniFile = open('nesi.ini', 'r')
    pilotRows = pickle.load(iniFile)
    iniFile.close()


def onError(error):
    dlg = wx.MessageDialog(None, 'An error has occurred:\n' + error, '', wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()  # Show it
    dlg.Destroy()  # finally destroy it when finished.


def apiCheck(keyID, vCode):
    pilots = []
    baseUrl = 'https://api.eveonline.com/account/APIKeyInfo.xml.aspx?keyID=%s&vCode=%s'
    apiURL = baseUrl % (keyID, vCode)
    # print(apiURL)  # Console debug

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
        error = ('HTTP Error: ' + str(err.code) + str(err.reason)
                 + '\nPlease check you key details have been entered correctly.')  # Error String
        onError(error)
    except urllib2.URLError as err:
        error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
        onError(error)
    except httplib.HTTPException as err:
        error = ('HTTP Exception')  # Error String
        onError(error)
    except Exception:
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
            # Exception String, Players Online data 0 as no data, Cache Until now as no data
            status = [('Generic Exception: ' + traceback.format_exc()), '0', serverTime]
            onError(status[0])

        return status
    else:
        # print('Not Contacting Server For Status')
        return args


def id2name(idType, ids):  # Takes a list of IDs to query the local db or api server.
    typeNames = {}
    if idType == 'item':
        # We'll use the local static DB for items as they don't change.
        if ids != []:  # We have some ids we don't know.
            try:
                idList = ("', '".join(map(str, ids[:])))
                con = lite.connect('static.db')

                with con:
                    cur = con.cursor()
                    statement = "SELECT typeID, typeName FROM invtypes WHERE typeID IN ('" + idList + "')"
                    cur.execute(statement)

                    rows = cur.fetchall()

                    # Use the item strings returned to populate the typeNames dictionary.
                    for row in rows:
                        typeNames.update({int(row[0]): str(row[1])})
                        ids.remove(row[0])

                if ids != []:  # We have some ids we don't know.
                    numItems = range(len(ids))
                    for y in numItems:
                        typeNames.update({int(ids[y]): str(ids[y])})
                    error = ('ids not found in database: ' + str(ids))  # Error String
                    onError(error)

            except lite.Error as err:
                error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
                ids = idList.split("', '")
                numItems = range(len(ids))
                for y in numItems:
                    typeNames.update({int(ids[y]): str(ids[y])})
                onError(error)
            finally:
                if con:
                    con.close()

    elif idType == 'character':
        # We'll have to talk to the API server for Pilot names as this can't be in the static dump.
        cacheFile = 'character.cache'
        baseUrl = 'https://api.eveonline.com/eve/CharacterName.xml.aspx?ids=%s'
        key = 'characterID'
        value = 'name'

        if (os.path.isfile(cacheFile)):
            typeFile = open(cacheFile, 'r')
            typeNames = pickle.load(typeFile)
            typeFile.close()

        numItems = list(range(len(ids)))
        # print(ids)  # Console debug

        for x in numItems:
            if ids[x] in typeNames:
                ids[x] = 'deleted'

        for y in ids[:]:
            if y == 'deleted':
                ids.remove(y)

        # print(ids)  # Console debug

        if ids != []:  # We still have some ids we don't know
            # Calculate the number of ids we have left. Server has hard maximum of 250 IDs per query.
            # So we'll need to split this into multiple queries.
            numIDs = len(ids)
            idList = []

            if numIDs > 250:
                startID = 0
                endID = 250
                while startID < numIDs:
                    idList.append(','.join(map(str, ids[startID:endID])))
                    startID = startID + 250
                    if ((numIDs - endID)) > 250:
                        endID = endID + 250
                    else:
                        endID = numIDs

            else:
                idList.append(','.join(map(str, ids[0:numIDs])))

            numIdLists = list(range(len(idList)))
            for x in numIdLists:  # Iterate over all of the id lists generated above.

                #Download the TypeName Data from API server
                apiURL = baseUrl % (idList[x])
                # print(apiURL)  # Console debug

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
                    error = ('HTTP Error: ' + str(err.code) + str(err.reason))  # Error String
                    ids = idList[x].split(',')
                    numItems = range(len(ids))
                    for y in numItems:
                        typeNames.update({int(ids[y]): str(ids[y])})
                    onError(error)
                except urllib2.URLError as err:
                    error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
                    ids = idList[x].split(',')
                    numItems = range(len(ids))
                    for y in numItems:
                        typeNames.update({int(ids[y]): str(ids[y])})
                    onError(error)
                except httplib.HTTPException as err:
                    error = ('HTTP Exception')  # Error String
                    ids = idList[x].split(',')
                    numItems = range(len(ids))
                    for y in numItems:
                        typeNames.update({int(ids[y]): str(ids[y])})
                    onError(error)
                except Exception:
                    error = ('Generic Exception: ' + traceback.format_exc())  # Error String
                    ids = idList[x].split(',')
                    numItems = range(len(ids))
                    for y in numItems:
                        typeNames.update({int(ids[y]): str(ids[y])})
                    onError(error)

    return typeNames


def is32(n):
    try:
        bitstring = bin(n)
    except (TypeError, ValueError):
        return False

    if len(bin(n)[2:]) <= 32:
        return True
    else:
        return False


def id2location(pilotRowID, ids):  # Take location IDs from API and use against local copy of the static data dump
    locationNames = {0: 'Unanchored'}
    locationIDs = []
    privateLocationIDs = []
    conquerableIDs = []

    numItems = list(range(len(ids)))
    # print(ids)  # Console debug

    for x in numItems:
        if is32(ids[x]) == False:
            # 32 bit value: Only known to Pilot or Corp via API
            privateLocationIDs.append(ids[x])
        elif 66000000 < ids[x] < 66014933:
            # Office in Station needs conversion
            officeID = ids[x] - 6000001
            if officeID not in locationIDs:
                locationIDs.append(officeID)
        elif 66014934 < ids[x] < 67999999:
            # Office in Conquerable Station needs conversion
            officeID = ids[x] - 6000000
            if officeID not in locationIDs:
                locationIDs.append(officeID)
        elif 60014861 < ids[x] < 60014928:
            # Conquerable Station
            if ids[x] not in conquerableIDs:
                conquerableIDs.append(ids[x])
        elif 60000000 < ids[x] < 61000000:
            # Station
            if ids[x] not in locationIDs:
                locationIDs.append(ids[x])
        elif 61000000 <= ids[x] < 66000000:
            # Conquerable Outpost
            if ids[x] not in conquerableIDs:
                conquerableIDs.append(ids[x])
        elif ids[x] < 60000000:  # locationID < 60000000 then the asset is somewhere in space
            if ids[x] not in locationIDs:
                locationIDs.append(ids[x])
        else:  # I am currently unsure how to translate this value, most likely an unexpected value.
            if ids[x] not in locationIDs:
                locationNames.update({int(ids[x]): str(ids[x])})

    if locationIDs != []:  # We still have some ids we don't know
        try:
            idList = ("', '".join(map(str, locationIDs[:])))
            con = lite.connect('static.db')

            with con:
                cur = con.cursor()
                statement = "SELECT itemID, itemName FROM invnames WHERE itemID IN ('" + idList + "')"
                cur.execute(statement)

                rows = cur.fetchall()

                # print((len(rows)))
                for row in rows:
                    # print(row)
                    locationNames.update({int(row[0]): str(row[1])})

        except lite.Error as err:
            error = ('SQL Lite Error: ' + str(err.args[0]) + str(err.args[1:]))  # Error String
            ids = idList.split("', '")
            numItems = range(len(ids))
            for y in numItems:
                locationNames.update({int(ids[y]): str(ids[y])})
            onError(error)
        finally:
            if con:
                con.close()

    if privateLocationIDs != []:  # We have some Pilot or Corp locations we don't know
        if pilotRows[pilotRowID].keyType == 'Corporation':
            baseUrl = 'https://api.eveonline.com/corp/locations.xml.aspx?keyID=%s&vCode=%s&characterID=%s&IDs=%s'
        else:  # Should be an account key
            baseUrl = 'https://api.eveonline.com/char/locations.xml.aspx?keyID=%s&vCode=%s&characterID=%s&IDs=%s'

        # Calculate the number of ids we have left. Server has hard maximum of 250 IDs per query.
        # So we'll need to split this into multiple queries.
        numIDs = len(privateLocationIDs)
        idList = []

        if numIDs > 250:
            startID = 0
            endID = 250
            while startID < numIDs:
                idList.append(','.join(map(str, privateLocationIDs[startID:endID])))
                startID = startID + 250
                if ((numIDs - endID)) > 250:
                    endID = endID + 250
                else:
                    endID = numIDs

        else:
            idList.append(','.join(map(str, privateLocationIDs[0:numIDs])))

        numIdLists = list(range(len(idList)))
        for x in numIdLists:  # Iterate over all of the id lists generated above.

            #Download the TypeName Data from API server
            apiURL = baseUrl % (pilotRows[pilotRowID].keyID, pilotRows[pilotRowID].vCode, pilotRows[pilotRowID].characterID, idList[x])
            # print(apiURL)  # Console debug

            try:  # Try to connect to the API server
                target = urllib2.urlopen(apiURL)  # download the file
                downloadedData = target.read()  # convert to string
                target.close()  # close file because we don't need it anymore

                XMLData = parseString(downloadedData)
                dataNodes = XMLData.getElementsByTagName('row')

                for row in dataNodes:
                    locationNames.update({int(row.getAttribute('itemID')): str(row.getAttribute('itemName'))})
            except urllib2.HTTPError as err:
                error = ('HTTP Error: ' + str(err.code) + str(err.reason))  # Error String
                ids = idList[x].split(',')
                numItems = range(len(ids))
                for y in numItems:
                    locationNames.update({int(ids[y]): str(ids[y])})
                onError(error)
            except urllib2.URLError as err:
                error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
                ids = idList[x].split(',')
                numItems = range(len(ids))
                for y in numItems:
                    locationNames.update({int(ids[y]): str(ids[y])})
                onError(error)
            except httplib.HTTPException as err:
                error = ('HTTP Exception')  # Error String
                ids = idList[x].split(',')
                numItems = range(len(ids))
                for y in numItems:
                    locationNames.update({int(ids[y]): str(ids[y])})
                onError(error)
            except Exception:
                error = ('Generic Exception: ' + traceback.format_exc())  # Error String
                ids = idList[x].split(',')
                numItems = range(len(ids))
                for y in numItems:
                    locationNames.update({int(ids[y]): str(ids[y])})
                onError(error)

    if conquerableIDs != []:  # We have some conquerableIDs we don't know
        idList = []

        apiURL = 'https://api.eveonline.com/eve/ConquerableStationList.xml.aspx'

        try:  # Try to connect to the API server
            target = urllib2.urlopen(apiURL)  # download the file
            downloadedData = target.read()  # convert to string
            target.close()  # close file because we don't need it anymore

            XMLData = parseString(downloadedData)
            dataNodes = XMLData.getElementsByTagName('row')

            for row in dataNodes:
                if int(row.getAttribute('stationID')) in idList:
                    locationNames.update({int(row.getAttribute('stationID')): str(row.getAttribute('stationName'))})

        except urllib2.HTTPError as err:
            error = ('HTTP Error: ' + str(err.code) + str(err.reason))  # Error String
            ids = idList[x].split(',')
            numItems = range(len(ids))
            for y in numItems:
                locationNames.update({int(ids[y]): str(ids[y])})
            onError(error)
        except urllib2.URLError as err:
            error = ('Error Connecting to Tranquility: ' + str(err.reason))  # Error String
            ids = idList[x].split(',')
            numItems = range(len(ids))
            for y in numItems:
                locationNames.update({int(ids[y]): str(ids[y])})
            onError(error)
        except httplib.HTTPException as err:
            error = ('HTTP Exception')  # Error String
            ids = idList[x].split(',')
            numItems = range(len(ids))
            for y in numItems:
                locationNames.update({int(ids[y]): str(ids[y])})
            onError(error)
        except Exception:
            error = ('Generic Exception: ' + traceback.format_exc())  # Error String
            ids = idList[x].split(',')
            numItems = range(len(ids))
            for y in numItems:
                locationNames.update({int(ids[y]): str(ids[y])})
            onError(error)

    return locationNames


def jobRowFormatter(listItem, row):  # Formatter for ObjectListView, will turn completed jobs green.
    if row.timeRemaining < datetime.timedelta(0):
        listItem.SetTextColour((0, 192, 0))


def apiRowFormatter(listItem, row):  # Formatter for GroupListView, will turn expired api keys red.
    if row.keyExpires != 'Never':
        if row.keyExpires < serverTime:
            listItem.SetTextColour(wx.RED)


def apiGroupKeyConverter(groupKey):
    # Convert the given group key (which is a date) into a representation string
    return 'API Key: %s' % (groupKey)


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


class PreferencesDialog(wx.Dialog):
    def __init__(self, *args, **kwds):
        # begin wxGlade: PreferenceDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.label_4 = wx.StaticText(self, -1, "Key ID:")
        self.keyIDTextCtrl = wx.TextCtrl(self, -1, "")
        self.label_5 = wx.StaticText(self, -1, "vCode:")
        self.vCodeTextCtrl = wx.TextCtrl(self, -1, "")
        self.addBtn = wx.Button(self, wx.ID_ADD, "")
        self.charList = GroupListView(self, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.cancelBtn = wx.Button(self, wx.ID_CANCEL)
        self.deleteBtn = wx.Button(self, -1, "Delete")
        self.saveBtn = wx.Button(self, -1, "Save")

        self.__set_properties()
        self.__do_layout()
        # end wxGlade

        self.saveBtn.Bind(wx.EVT_BUTTON, self.onSave)
        self.addBtn.Bind(wx.EVT_BUTTON, self.onAdd)
        self.deleteBtn.Bind(wx.EVT_BUTTON, self.onDelete)

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
        self.tempPilotRows = pilotRows[:]
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
                        # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, isActive
                        self.tempPilotRows.append(Character(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], 0))

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
        global pilotRows
        global jobsCachedUntil
        pilotRows = self.tempPilotRows[:]
        jobsCachedUntil = serverTime  # Lets reset the cache time as we have updated the api keys.
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

        # Menu Bar
        self.frame_menubar = wx.MenuBar()
        self.fileMenu = wx.Menu()
        self.menuAbout = wx.MenuItem(self.fileMenu, wx.NewId(), "&About", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuAbout)
        self.menuConfig = wx.MenuItem(self.fileMenu, wx.NewId(), "&Configure", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuConfig)
        self.menuExit = wx.MenuItem(self.fileMenu, wx.NewId(), "E&xit", "", wx.ITEM_NORMAL)
        self.fileMenu.AppendItem(self.menuExit)
        self.frame_menubar.Append(self.fileMenu, "File")
        self.SetMenuBar(self.frame_menubar)
        # Menu Bar end
        self.statusbar = self.CreateStatusBar(1, 0)
        self.bitmap_1 = wx.StaticBitmap(self, -1, wx.Bitmap("images/nesi.png", wx.BITMAP_TYPE_ANY))
        self.label_1 = wx.StaticText(self, -1, "Nova Echo Science and Industry")
        self.mainNotebook = wx.Notebook(self, -1, style=0)
        self.notebookJobPane = wx.Panel(self.mainNotebook, -1)
        self.jobBtn = wx.Button(self.notebookJobPane, -1, "Get Jobs")
        self.jobList = ObjectListView(self.notebookJobPane, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.jobDetailBox = wx.TextCtrl(self.notebookJobPane, -1, "", style=wx.TE_MULTILINE)
        self.notebookStarbasePane = wx.Panel(self.mainNotebook, -1)
        self.starbaseBtn = wx.Button(self.notebookStarbasePane, -1, "Refresh")
        self.starbaseList = ObjectListView(self.notebookStarbasePane, -1, style=wx.LC_REPORT | wx.SUNKEN_BORDER)
        self.starbaseDetailBox = wx.TextCtrl(self.notebookStarbasePane, -1, "", style=wx.TE_MULTILINE)

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_MENU, self.onAbout, self.menuAbout)
        self.Bind(wx.EVT_MENU, self.onConfig, self.menuConfig)
        self.Bind(wx.EVT_MENU, self.onExit, self.menuExit)
        self.Bind(wx.EVT_BUTTON, self.onGetJobs, self.jobBtn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onJobSelect, self.jobList)
        self.Bind(wx.EVT_BUTTON, self.onGetStarbases, self.starbaseBtn)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onStarbaseSelect, self.starbaseList)
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

    def __do_layout(self):
        # begin wxGlade: MainWindow.__do_layout
        mainSizer = wx.BoxSizer(wx.VERTICAL)
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
        self.mainNotebook.AddPage(self.notebookJobPane, "Jobs")
        self.mainNotebook.AddPage(self.notebookStarbasePane, "Starbases")
        mainSizer.Add(self.mainNotebook, 1, wx.EXPAND, 0)
        self.SetSizer(mainSizer)
        self.Layout()
        # end wxGlade

    def onGetJobs(self, event):
        """Event handler to fetch job data from server"""
        global jobRows
        global serverStatus
        global jobsCachedUntil
        global serverTime

        timingMsg = 'Using Local Cache'
        serverTime = datetime.datetime.utcnow().replace(microsecond=0)  # Update Server Time.
        # Inform the user what we are doing.
        self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Connecting to Tranquility...')
        serverStatus = getServerStatus(serverStatus)  # Try the API server for current server status.

        if serverStatus[0] == 'Tranquility Online':  # Status has returned a value other than online, so why continue?
            if serverTime >= jobsCachedUntil:
                # Start the clock.
                t = clock()
                tempJobRows = []
                if pilotRows != []:  # Make sure we have keys in the config
                    # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, isActive
                    numPilotRows = list(range(len(pilotRows)))
                    for x in numPilotRows:  # Iterate over all of the keys and character ids in config
                        #Download the Account Industry Data
                        keyOK = 1  # Set key check to OK test below changes if expired
                        if pilotRows[x].keyExpires != 'Never':
                            if pilotRows[x].keyExpires < serverTime:
                                keyOK = 0
                                error = ('KeyID' + pilotRows[x].keyID + 'has Expired')
                                onError(error)

                        if keyOK == 1:
                            if pilotRows[x].keyType == 'Corporation':
                                baseUrl = 'https://api.eveonline.com/corp/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s'
                            else:  # Should be an account key
                                baseUrl = 'https://api.eveonline.com/char/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s'

                            apiURL = baseUrl % (pilotRows[x].keyID, pilotRows[x].vCode, pilotRows[x].characterID)
                            # print(apiURL)  # Console debug

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
                                locationNames = id2location(x, locationIDs)

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
                    timingMsg = 'Updated in: %0.2f ms' % (((clock() - t) * 1000))
                else:
                    onError('Please open Config to enter a valid API key')
            else:
                numItems = list(range(len(jobRows)))
                for r in numItems:
                    if jobRows[r].endProductionTime > serverTime:
                        jobRows[r].timeRemaining = jobRows[r].endProductionTime - serverTime
                        jobRows[r].state = 'In Progress'
                    else:
                        jobRows[r].timeRemaining = jobRows[r].endProductionTime - serverTime
                        jobRows[r].state = 'Ready'
                self.jobList.RefreshObjects(jobRows)
                # print('Not Contacting Server, Cache Not Expired')

            self.statusbar.SetStatusText(serverStatus[0] + ' - ' + serverStatus[1]
                                         + ' Players Online - EvE Time: ' + str(serverTime)
                                         + ' - API Cached Until: ' + str(jobsCachedUntil)
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
        global serverTime

        timingMsg = 'Using Local Cache'
        serverTime = datetime.datetime.utcnow().replace(microsecond=0)  # Update Server Time.
        # Inform the user what we are doing.
        self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Connecting to Tranquility...')
        serverStatus = getServerStatus(serverStatus)  # Try the API server for current server status.

        if serverStatus[0] == 'Tranquility Online':  # Status has returned a value other than online, so why continue?
            if serverTime >= starbaseCachedUntil:
                # Start the clock.
                t = clock()
                tempStarbaseRows = []
                if pilotRows != []:  # Make sure we have keys in the config
                    # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, isActive
                    numPilotRows = list(range(len(pilotRows)))
                    for x in numPilotRows:  # Iterate over all of the keys and character ids in config
                        #Download the Account Starbase Data
                        keyOK = 1  # Set key check to OK test below changes if expired
                        if pilotRows[x].keyExpires != 'Never':
                            if pilotRows[x].keyExpires < serverTime:
                                keyOK = 0
                                error = ('KeyID' + pilotRows[x].keyID + 'has Expired')
                                onError(error)

                        if keyOK == 1 and pilotRows[x].keyType == 'Corporation':
                            baseUrl = 'https://api.eveonline.com/corp/StarbaseList.xml.aspx?keyID=%s&vCode=%s'
                            apiURL = baseUrl % (pilotRows[x].keyID, pilotRows[x].vCode)
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
                                    apiURL = baseUrl % (pilotRows[x].keyID, pilotRows[x].vCode, row.getAttribute('itemID'))
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
                                        locationNames = id2location(x, locationIDs)

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
                    if tempStarbaseRows != []:
                        starbaseRows = tempStarbaseRows[:]
                    self.starbaseList.SetObjects(starbaseRows)
                    timingMsg = 'Updated in: %0.2f ms' % (((clock() - t) * 1000))
                else:
                    onError('Please open Config to enter a valid API key')
            else:
                self.starbaseList.RefreshObjects(jobRows)
                # print('Not Contacting Server, Cache Not Expired')

            self.statusbar.SetStatusText(serverStatus[0] + ' - ' + serverStatus[1]
                                         + ' Players Online - EvE Time: ' + str(serverTime)
                                         + ' - API Cached Until: ' + str(jobsCachedUntil)
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
        info.SetVersion('1.1.0')
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
