# -*- coding: utf-8 -*-

__author__      = "Saulius Lukse"
__copyright__   = "Copyright 2016, kurokesu.com"
__version__ = "0.1"
__license__ = "GPL"


import sys
import os
from PyQt4 import QtGui, uic
import time
import threading
import Queue
import LV8044LP_lib as lens


if os.name == 'nt':
    from serial.tools.list_ports_windows import *
elif sys.platform == 'darwin':
    from serial.tools.list_ports_osx import *
    from serial.tools.list_ports_vid_pid_osx_posix import *
elif os.name == 'posix':
    from serial.tools.list_ports_posix import *
    from serial.tools.list_ports_vid_pid_osx_posix import *
else:
    raise ImportError("Serial error: no implementation for your platform ('%s') available" % (os.name,))


form_class = uic.loadUiType("gui.ui")[0]
ser = serial.Serial()
q = Queue.Queue()
qs = Queue.Queue()
img_q = Queue.Queue()
pos_zoom = 0
pos_focus = 0
speed = 30
max_zoom = 5500
max_focus = 2100 
l = None
running = True


def build_m99(val):
    ret = 'M99 R'
    val = lens.reverse(val)
    ret += str(val)
    return ret


class MyWindowClass(QtGui.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.btn_connect.clicked.connect(self.btn_connect_clicked)
        self.btn_disconnect.clicked.connect(self.btn_disconnect_clicked)
        self.btn_initlens.clicked.connect(self.btn_initlens_clicked)
        self.btn_powersave.clicked.connect(self.btn_powersave_clicked)

        self.dial_zoom.valueChanged.connect(self.zoom_adjust)
        self.dial_focus.valueChanged.connect(self.focus_adjust)

        self.group_special.setEnabled(False)
        self.group_controls.setEnabled(False)
        self.btn_disconnect.setEnabled(False)

        self.dial_focus.setMaximum(max_focus)
        self.dial_zoom.setMaximum(max_zoom)

        self.combo_ports.clear()
        com_ports = sorted(comports())
        for port, desc, hwid in com_ports:
            self.combo_ports.addItem(port)

    def btn_initlens_clicked(self):
        global l
        qs.put(build_m99(l.ch12_1(mode=lens.e_mode.PHASE_4W, current=lens.e_current.C_67)))
        qs.put(build_m99(l.ch34_1(mode=lens.e_mode.PHASE_4W, current=lens.e_current.C_67, pwm_microstep=lens.e_pwm_microstep.MICROSTEP)))
        qs.put(build_m99(l.ch12_2(direction=lens.e_direction.CCW, hold=lens.e_hold.CANCEL, counter_reset=lens.e_counter.CANCEL, output=lens.e_output.ON)))
        qs.put(build_m99(l.ch34_2(direction=lens.e_direction.CCW, hold=lens.e_hold.CANCEL, counter_reset=lens.e_counter.CANCEL, output=lens.e_output.ON)))
        qs.put('G0 X'+str(max_zoom*10)+' F'+str(speed))
        qs.put('G0 Y'+str(max_focus*10)+' F'+str(speed))

    def btn_powersave_clicked(self):
        global l
        qs.put(build_m99(l.ch12_2(output=lens.e_output.OFF)))
        qs.put(build_m99(l.ch34_2(output=lens.e_output.OFF)))

    def btn_connect_clicked(self):
        global ser
        global l
        try:
            ser.port = str(self.combo_ports.currentText())
            ser.baudrate = 115200
            ser.timeout = 2
            ser.open()
            ser.flushInput()
            ser.flushOutput()

        except Exception, e:
            reply = QtGui.QMessageBox.warning(self, 'Serial port error', str(e))
            return 0

        l = lens.LV8044()
        self.group_special.setEnabled(True)
        self.group_controls.setEnabled(True)
        self.btn_connect.setEnabled(False)
        self.combo_ports.setEnabled(False)
        self.btn_disconnect.setEnabled(True)

    def btn_disconnect_clicked(self):
        self.group_special.setEnabled(False)
        self.group_controls.setEnabled(False)
        ser.close()
        self.btn_connect.setEnabled(True)
        self.combo_ports.setEnabled(True)
        self.btn_disconnect.setEnabled(False)

    def zoom_adjust(self):
        value = self.dial_zoom.value()
        self.label_zoom.setText(str(value))
        cmd = {}
        cmd["ch"] = "zoom"
        cmd["val"] = value
        q.put(cmd)

    def focus_adjust(self):
        value = self.dial_focus.value()
        self.label_focus.setText(str(value))
        cmd = {}
        cmd["ch"] = "focus"
        cmd["val"] = value
        q.put(cmd)

    def closeEvent(self, event):
        global running
        running = False


def receiver():
    global pos_zoom
    global pos_focus

    val_zoom = 0
    val_focus = 0

    while running:
        while not q.empty():
            dataq = q.get()

            if dataq['ch'] == 'zoom':
                val_zoom = dataq['val']

            if dataq['ch'] == 'focus':
                val_focus = dataq['val']

        diff_zoom = (val_zoom - pos_zoom)
        if diff_zoom > 0:
            qs.put(build_m99(l.ch12_2(direction=lens.e_direction.CW, output=lens.e_output.ON)))
        if diff_zoom < 0:
            qs.put(build_m99(l.ch12_2(direction=lens.e_direction.CCW, output=lens.e_output.ON)))
        steps_zoom = abs(diff_zoom*10)
        qs.put('G0 X'+str(steps_zoom)+' F'+str(speed))  # go to 0
        pos_zoom = val_zoom

        diff_focus = (val_focus - pos_focus)       
        if diff_focus > 0:
            qs.put(build_m99(l.ch34_2(direction=lens.e_direction.CW, output=lens.e_output.ON)))
        if diff_focus < 0:
            qs.put(build_m99(l.ch34_2(direction=lens.e_direction.CCW, output=lens.e_output.ON)))

        steps_focus = abs(diff_focus*10)
        qs.put('G0 Y'+str(steps_focus)+' F'+str(speed)) # go to 0
        pos_focus = val_focus
        time.sleep(0.1)


def serial_sender():
    global ser
    while running:
        if ser.isOpen():
            dataqs = qs.get()
            if dataqs:
                ser.write(dataqs+'\n')
                rd = ser.readline()


threading.Thread(target=receiver).start()
threading.Thread(target=serial_sender).start()
app = QtGui.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
