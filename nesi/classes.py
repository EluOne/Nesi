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
# Modified: 21/02/15

import datetime
import time

import config


# Use objects for referencing the data within each row and column.


class Character(object):
    def __init__(self, keyID, vCode, characterID, characterName, corporationID, corporationName, keyType, keyExpires, skills, isActive):
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
        self.skills = skills
        self.isActive = isActive

# end of class Character


class Server(object):
    def __init__(self, serverName, serverAddress, serverStatus, serverPlayers, cacheExpire):
        self.svrName = serverName
        self.svrAddress = serverAddress
        self.svrStatus = serverStatus
        self.svrPlayers = serverPlayers
        self.svrCacheExpire = cacheExpire

# end of class Server


class Job(object):
    def __init__(self, jobID, completedStatus, activityID, installedItemTypeID,
                 outputLocationID,
                 installedInSolarSystemID, installerID, runs, outputTypeID, installTime, endProductionTime):
        self.jobID = jobID
        self.completedStatus = completedStatus
        self.activityID = activityID
        self.installedItemTypeID = installedItemTypeID
        # self.installedItemProductivityLevel = installedItemProductivityLevel
        # self.installedItemMaterialLevel = installedItemMaterialLevel
        self.outputLocationID = outputLocationID
        self.installedInSolarSystemID = installedInSolarSystemID
        self.installerID = installerID
        self.runs = runs
        self.outputTypeID = outputTypeID
        self.installTime = datetime.datetime(*(time.strptime(installTime, '%Y-%m-%d %H:%M:%S')[0:6]))
        self.endProductionTime = datetime.datetime(*(time.strptime(endProductionTime, '%Y-%m-%d %H:%M:%S')[0:6]))
        if self.endProductionTime > config.serverTime:
            self.timeRemaining = self.endProductionTime - config.serverTime
            self.state = 'In Progress'
        else:
            self.timeRemaining = self.endProductionTime - config.serverTime
            self.state = 'Ready'

    # New API Output
    # columns="jobID,installerID,installerName,facilityID,solarSystemID,solarSystemName,
    # stationID,activityID,blueprintID,blueprintTypeID,blueprintTypeName,blueprintLocationID,
    # outputLocationID,runs,cost,teamID,licensedRuns,probability,productTypeID,productTypeName,
    # status,timeInSeconds,startDate,endDate,pauseDate,completedDate,completedCharacterID,successfulRuns"

# Old S&I window shows: state, activity, type, location, jumps, installer, owner, install date, end date
# This is what the API returns:
# columns="jobID,assemblyLineID,containerID,installedItemID,installedItemLocationID,installedItemQuantity
# installedItemProductivityLevel,installedItemMaterialLevel,installedItemLicensedProductionRunsRemaining,
# outputLocationID,installerID,runs,licensedProductionRuns,installedInSolarSystemID,containerLocationID,
# materialMultiplier,charMaterialMultiplier,timeMultiplier,charTimeMultiplier,installedItemTypeID,outputTypeID,
# containerTypeID,installedItemCopy,completed,completedSuccessfully,installedItemFlag,outputFlag,activityID,
# completedStatus,installTime,beginProductionTime,endProductionTime,pauseProductionTime"

# end of class Job


class Starbase(object):
    def __init__(self, itemID, typeID, typeStr, locationID, moonID, state, stateTimestamp, onlineTimestamp,
                 # fuelBlocks, blockQty, charters, charterQty, stront, strontQty, standingOwnerID):
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

# end of class Starbase


class Materials(object):
    def __init__(self, item, quantity, category, damage, waste):
        self.item = item
        self.quantity = quantity
        self.category = category
        self.damage = damage
        self.waste = waste

# end of class Materials


class MlAnalysis(object):
    def __init__(self, item, perfect):
        self.item = item
        self.perfect = perfect

# end of class MlAnalysis
