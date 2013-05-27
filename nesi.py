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
        
# S&I window shows: state, activity, type, location, jumps, installer, owner, install date, end date

#columns="jobID,assemblyLineID,containerID,installedItemID,installedItemLocationID,installedItemQuantity,installedItemProductivityLevel,
#installedItemMaterialLevel,installedItemLicensedProductionRunsRemaining,outputLocationID,installerID,runs,licensedProductionRuns,
#installedInSolarSystemID,containerLocationID,materialMultiplier,charMaterialMultiplier,timeMultiplier,charTimeMultiplier,
#installedItemTypeID,outputTypeID,containerTypeID,installedItemCopy,completed,completedSuccessfully,installedItemFlag,
#outputFlag,activityID,completedStatus,installTime,beginProductionTime,endProductionTime,pauseProductionTime"


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
        menuAbout= filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar.
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Menu events.
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
 
        #https://api.eveonline.com/eve/CharacterName.xml.aspx?ids=xxxxx,xxxxx
        #
        #https://api.eveonline.com/eve/TypeName.xml.aspx?ids=xxxxx
 
        #Download the Account Industry Data
        apiURL = 'http://api.eveonline.com/corp/IndustryJobs.xml.aspx?keyID=%s&vCode=%s&characterID=%s' % (keyID, vCode, characterID)
        print apiURL

        #download the file:
        #target = urllib2.urlopen(apiURL)
        
        #open a local xml file for reading: (testing)
        target = open('IndustryJobs.xml','r')

        #convert to string:
        downloadedData = target.read()

        #close file because we don't need it anymore:
        target.close()

        XMLData = parseString(downloadedData)
#        headerNode = XMLData.getElementsByTagName("rowset")[0]
#        columnHeaders = headerNode.attributes['columns'].value.split(',')
        dataNodes = XMLData.getElementsByTagName("row")

        rows = []
        for row in dataNodes:
            if row.getAttribute(u'completed') == '0': # Ignore Delivered Jobs
                rows.append(Job(row.getAttribute(u'jobID'),
                                row.getAttribute(u'completedStatus'),
                                row.getAttribute(u'activityID'),
                                row.getAttribute(u'installedItemTypeID'),
                                row.getAttribute(u'installerID'),
                                row.getAttribute(u'installTime'),
                                row.getAttribute(u'beginProductionTime'),
                                row.getAttribute(u'endProductionTime')))

        
        self.myOlv = ObjectListView(self, -1, style=wx.LC_REPORT|wx.SUNKEN_BORDER)

        self.myOlv.SetColumns([
            ColumnDefn("jobID", "left", 100, "jobID"),
            ColumnDefn("completedStatus", "left", 100, "completedStatus"),
            ColumnDefn("activityID", "left", 100, "activityID"),
            ColumnDefn("installedItemTypeID", "center", 200, "installedItemTypeID"),
            ColumnDefn("installerID", "center", 150, "installerID"),
            ColumnDefn("Install Time", "left", 120, "installTime", stringConverter="%Y-%m-%d %H:%M"),
            ColumnDefn("Start Time", "left", 120, "beginProductionTime", stringConverter="%Y-%m-%d %H:%M"),
            ColumnDefn("End Time", "left", 120, "endProductionTime", stringConverter="%Y-%m-%d %H:%M")
        ])
        self.myOlv.SetObjects(rows)
 
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.myOlv, 1, wx.ALL|wx.EXPAND, 4)
        self.SetSizer(sizer)

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
