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
import datetime
import time
import os.path
import pickle
import urllib2
import httplib
import traceback
import sqlite3 as lite

from xml.dom.minidom import parseString


def onError(error):
    dlg = wx.MessageDialog(None, 'An error has occurred:\n' + error, '', wx.OK | wx.ICON_ERROR)
    dlg.ShowModal()  # Show it
    dlg.Destroy()  # finally destroy it when finished.


def skillCheck(keyID, vCode, characterID):  # TODO: Pull in implants from api.
    skills = {}
    skillUrl = 'https://api.eveonline.com/char/CharacterSheet.xml.aspx?keyID=%s&vCode=%s&characterID=%s' % (keyID, vCode, characterID)

    try:  # Try to connect to the API server

        target = urllib2.urlopen(skillUrl)  # download the file
        skillData = target.read()  # convert to string
        target.close()  # close file because we don't need it anymore:

        XMLSkillData = parseString(skillData)
        skillDataNodes = XMLSkillData.getElementsByTagName('row')

        for skillRow in skillDataNodes:  # At present this will be the full list of pilot skills.
            if (skillRow.getAttribute('typeID') != '') or (skillRow.getAttribute('level') != ''):  # Check for blanks.
                skills[int(skillRow.getAttribute('typeID'))] = int(skillRow.getAttribute('level'))

        # print(skills)  # Console debug

    except urllib2.HTTPError as err:
        error = ('HTTP Error: %s %s\nThis key does not have access to pilot skills.' % (str(err.code), str(err.reason)))  # Error String
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

    return skills


def apiCheck(keyID, vCode):
    pilots = []
    skills = {}
    baseUrl = 'https://api.eveonline.com/account/APIKeyInfo.xml.aspx?keyID=%s&vCode=%s' % (keyID, vCode)
    # print(baseUrl)  # Console debug

    try:  # Try to connect to the API server
        target = urllib2.urlopen(baseUrl)  # download the file
        downloadedData = target.read()  # convert to string
        target.close()  # close file because we don't need it anymore:

        XMLData = parseString(downloadedData)
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

    except urllib2.HTTPError as err:
        error = ('HTTP Error: %s %s\nPlease check your key details have been entered correctly.' % (str(err.code), str(err.reason)))  # Error String
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


def getServerStatus(args, serverTime):
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
        # print('Not Contacting Server For Status')  # Console debug
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
                    error = ('HTTP Error: %s %s' % (str(err.code), str(err.reason)))  # Error String
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


def is32(n):  # Used in id2location to check for 32bit numbers
    try:
        bitstring = bin(n)
    except (TypeError, ValueError):
        return False

    if len(bin(n)[2:]) <= 32:
        return True
    else:
        return False


def id2location(pilotRowID, ids, pilotRows):  # Take location IDs from API and use against local copy of the static data dump
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
                error = ('HTTP Error: %s %s' % (str(err.code), str(err.reason)))  # Error String
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
            error = ('HTTP Error: %s %s' % (str(err.code), str(err.reason)))  # Error String
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
