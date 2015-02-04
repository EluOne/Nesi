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
# Created: 13/01/13
# Modified: 17/01/15

import datetime
import time

import os.path
import pickle

import sqlite3 as lite

from kivy.network.urlrequest import UrlRequest
# from kivy.storage.jsonstore import JsonStore

from xml.dom.minidom import parseString

from nesi.error import onError
from nesi.classes import Job, Character
from nesi.functions import is32, checkClockDrift

import config


# Fetch server status from api server and update values in config.serverConn
# Send results to nesi.statusbar.StatusBar in kivy gui.
def getServerStatus(cacheExpire, serverTime, target):
    print(target)
    # Only query the server if the cache time has expired.
    if serverTime >= cacheExpire:
        # Download the Server Status Data from API server
        apiURL = config.serverConn.svrAddress + 'server/ServerStatus.xml.aspx/'
        print(apiURL)

        # Start the clock!
        t = time.clock()

        def server_status(self, result):
            XMLData = parseString(result)

            currentTime = XMLData.getElementsByTagName('currentTime')
            result = XMLData.getElementsByTagName('result')
            serverOpen = result[0].getElementsByTagName('serverOpen')
            onlinePlayers = result[0].getElementsByTagName('onlinePlayers')
            cacheUntil = XMLData.getElementsByTagName('cachedUntil')

            # The current time as reported by the server at time of query.
            serCurrentTime = datetime.datetime(*(time.strptime((currentTime[0].firstChild.nodeValue), '%Y-%m-%d %H:%M:%S')[0:6]))

            # Use the server reported UTC time to check the clock of our device.
            checkClockDrift(serCurrentTime)

            # This is returned as 'True' for open from the api server.
            if (serverOpen[0].firstChild.nodeValue):
                config.serverConn.svrStatus = 'Online'
            else:
                config.serverConn.svrStatus = 'Down'

            config.serverConn.svrPlayers = (onlinePlayers[0].firstChild.nodeValue)
            config.serverConn.svrCacheExpire = datetime.datetime(*(time.strptime((cacheUntil[0].firstChild.nodeValue), '%Y-%m-%d %H:%M:%S')[0:6]))

            # Stop the clock for this update.
            timingMsg = 'Updated in: %0.2f ms' % (((time.clock() - t) * 1000))

            # Send the data to the gui elements of status_bar
            target.server = str('%s %s' % (config.serverConn.svrName, config.serverConn.svrStatus))
            target.players = str(config.serverConn.svrPlayers)
            target.serverTime = str(config.serverTime)
            target.jobsCachedUntil = str(config.serverConn.svrCacheExpire)
            target.state = str(timingMsg)

            print(timingMsg)

        def server_error(self, error):
            status = 'Error Connecting to %s:\n%s\nAt: %s' % (config.serverConn.svrName, str(error), config.serverTime)
            onError(status)

            print(status)

        target.state = ('Connecting to ' + config.serverConn.svrName)

        UrlRequest(apiURL, on_success=server_status, on_error=server_error, req_headers=config.headers)


# Pull in the character skills and levels from the api server if we have access.
def skillCheck(keyID, vCode, characterID):  # TODO: Pull in implants from api.
    skills = {}
    baseUrl = config.serverConn.svrAddress + 'char/CharacterSheet.xml.aspx?keyID=%s&vCode=%s&characterID=%s'
    apiURL = baseUrl % (keyID, vCode, characterID)

    def skill_process(self, result):
        XMLData = parseString(result)

        skillDataNodes = XMLData.getElementsByTagName('row')

        for skillRow in skillDataNodes:
            skills[skillRow.getAttribute('typeID')] = skillRow.getAttribute('level')

        # print(skills)  # Console debug

    def skill_error(self, error):
        status = 'This key may not have access to pilot skills.\nError Using %s:\n%s\nAt: %s' % (config.serverConn.svrName, str(error), config.serverTime)
        onError(status)

    req = UrlRequest(apiURL, on_success=skill_process, on_error=skill_error, req_headers=config.headers)
    req.wait()

    return skills


# Check an API keyID vCode pair with the server.
def apiCheck(keyID, vCode):
    pilots = []
    skills = {}
    baseUrl = config.serverConn.svrAddress + 'account/APIKeyInfo.xml.aspx?keyID=%s&vCode=%s'
    apiURL = baseUrl % (keyID, vCode)
    print(apiURL)  # Console debug

    def api_process(self, result):
        XMLData = parseString(result)

        key = XMLData.getElementsByTagName('key')
        keyInfo = {'accessMask': key[0].getAttribute('accessMask'),
                   'type': key[0].getAttribute('type'),
                   'expires': key[0].getAttribute('expires')}

        dataNodes = XMLData.getElementsByTagName('row')

        for row in dataNodes:
            # TODO: Need to find out a way to not call this if the key has no access to this data.
            skills = skillCheck(keyID, vCode, row.getAttribute('characterID'))

            pilots.append([keyID, vCode,
                           row.getAttribute('characterID'),
                           row.getAttribute('characterName'),
                           row.getAttribute('corporationID'),
                           row.getAttribute('corporationName'),
                           keyInfo['type'], keyInfo['expires'],
                           skills])

        # TODO: work out how to use this as async
        print('Pilots at end of api_process: ' + str(pilots))

        if pilots != []:
            for row in pilots:
                # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                config.pilotRows.append(Character(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], 0))

        return pilots

    def api_fail(self, result):
        XMLData = parseString(result)

        error = XMLData.getElementsByTagName('error')
        errorInfo = {'number': error[0].getAttribute('code'), 'text': error[0].firstChild.nodeValue}

        status = '%s Returned Error:\n%s\n%s' % (config.serverConn.svrName, errorInfo['number'], errorInfo['text'])
        onError(status)

    def api_error(self, error):
        status = 'Error Connecting to %s:\n%s\nAt: %s' % (config.serverConn.svrName, str(error), config.serverTime)
        onError(status)

    UrlRequest(apiURL, on_success=api_process, on_error=api_error, on_failure=api_fail, req_headers=config.headers)

    return pilots


# Takes a list of IDs to query the local db or api server.
def id2name(idType, ids):
    typeNames = {}
    if idType == 'item':
        # We'll use the local static DB for items as they don't change.
        if ids != []:  # We have some ids we don't know.
            try:
                idList = ("', '".join(map(str, ids[:])))
                con = lite.connect(config.staticDB)

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
        # cacheFile = config.characterCache
        cacheFile = '../character.cache'

        # TODO: Change to JSON
        if (os.path.isfile('cacheFile')):
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
            baseUrl = config.serverConn.svrAddress + 'eve/CharacterName.xml.aspx?ids=%s'
            key = 'characterID'
            value = 'name'

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

                # Download the CharacterName Data from API server
                apiURL = baseUrl % (idList[x])
                # print(apiURL)  # Console debug

                def characterNames_process(self, result):
                    XMLData = parseString(result)
                    dataNodes = XMLData.getElementsByTagName('row')

                    for row in dataNodes:
                        typeNames.update({int(row.getAttribute(key)): str(row.getAttribute(value))})
                        config.characterCache.put(int(row.getAttribute(key)), name=str(row.getAttribute(value)))

                    # Save the data we have so we don't have to fetch it
                    typeFile = open(cacheFile, 'w')
                    pickle.dump(typeNames, typeFile)
                    typeFile.close()

                def characterNames_error(self, error):
                    status = 'Error Connecting to %s:\n%s\nAt: %s' % (config.serverConn.svrName, str(error), config.serverTime)
                    ids = idList[x].split(',')
                    numItems = range(len(ids))
                    for y in numItems:
                        typeNames.update({int(ids[y]): str(ids[y])})
                    onError(status)

                    print(status)

                req = UrlRequest(apiURL, on_success=characterNames_process, on_error=characterNames_error, req_headers=config.headers)
                req.wait()

    return typeNames


# Take location IDs from API and use against local copy of the static data dump
def id2location(pilotRowID, ids, pilotRows):
    locationNames = {0: 'Unanchored'}
    locationIDs = []
    privateLocationIDs = []
    conquerableIDs = []

    numItems = list(range(len(ids)))
    # print(ids)  # Console debug

    for x in numItems:
        if is32(ids[x]) is False:
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
            con = lite.connect(config.staticDB)

            with con:
                cur = con.cursor()
                statement = "SELECT itemID, itemName FROM invnames WHERE itemID IN ('" + idList + "')"
                cur.execute(statement)

                rows = cur.fetchall()

                # print((len(rows)))  # Console debug
                for row in rows:
                    # print(row)  # Console debug
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
            baseUrl = config.serverConn.svrAddress + 'corp/locations.xml.aspx?keyID=%s&vCode=%s&characterID=%s&IDs=%s'
        else:  # Should be an account key
            baseUrl = config.serverConn.svrAddress + 'char/locations.xml.aspx?keyID=%s&vCode=%s&characterID=%s&IDs=%s'

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

            # Download the TypeName Data from API server
            apiURL = baseUrl % (pilotRows[pilotRowID].keyID, pilotRows[pilotRowID].vCode, pilotRows[pilotRowID].characterID, idList[x])
            # print(apiURL)  # Console debug

            def typeNames_process(self, result):
                XMLData = parseString(result)
                dataNodes = XMLData.getElementsByTagName('row')

                for row in dataNodes:
                    locationNames.update({int(row.getAttribute('itemID')): str(row.getAttribute('itemName'))})

            def typeNames_error(self, error):
                status = 'Error Connecting to %s:\n%s\nAt: %s' % (config.serverConn.svrName, str(error), config.serverTime)
                ids = idList[x].split(',')
                numItems = range(len(ids))
                for y in numItems:
                    locationNames.update({int(ids[y]): str(ids[y])})
                onError(status)

                print(status)

            req = UrlRequest(apiURL, on_success=typeNames_process, on_error=typeNames_error, req_headers=config.headers)
            req.wait()

    if conquerableIDs != []:  # We have some conquerableIDs we don't know
        idList = []

        apiURL = config.serverConn.svrAddress + 'eve/ConquerableStationList.xml.aspx'

        def typeNames_process(self, result):
            XMLData = parseString(result)
            dataNodes = XMLData.getElementsByTagName('row')

            for row in dataNodes:
                if int(row.getAttribute('stationID')) in idList:
                    locationNames.update({int(row.getAttribute('stationID')): str(row.getAttribute('stationName'))})

        def typeNames_error(self, error):
            status = 'Error Connecting to %s:\n%s\nAt: %s' % (config.serverConn.svrName, str(error), config.serverTime)
            ids = idList[x].split(',')
            numItems = range(len(ids))
            for y in numItems:
                locationNames.update({int(ids[y]): str(ids[y])})
            onError(status)

            print(status)

        req = UrlRequest(apiURL, on_success=typeNames_process, on_error=typeNames_error, req_headers=config.headers)
        req.wait()

    return locationNames


def getJobs(target):
    """Event handler to fetch job data from server"""
    timingMsg = 'Using Local Cache'
    # Inform the user what we are doing.
    target.state = ('Connecting to ' + config.serverConn.svrName)

    getServerStatus(config.serverConn.svrCacheExpire, config.serverTime, target)  # Try the API server for current server status.

    if config.serverConn.svrStatus == 'Online':  # Status has returned a value other than online, so why continue?
        if config.serverTime >= config.jobsCachedUntil:
            # Start the clock.
            t = time.clock()
            tempJobRows = []

            if config.pilotRows != []:  # Make sure we have keys in the config
                # keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive
                numPilotRows = list(range(len(config.pilotRows)))
                for x in numPilotRows:  # Iterate over all of the keys and character ids in config
                    # Download the Account Industry Data
                    keyOK = 1  # Set key check to OK test below changes if expired
                    if config.pilotRows[x].keyExpires != 'Never':
                        if config.pilotRows[x].keyExpires < config.serverTime:
                            keyOK = 0
                            error = ('KeyID ' + config.pilotRows[x].keyID + ' has Expired')
                            onError(error)

                    if keyOK == 1:
                        if config.pilotRows[x].keyType == 'Corporation':
                            baseUrl = '/corp/IndustryJobsHistory.xml.aspx?keyID=%s&vCode=%s&characterID=%s'
                        else:  # Should be an account key
                            baseUrl = '/char/IndustryJobsHistory.xml.aspx?keyID=%s&vCode=%s&characterID=%s'

                        apiURL = config.serverConn.svrAddress + baseUrl % (config.pilotRows[x].keyID, config.pilotRows[x].vCode, config.pilotRows[x].characterID)
                        print(apiURL)  # Console debug

                        def jobs_process(self, result):

                            XMLData = parseString(result)
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
                                # columns="assemblyLineID,containerID,installedItemLocationID,installedItemQuantity,
                                # installedItemLicensedProductionRunsRemaining,outputLocationID,licensedProductionRuns,
                                # installedInSolarSystemID,containerLocationID,materialMultiplier,charMaterialMultiplier,
                                # timeMultiplier,charTimeMultiplier,containerTypeID,installedItemCopy,completed,
                                # completedSuccessfully,installedItemFlag,outputFlag,completedStatus,beginProductionTime,
                                # pauseProductionTime"

                            print(tempJobRows)

                        def server_error(self, error):
                            status = 'Error Connecting to %s:\n%s\nAt: %s' % (config.serverConn.svrName, str(error), config.serverTime)
                            onError(status)

                            print(status)

                        target.state = ('Connecting to ' + config.serverConn.svrName)

                        UrlRequest(apiURL, on_success=jobs_process, on_error=server_error, req_headers=config.headers)

                if tempJobRows != []:
                    config.jobRows = tempJobRows[:]
#                self.jobList.SetObjects(config.jobRows)
                timingMsg = 'Updated in: %0.2f ms' % (((time.clock() - t) * 1000))
                target.state = str(timingMsg)
            else:
                onError('Please open Config to enter a valid API key')
        else:
            numItems = list(range(len(config.jobRows)))
            for r in numItems:
                if config.jobRows[r].endProductionTime > config.serverTime:
                    config.jobRows[r].timeRemaining = config.jobRows[r].endProductionTime - config.serverTime
                    config.jobRows[r].state = 'In Progress'
                else:
                    config.jobRows[r].timeRemaining = config.jobRows[r].endProductionTime - config.serverTime
                    config.jobRows[r].state = 'Ready'
#            self.jobList.RefreshObjects(config.jobRows)
            # print('Not Contacting Server, Cache Not Expired')

#        self.statusbar.SetStatusText(serverStatus[0] + ' - ' + serverStatus[1]
#                                     + ' Players Online - EvE Time: ' + str(config.serverTime)
#                                     + ' - API Cached Until: ' + str(config.jobsCachedUntil)
#                                     + ' - ' + timingMsg)
    else:
        # Skip everything send 'Using local cache' to status bar.
        # self.statusbar.SetStatusText('Welcome to Nesi - ' + serverStatus[0])
        return()
