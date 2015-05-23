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
# Modified: 22/05/15

import kivy
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager

kivy.require('1.8.0')

Builder.load_file('nesi/statusbar.kv')
Builder.load_file('nesi/jobstab.kv')
Builder.load_file('nesi/jobgrid.kv')
Builder.load_file('nesi/starbasestab.kv')
Builder.load_file('nesi/nesi.kv')
Builder.load_file('nesi/nesiscreenmanager.kv')


class NesiScreenManager(ScreenManager):
    pass


# class NesiApp(App):
class NesiScreenManagerApp(App):
    title = 'Nesi'

    def build(self):
        # return RootWidget()
        return NesiScreenManager()

    def on_pause(self):
        '''This is necessary to allow your app to be paused on mobile os.
           refer http://kivy.org/docs/api-kivy.app.html#pause-mode .
        '''
        return True

if __name__ == "__main__":
    NesiScreenManagerApp().run()
