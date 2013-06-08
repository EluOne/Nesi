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
import httplib
import os.path
import pickle
import wx
import datetime
import time

# Initialise some variables.
keyID = ''
vCode = ''
characterID = ''
e = ''

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
    def __init__(self, jobID, completedStatus, activityID, installedItemTypeID, installerID, installTime, endProductionTime):
        self.jobID = jobID
        self.completedStatus = completedStatus
        self.activityID = activityID
        self.installedItemTypeID = installedItemTypeID
        self.installerID = installerID
        self.installTime = datetime.datetime(*(time.strptime(installTime, "%Y-%m-%d %H:%M:%S")[0:6]))
        self.endProductionTime = datetime.datetime(*(time.strptime(endProductionTime, "%Y-%m-%d %H:%M:%S")[0:6]))
        self.timeRemaining = self.endProductionTime - self.installTime
        
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
        status.append(cacheuntil)
    except urllib2.HTTPError, e:
        status.append('HTTP Error: ' + str(e.code))
        status.append('0') # Players Online 0 as no data
        status.append('0') # Cache Until data 0 as no data
    except urllib2.URLError, e:
        status.append('Error Connecting to Tranquility: ' + str(e.reason))
        status.append('0') # Players Online 0 as no data
        status.append('0') # Cache Until data 0 as no data
    except httplib.HTTPException, e:
        status.append('HTTP Exception')
        status.append('0') # Players Online 0 as no data
        status.append('0') # Cache Until data 0 as no data
    except Exception:
        import traceback
        status.append('Generic Exception: ' + traceback.format_exc())
        status.append('0') # Players Online 0 as no data
        status.append('0') # Cache Until data 0 as no data

    return status


def iid2name(ids): # Takes a list of typeIDs to query the api server.
    items = []

    idList = ','.join(map(str, ids))

    #Download the TypeName Data from API server
    apiURL = 'https://api.eveonline.com/eve/TypeName.xml.aspx?ids=%s' % (idList)
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


def cid2name(ids): # Takes a list of characterIDs to query the api server.
    characters = []
    
    idList = ','.join(map(str, ids))

    #Download the Character Data from API server
    apiURL = 'https://api.eveonline.com/eve/CharacterName.xml.aspx?ids=%s' % (idList)
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

    return characters
'''    


class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        """Constructor"""
        wx.Frame.__init__(self, parent, title=title, size=(1024, 600))

        panel = wx.Panel(self, -1)
        panel.SetBackgroundColour(wx.NullColour) # Use system default colour

        self.statusbar = self.CreateStatusBar() # A Statusbar in the bottom of the window
        self.statusbar.SetStatusText('Welcome to Nesi')

        # Job Details box TODO
#        self.detailBox = wx.TextCtrl(panel, style=wx.TE_MULTILINE, size=(256,-1))
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


        # Menu events.
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_BUTTON, self.OnGetData, id=1)
        self.Bind(wx.EVT_MENU, self.OnConfig, menuConfig) # TODO

        self.myOlv = ObjectListView(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER)

        self.myOlv.SetColumns([
            ColumnDefn("jobID", "left", 100, "jobID"),
            ColumnDefn("completedStatus", "left", 100, "completedStatus"),
            ColumnDefn("activityID", "left", 100, "activityID"),
            ColumnDefn("installedItemTypeID", "center", 200, "installedItemTypeID"),
            ColumnDefn("installerID", "center", 150, "installerID"),
            ColumnDefn("Install Time", "left", 145, "installTime", stringConverter="%Y-%m-%d %H:%M"),
            ColumnDefn("End Time", "left", 145, "endProductionTime", stringConverter="%Y-%m-%d %H:%M"),
            ColumnDefn("Time Remaining", "left", 145, "timeRemaining")
        ])

 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.myOlv, 1, wx.ALL|wx.EXPAND, 4)
#        sizer.Add(self.detailBox, 1, wx.EXPAND | wx.ALL, 1) #TODO
        self.SetSizer(sizer)


    def OnGetData(self, e):
        self.statusbar.SetStatusText('Welcome to Nesi - ' + 'Connecting to Tranquility...')
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
        installerIDs = []
        for row in dataNodes:
            if row.getAttribute(u'completed') == '0': # Ignore Delivered Jobs
                if row.getAttribute(u'installedItemTypeID') not in itemIDs:
                    itemIDs.append(row.getAttribute(u'installedItemTypeID'))
                if row.getAttribute(u'installerID') not in installerIDs:
                    installerIDs.append(row.getAttribute(u'installerID'))
                rows.append(Job(row.getAttribute(u'jobID'),
                                row.getAttribute(u'completedStatus'),
                                row.getAttribute(u'activityID'),
                                row.getAttribute(u'installedItemTypeID'),
                                row.getAttribute(u'installerID'),
                                row.getAttribute(u'installTime'),
                                row.getAttribute(u'endProductionTime')))



        print iid2name(itemIDs)
        print cid2name(installerIDs)


        self.myOlv.SetObjects(rows)


    def OnConfig(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog(self, 'Configure Nesi #TODO', 'Configure Nesi', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.


    def OnAbout(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        about_text = 'Nova Echo Science & Industry\n\nA tool to see your queues while out of game.\n\nCreated By: Tim Cumming aka Elusive One\nCopyright (C) 2013'
        dlg = wx.MessageDialog(self, about_text, 'About Nesi', wx.OK | wx.ICON_INFORMATION)
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
