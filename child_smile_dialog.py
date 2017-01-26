#! /usr/bin/python

# ########################################################################### #
# #                                                                         # #
# # Copyright (c) 2009-2016 Neil Wallace <neil@openmolar.com>               # #
# #                                                                         # #
# # This file is part of OpenMolar.                                         # #
# #                                                                         # #
# # OpenMolar is free software: you can redistribute it and/or modify       # #
# # it under the terms of the GNU General Public License as published by    # #
# # the Free Software Foundation, either version 3 of the License, or       # #
# # (at your option) any later version.                                     # #
# #                                                                         # #
# # OpenMolar is distributed in the hope that it will be useful,            # #
# # but WITHOUT ANY WARRANTY; without even the implied warranty of          # #
# # MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           # #
# # GNU General Public License for more details.                            # #
# #                                                                         # #
# # You should have received a copy of the GNU General Public License       # #
# # along with OpenMolar.  If not, see <http://www.gnu.org/licenses/>.      # #
# #                                                                         # #
# ########################################################################### #

from gettext import gettext as _
import logging
import re
import socket
import urllib.request
import urllib.error
import urllib.parse
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

LOGGER = logging.getLogger("soe")
LOOKUP_URL = "http://www.psd.scot.nhs.uk/dev/simd/simdLookup.aspx"

class Folder:
    '''
    class to ensure vim folds this clutter
    '''
    # here is an example result of a lookup using this
    EXAMPLE_RESULT = '''
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head><title>
    SIMD Lookup for PSD
    </title></head>
    <body>
        <form method="post" action="simdLookup.aspx?_=1348071532912&amp;pCode=IV2+5XQ" id="form1">
    <input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="/wEPDwUJODExMDE5NzY5D2QWAgIDD2QWAgIBDw8WAh4EVGV4dAUMU0lNRCBBcmVhOiA0ZGRkXUm1+PLLKbrXDulhPdHkxpJgof6hEmrnSC3uCZiOeQ0=" />
        <div>
            <span id="simd">SIMD Area: 4</span>
        </div>
        </form>
    </body>
    </html>
    '''

    HEADERS = {
        'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 '
                       '(KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'),
        'Accept':
            'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'}

    # AGE 0-2
    # ohi by dentist = 4103
    # dietary advice by dentist = 4105
    # ohi by dcp = 4104
    # dietary advice by dcp = 4106
    # simd 1-3 claim 4101 £16.34
    # simd 4+5 claim 4102 £5.36

    # AGE 3-5
    # ohi by dentist = 4107
    # dietary advice by dentist = 4109
    # ohi by dcp = 4108
    # dietary advice by dcp = 4110
    # simd 1-3 claim 4111 £5.36

    # AGE 2-5
    # Fluoride aplication
    # code 4407


    TEMPLATE = '''<html>
    <body>
    <h3>Age 0-2</h3>
    <table width="100%" border="1">
    <tr>
    <th>Code</th>
    <th>Description</th>
    <th>Fee</th>
    </tr>
    <tr>
    <td align="center">
    4103
    </td>
    <td align="center">
    TB/OHI
    </td>
    <td align="center">
    &nbsp;
    </td>
    </tr>
    <tr>
    <td align="center">
    4105
    </td>
    <td align="center">
    Dietary Advice
    </td>
    <td align="center">
    </td>
    </tr>
    <tr>
    <td align="center">
    4101
    </td>
    <td align="center">
    &nbsp;
    </td>
    <td align="center">
    SIMD_FEE1
    </td>
    </tr>
    </table>
    <h3>Age 2-5</h3>
    <table width="100%" border="1">
    <tr>
    <th>Code</th>
    <th>Description</th>
    <th>Fee</th>
    </tr>
    <tr>
    <td align="center">
    4407
    </td>
    <td align="center">
    Fluoride Application
    </td>
    <td align="center">
    &pound;6.40
    </td>
    </tr>
    </table>
    <h3>Age 3-5</h3>
    <table width="100%" border="1">
    <tr>
    <th>Code</th>
    <th>Description</th>
    <th>Fee</th>
    </tr>
    <tr>
    <td align="center">
    4107
    </td>
    <td align="center">
    TB/OHI
    </td>
    <td align="center">
    &nbsp;
    </td>
    </tr>
    <tr>
    <td align="center">
    4109
    </td>
    <td align="center">
    Dietary Advice
    </td>
    <td align="center">
    </td>
    </tr>
    <!--SIMD_ROW-->
    </table>
    </body>
    </html>'''

    SIMD_ROW = '''<tr>
    <td align="center">
    4111
    </td>
    <td align="center">
    &nbsp;
    </td>
    <td align="center">
    &pound;5.36
    </td>
    </tr>'''


HEADERS = Folder.HEADERS
TEMPLATE = Folder.TEMPLATE
SIMD_ROW = Folder.SIMD_ROW


class UpperCaseLineEdit(QtWidgets.QLineEdit):

    '''
    A custom line edit that accepts only BLOCK LETTERS.
    '''

    def setText(self, text):
        QtWidgets.QLineEdit.setText(self, text.upper())

    def keyPressEvent(self, event):
        '''
        convert the text to upper case, and pass the signal on to the
        base widget
        '''
        if 65 <= event.key() <= 90:
            event = QtGui.QKeyEvent(event.type(), event.key(),
                                    event.modifiers(), event.text().upper())
        QtWidgets.QLineEdit.keyPressEvent(self, event)



class ChildSmileDialog(QtWidgets.QMainWindow):
    LOOKUPS = {}
    result = ""
    is_checking_website = False
    _simd = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("ChildSmile Lookup"))

        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout_ = QtWidgets.QGridLayout(central_widget)

        header_label = QtWidgets.QLabel()
        header_label.setText(_("Please enter a valid postcode"))
        self.pcde_le = UpperCaseLineEdit()
        self.result_label = QtWidgets.QLabel()
        self.result_label.setAlignment(QtCore.Qt.AlignCenter)
        tab_widget = QtWidgets.QTabWidget()

        self.dent_label = QtWidgets.QLabel()
        tab_widget.addTab(self.dent_label, _("Dentist Codes"))
        self.hyg_label = QtWidgets.QLabel()
        tab_widget.addTab(self.hyg_label, _("DCP Codes"))

        layout_.addWidget(header_label, 0, 0)
        layout_.addWidget(self.pcde_le, 0, 1)
        layout_.addWidget(self.result_label, 1, 0, 1, 2)
        layout_.addWidget(tab_widget, 2, 0, 1, 2)

        self.pcde_le.textEdited.connect(self.check_pcde)

    def sizeHint(self):
        '''
        Overwrite this function inherited from QWidget
        '''
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        '''
        Overwrite this function inherited from QWidget
        '''
        return QtCore.QSize(400, 500)

    @property
    def pcde(self):
        try:
            return str(self.pcde_le.text())
        except:
            return ""

    @property
    def valid_postcode(self):
        return bool(re.match(r"[A-Z][A-Z]?(\d+) (\d+)[A-Z][A-Z]$", self.pcde))

    def postcode_warning(self):
        if not self.valid_postcode:
            QtWidgets.QMessageBox.warning(self, _("Error"),
                                          _("Postcode is not valid"))

    def check_pcde(self):
        if self.valid_postcode:
            QtCore.QTimer.singleShot(50, self.simd_lookup)
        else:
            self.result_label.setText("")
            self.dent_label.setText("")
            self.hyg_label.setText("")

    def simd_lookup(self):
        '''
        poll the server for a simd for a postcode
        '''
        self._simd = None
        self.dent_label.setText("")
        self.hyg_label.setText("")
        QtWidgets.QApplication.instance().processEvents()
        try:
            self.result = "SIMD: %s" % self.LOOKUPS[self.pcde]
            LOGGER.debug("simd_lookup unnecessary, value known")
        except KeyError:
            self.result_label.setText(_("Polling psd.scot.nhs.uk"))
            QtWidgets.QApplication.instance().processEvents()

            pcde = self.pcde.replace(" ", "%20")
            url = "%s?pCode=%s" % (LOOKUP_URL, pcde)

            try:
                QtWidgets.QApplication.instance().setOverrideCursor(
                    QtCore.Qt.WaitCursor)
                req = urllib.request.Request(url, headers=HEADERS)
                response = urllib.request.urlopen(req, timeout=20)
                result = response.read()
                self.result = self._parse_result(result)
                if self.simd_number is not None:
                    self.LOOKUPS[self.pcde] = self.simd_number
            except urllib.error.URLError:
                LOGGER.error("url error polling NHS website?")
                self.result = _("Error polling website")
            except socket.timeout:
                LOGGER.error("timeout error polling NHS website?")
                self.result = _("Timeout polling website")
            finally:
                QtWidgets.QApplication.instance().restoreOverrideCursor()

        self.result_label.setText(
            "%s %s = <b>%s</b>" % (_("Postcode"),
                                self.pcde,
                                self.result))
        QtWidgets.QApplication.instance().processEvents()
        self.update_code_labels()

    def _parse_result(self, result):
        try:
            dom = minidom.parseString(result)
            e = dom.getElementsByTagName("span")[0]
            return e.firstChild.data
        except ExpatError:
            return "UNDECIPHERABLE REPLY"

    def update_code_labels(self):
        dent_html = TEMPLATE

        if self.simd_number is None:
            return
        elif self.simd_number in (1,2,3):
            dent_html = dent_html.replace(
                "SIMD_FEE1", "&pound;16.34").replace(
                    "<!--SIMD_ROW-->", SIMD_ROW)
        else:
            dent_html = dent_html.replace("SIMD_FEE1", "&pound;5.36")

        hyg_html = dent_html
        for dcode, hcode in (('4103', '4104'),
                             ('4105', '4106'),
                             ('4107', '4108'),
                             ('4109', '4110')):
            hyg_html = hyg_html.replace(dcode, hcode)


        self.dent_label.setText(dent_html)
        self.hyg_label.setText(hyg_html)

    @property
    def simd_number(self):
        if self._simd is None:
            m = re.search("(\d+)", self.result)
            if m:
                self._simd = int(m.groups()[0])
        return self._simd


if __name__ == "__main__":
    LOGGER.setLevel(logging.DEBUG)

    app = QtWidgets.QApplication([])
    mw = ChildSmileDialog()
    mw.show()
    app.exec_()
