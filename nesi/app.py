#!/usr/bin/python
"""Nova Echo Science & Industry"""
# Copyright (C) 2015  Tim Cumming
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
# Created: 11/01/15
# Modified: 17/01/15

import kivy
kivy.require('1.8.0')
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.gridlayout import GridLayout

# import datetime

import config

from nesi.api import getServerStatus
from nesi.functions import updateCurrentTime
from nesi.classes import Character

Builder.load_file('nesi/statusbar.kv')


# TODO: Change to JSON and use kivy.storage.jsonstore
import os.path
import pickle
# Lets try to load up our API keys from the ini file.
# This requires the Pilot class to work.
if (os.path.isfile('../nesi.ini')):
    iniFile = open('../nesi.ini', 'r')
    config.pilotRows = pickle.load(iniFile)
    iniFile.close()


class RootWidget(GridLayout):
    '''This the class representing your root widget.
       By default it is inherited from BoxLayout,
       you can use any other layout/widget depending on your usage.
    '''
    def fetch_jobs(self):
        print('fetch_jobs called')

        # Update the config.serverTime to now.
        updateCurrentTime()

        # getServerStatus(config.serverStatus, config.serverTime, self.status_bar)
        getServerStatus(config.serverConn.svrCacheExpire, config.serverTime, self.status_bar)


class NesiApp(App):
    title = 'Nesi'
    '''This is the main class of your app.
       Define any app wide entities here.
       This class can be accessed anywhere inside the kivy app as,
       in python::

         app = App.get_running_app()
         print (app.title)

       in kv language::

         on_release: print(app.title)
       Name of the .kv file that is auto-loaded is derived from the name of this cass::

         MainApp = main.kv
         MainClass = mainclass.kv

       The App part is auto removed and the whole name is lowercased.
    '''

    def build(self):
        '''Your app will be build from here.
           Return your root widget here.
        '''
        return RootWidget()

    def on_pause(self):
        '''This is necessary to allow your app to be paused on mobile os.
           refer http://kivy.org/docs/api-kivy.app.html#pause-mode .
        '''
        return True
