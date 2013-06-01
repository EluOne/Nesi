#!/usr/bin/python
'Nova Echo Science & Industry'
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

from xml.dom.minidom import parse, parseString
from ObjectListView import ObjectListView, ColumnDefn

import urllib2
import os.path
import pickle
import wx
import datetime
import time

#Enter your UserID, API Key, and CharacterID here
keyID = ''
vCode = ''
characterID = ''

# Load the settings file if we have one.
if (os.path.isfile("nesi.settings")):
    settingsfile = open("nesi.settings",'r')
    keyID = pickle.load(settingsfile)
    vCode = pickle.load(settingsfile)
    characterID = pickle.load(settingsfile)
    settingsfile.close()

if (os.path.isfile("items.cache")):
    itemsfile = open("items.cache",'r')
    items = pickle.load(itemsfile)
    itemsfile.close()


class Job(object):
    def __init__(self, jobID, completedStatus, activityID, installedItemTypeID, installerID, installTime, beginProductionTime, endProductionTime):
        self.jobID = jobID
        self.completedStatus = completedStatus
        self.activityID = activityID
        self.installedItemTypeID = installedItemTypeID
        self.installerID = installerID
        self.installTime = datetime.datetime(*(time.strptime(installTime, "%Y-%m-%d %H:%M:%S")[0:6]))
        self.beginProductionTime = datetime.datetime(*(time.strptime(beginProductionTime, "%Y-%m-%d %H:%M:%S")[0:6]))
        self.endProductionTime = datetime.datetime(*(time.strptime(endProductionTime, "%Y-%m-%d %H:%M:%S")[0:6]))
        self.timeRemaining = self.endProductionTime - self.beginProductionTime
        
# S&I window shows: state, activity, type, location, jumps, installer, owner, install date, end date

#columns="jobID,assemblyLineID,containerID,installedItemID,installedItemLocationID,installedItemQuantity,installedItemProductivityLevel,
#installedItemMaterialLevel,installedItemLicensedProductionRunsRemaining,outputLocationID,installerID,runs,licensedProductionRuns,
#installedInSolarSystemID,containerLocationID,materialMultiplier,charMaterialMultiplier,timeMultiplier,charTimeMultiplier,
#installedItemTypeID,outputTypeID,containerTypeID,installedItemCopy,completed,completedSuccessfully,installedItemFlag,
#outputFlag,activityID,completedStatus,installTime,beginProductionTime,endProductionTime,pauseProductionTime"

class Item(object):
    def __init__(self, typeID, typeName):
        self.typeID = typeID
        self.typeName = typeName

def serverStatus():
    status = []
    #Download the Account Industry Data from API server
    apiURL = 'https://api.eveonline.com/server/ServerStatus.xml.aspx/'

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
    status.append(cacheuntil)

    return status

    
def iid2name(ids): # Takes a list of typeIDs to query the api server.
    items = []
    #Download the TypeName Data from API server
    apiURL = 'https://api.eveonline.com/eve/TypeName.xml.aspx?ids=%s' % (ids)
    return apiURL
'''
    target = urllib2.urlopen(apiURL) #download the file
    downloadedData = target.read() #convert to string
    target.close() #close file because we don't need it anymore

    XMLData = parseString(downloadedData)
    dataNodes = XMLData.getElementsByTagName("row")

    for row in dataNodes:
        items.append(Item(row.getAttribute(u'typeID'),
                        row.getAttribute(u'typeName')))
    return items
'''    

class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        """Constructor"""
        wx.Frame.__init__(self, parent, title=title, size=(1024, 600))

        panel = wx.Panel(self, -1)
        panel.SetBackgroundColour(wx.NullColour) # Use system default colour

        self.statusbar = self.CreateStatusBar() # A Statusbar in the bottom of the window
        self.statusbar.SetStatusText('Welcome to Nesi')

        # Setting up the menu.
        filemenu= wx.Menu()
        menuRefresh= filemenu.Append(wx.ID_ABOUT, "&Refresh"," Refresh The List") # FIXME
        menuAbout= filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar.
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Menu events.
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.GetData, menuRefresh) # FIXME
        
        self.myOlv = ObjectListView(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER)

        self.myOlv.SetColumns([
            ColumnDefn("jobID", "left", 100, "jobID"),
            ColumnDefn("completedStatus", "left", 100, "completedStatus"),
            ColumnDefn("activityID", "left", 100, "activityID"),
            ColumnDefn("installedItemTypeID", "center", 200, "installedItemTypeID"),
            ColumnDefn("installerID", "center", 150, "installerID"),
            ColumnDefn("Install Time", "left", 145, "installTime", stringConverter="%Y-%m-%d %H:%M"),
            ColumnDefn("Start Time", "left", 145, "beginProductionTime", stringConverter="%Y-%m-%d %H:%M"),
            ColumnDefn("End Time", "left", 145, "endProductionTime", stringConverter="%Y-%m-%d %H:%M"),
            ColumnDefn("Time Remaining", "left", 145, "timeRemaining")
        ])
        
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.myOlv, 1, wx.ALL|wx.EXPAND, 4)
        self.SetSizer(sizer)

        
    def GetData(self, e):
        server = serverStatus()
        self.statusbar.SetStatusText('Welcome to Nesi - ' + server[0] + ' - ' + server[1] + ' Players Online')

        #Download the Account Industry Data
        apiURL = 'http://api.eveonline.com/corp/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s' % (keyID, vCode, characterID)
        print apiURL

        #target = urllib2.urlopen(apiURL) #download the file
        target = open('IndustryJobs.xml','r') #open a local xml file for reading: (testing)

        downloadedData = target.read() #convert to string

        #close file because we don't need it anymore:
        target.close()

        XMLData = parseString(downloadedData)
        dataNodes = XMLData.getElementsByTagName("row")

        rows = []
        itemIDs = []
        for row in dataNodes:
            if row.getAttribute(u'completed') == '0': # Ignore Delivered Jobs
                if row.getAttribute(u'installedItemTypeID') not in itemIDs:
                    itemIDs.append(row.getAttribute(u'installedItemTypeID'))
                rows.append(Job(row.getAttribute(u'jobID'),
                                row.getAttribute(u'completedStatus'),
                                row.getAttribute(u'activityID'),
                                row.getAttribute(u'installedItemTypeID'),
                                row.getAttribute(u'installerID'),
                                row.getAttribute(u'installTime'),
                                row.getAttribute(u'beginProductionTime'),
                                row.getAttribute(u'endProductionTime')))

        #print iid2name(itemIDs)
        ids = ''
        for item in itemIDs:
            if ids == '':
                ids = item
            else:
                ids = ('%s,%s' % (ids, item))
        #print items
        print iid2name(ids)
        #print itemIDs
        
        self.myOlv.SetObjects(rows)


    def OnAbout(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog(self, 'Nova Echo S&I', 'About Nesi', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.


    def OnExit(self, e):
        dlg = wx.MessageDialog(self, 'Are you sure to quit Nesi?', 'Please Confirm', wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
        if dlg.ShowModal() == wx.ID_YES:
            self.Close(True)


if __name__ == '__main__':
    app = wx.App(0)
    frame = MainWindow(None, "Nesi")
    app.SetTopWindow(frame)
    frame.Show()
    app.MainLoop()
