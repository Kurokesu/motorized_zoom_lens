# -*- coding: utf-8 -*-

__author__      = "Saulius Lukse"
__copyright__   = "Copyright 2016, kurokesu.com"
__version__ = "0.3"
__license__ = "GPL"


'''
Changelog
=========

v0.2
----
* initlal up and running version

v0.3
----
* Read realtime lens position
* Save value to json on exit
* Remove init lens and power save buttons. Not needed any more
* Load settings on boot, set dials to correct position
* add camera view / 640x480 @ 30fps? / some issues setting to MJPG mode

'''

import sys
import os
from PyQt4 import QtGui, uic, QtCore
import time
import threading
import Queue
import utils
import cv2
import numpy as np


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
q_labels = Queue.Queue()
#img_q = Queue.Queue()
pos_zoom = 0
pos_focus = 0
speed = 30
max_zoom = 55000
max_focus = 21000
running = True
json_file = 'settings.json'
config = {}
boot_sequence = True
video_running = False
capture_thread = None
q_video = Queue.Queue()


config = utils.json_boot_routine(json_file)


def grab(cam, queue, width, height, fps):
    global running
    capture = cv2.VideoCapture(cam)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    capture.set(cv2.CAP_PROP_FPS, fps)

    while(running):
        frame = {}        
        capture.grab()
        retval, img = capture.retrieve(0)
        frame["img"] = img
        #print '.',

        if queue.qsize() < 10:
            queue.put(frame)
        else:
            print queue.qsize()

class OwnImageWidget(QtGui.QWidget):
    def __init__(self, parent=None):
        super(OwnImageWidget, self).__init__(parent)
        self.image = None

    def setImage(self, image):
        self.image = image
        sz = image.size()
        self.setMinimumSize(sz)
        self.update()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        if self.image:
            qp.drawImage(QtCore.QPoint(0, 0), self.image)
        qp.end()


class MyWindowClass(QtGui.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.btn_video.clicked.connect(self.start_video_clicked)

        self.btn_connect.clicked.connect(self.btn_connect_clicked)
        #self.btn_disconnect.clicked.connect(self.btn_disconnect_clicked)

        self.dial_zoom.valueChanged.connect(self.zoom_adjust)
        self.dial_focus.valueChanged.connect(self.focus_adjust)

        self.group_controls.setEnabled(False)
        #self.btn_disconnect.setEnabled(False)

        self.dial_focus.setMaximum(max_focus)
        self.dial_zoom.setMaximum(max_zoom)

        # setup video timer and widget
        w = self.widget_video.width() 
        h = self.widget_video.height() 
        self.widget_video = OwnImageWidget(self.widget_video)
        self.widget_video.resize(w, h)



        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)


        self.combo_ports.clear()
        com_ports = sorted(comports())
        for port, desc, hwid in com_ports:
            self.combo_ports.addItem(port)

        self.timer1 = QtCore.QTimer(self)
        self.timer1.timeout.connect(self.update_pos)
        self.timer1.start(1)


    def update_frame(self):
        if not q_video.empty():
            self.btn_video.setText('Camera is live')
            frame = q_video.get()
            img = frame["img"]

            img_height, img_width, img_colors = img.shape


            scale_w = float(self.widget_video.width()) / float(img_width)
            scale_h = float(self.widget_video.height()) / float(img_height)
            scale = min([scale_w, scale_h])

            if scale == 0:
                scale = 1
            
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation = cv2.INTER_CUBIC)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width, bpc = img.shape
            bpl = bpc * width
            image = QtGui.QImage(img.data, width, height, bpl, QtGui.QImage.Format_RGB888)
            self.widget_video.setImage(image)

    def start_video_clicked(self):
        global video_running
        video_running = True
        capture_thread.start()
        self.btn_video.setEnabled(False)
        self.btn_video.setText('Starting...')


    def update_pos(self):
        global boot_sequence
        if not q_labels.empty():
            f = q_labels.get()
            if not boot_sequence:
                self.label_focus_real.setText(f["1"])
                self.label_zoom_real.setText(f["2"])
            else:
                # Send command to adjust offset to controller
                cmd = 'G92 X'+str(config["1"])+' Y'+str(config["2"])+'\n'
                ser.write(cmd)

                # update dials
                self.dial_zoom.setValue(int(config["1"]))
                self.dial_focus.setValue(int(config["2"]))

                # enable dials
                self.dial_zoom.setEnabled(True)
                self.dial_focus.setEnabled(True)
                boot_sequence = False



    def btn_connect_clicked(self):
        global ser
        try:
            ser.port = str(self.combo_ports.currentText())
            ser.baudrate = 115200
            ser.timeout = 2
            ser.open()
            ser.flushInput()
            ser.flushOutput()
            config["port"] = str(self.combo_ports.currentText())

        except Exception, e:
            reply = QtGui.QMessageBox.warning(self, 'Serial port error', str(e))
            return 0

        self.group_controls.setEnabled(True)
        self.btn_connect.setEnabled(False)
        self.combo_ports.setEnabled(False)
        self.dial_zoom.setEnabled(False)
        self.dial_focus.setEnabled(False)

    def zoom_adjust(self):
        value = self.dial_zoom.value()
        self.label_zoom.setText(str(value))
        cmd = 'G0 X'+str(value)+'\n'
        ser.write(cmd)

    def focus_adjust(self):
        value = self.dial_focus.value()
        self.label_focus.setText(str(value))
        cmd = 'G0 Y'+str(value)+'\n'
        ser.write(cmd)

    def closeEvent(self, event):
        global config
        global running
        if not boot_sequence:
            utils.json_exit_routine(json_file, config)
        running = False


def serial_sender():
    global ser  

    line_old = None 
    while running:
        if ser.isOpen():
            try:
                rd = ser.readline()
                line = rd.rstrip()
                if line != line_old:
                    feedback = {}
                    line_2 = line.split(',')
                    for l in line_2:
                        l_s = l.split("=")
                        if len(l_s) == 2:
                            feedback[str(l_s[0])] = l_s[int(1)]
                    
                    q_labels.put(feedback)

                    if not boot_sequence:
                        config["1"] = feedback["1"]
                        config["2"] = feedback["2"]

                line_old = line
            except:
                pass


capture_thread = threading.Thread(target=grab, args = (0, q_video, 640, 360, 30))
threading.Thread(target=serial_sender).start()
app = QtGui.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
