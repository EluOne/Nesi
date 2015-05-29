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
# Created: 31/01/15
# Modified: 29/05/15

from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout


def onError(error):

    content = BoxLayout(orientation="vertical")

    content.add_widget(Label(text=str(error), font_size=18))

    acknowledge = Button(text="Got It!", size_hint=(1, .20), font_size=18)
    content.add_widget(acknowledge)

    popup = Popup(content=content,
                  title='Something went wrong!',
                  auto_dismiss=False,
                  size_hint=(.7, .5),
                  font_size='18sp')

    acknowledge.bind(on_press=popup.dismiss)

    popup.open()

    print(error)
