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


class AutoComboBox(wx.ComboBox):  # FIXME: Why is this broken on Windoze?
    def __init__(self, parent, value, choices=[], style=0, **par):
        wx.ComboBox.__init__(self, parent, wx.ID_ANY, value, style=style | wx.CB_DROPDOWN, choices=choices, **par)
        self.choices = choices
        self.Bind(wx.EVT_CHAR, self.EvtChar)
        self.Bind(wx.EVT_TEXT, self.EvtText)

    def EvtChar(self, event):
        event.Skip()

    def EvtText(self, event):
        currentText = str(event.GetString()).lower()
        found = False
        newChoices = []

        # If the user has deleted the text reset to the whole list.
        if len(currentText) == 0:
            self.Clear()
            self.AppendItems(self.choices)

        # After the user inputs 3 or more characters search for matches.
        if len(currentText) >= 3:
            for choice in self.choices:
                # Check entered text at start and within string of choices.
                if (choice.lower().find(currentText) > 0) or (choice.lower().startswith(currentText)):
                    newChoices.append(choice)
                    found = True

        if found:
            self.Clear()
            self.AppendItems(newChoices)
        else:
            event.Skip()

# end of class AutoComboBox
