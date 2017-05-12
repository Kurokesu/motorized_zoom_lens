#! /usr/bin/env python3

# -*- coding: utf-8 -*-

__author__ = "Saulius Lukse"
__copyright__ = "Copyright 2016-2017, kurokesu.com"
__version__ = "0.5"
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

v0.4
----
* basic software autofocus implementation

v0.5
----
* Converted to PyQt5 by Nick Zanobini

'''

import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic
import threading
import queue
import utils
import cv2


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
q = queue.Queue()
q_labels = queue.Queue()
max_2 = 32000
max_1 = 42000
focus_backlash = -500

autofocus_step = 200
autofocus_best = 0

running = True
json_file = 'settings.json'
config = {}
boot_sequence = True
video_running = False
capture_thread = None
q_video = queue.Queue()

autofocus_state = 0
focus_data = []


config = utils.json_boot_routine(json_file)


def get_blur(frame, scale):
    frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return fm


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
        frame["1"] = config["1"]
        frame["2"] = config["2"]

        blur = get_blur(img, 0.05)
        frame["blur"] = blur

        if queue.qsize() < 10:
            queue.put(frame)
        else:
            print(queue.qsize())


class OwnImageWidget(QtWidgets.QWidget):
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


class MyWindowClass(QtWidgets.QMainWindow, form_class):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.btn_video.clicked.connect(self.start_video_clicked)
        self.btn_autofocus.setEnabled(False)

        self.push_zero.clicked.connect(self.zero_clicked)
        self.push_zero.setEnabled(False)

        self.btn_connect.clicked.connect(self.btn_connect_clicked)
        self.btn_autofocus.clicked.connect(self.btn_autofocus_clicked)

        self.dial_2.valueChanged.connect(self.adjust_1)
        self.dial_1.valueChanged.connect(self.adjust_2)

        self.group_controls.setEnabled(False)

        self.dial_2.setMaximum(max_1)
        self.dial_1.setMaximum(max_2)

        # setup video timer and widget
        w = self.widget_video.width()
        h = self.widget_video.height()
        self.widget_video = OwnImageWidget(self.widget_video)
        self.widget_video.resize(w, h)

        # setup update frame thread
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)

        # setup com port comunication
        self.combo_ports.clear()
        com_ports = sorted(comports())
        for port, desc, hwid in com_ports:
            self.combo_ports.addItem(port)

        self.timer1 = QtCore.QTimer(self)
        self.timer1.timeout.connect(self.update_pos)
        self.timer1.start(1)

    def zero_clicked(self):
        cmd = 'G92 X0 Y0\n'
        ser.write(bytes(cmd, 'utf8'))

    def update_frame(self):
        global autofocus_state
        global autofocus_best
        global focus_data

        if not q_video.empty():
            self.btn_video.setText('Camera is live')
            # self.btn_autofocus.setEnabled(True)
            frame = q_video.get()
            img = frame["img"]
            # print frame["1"], frame["2"]

            img_height, img_width, img_colors = img.shape

            scale_w = float(self.widget_video.width()) / float(img_width)
            scale_h = float(self.widget_video.height()) / float(img_height)
            scale = min([scale_w, scale_h])

            if scale == 0:
                scale = 1

            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width, bpc = img.shape
            bpl = bpc * width
            image = QtGui.QImage(img.data, width, height, bpl, QtGui.QImage.Format_RGB888)
            self.widget_video.setImage(image)

            blur = frame["blur"]
            self.label_blur.setText('%d' % blur)
            self.progress_focus.setValue(blur)

            # here starts autofocus code
            # --------------------------

            # just wait and do nothing
            if (autofocus_state == 1) and (int(frame["2"]) != 0):
                self.btn_autofocus.setText('Going to 0 focus point...')
                focus_data = []
                pass

            # swith to next state
            if (autofocus_state == 1) and (int(frame["2"]) == 0):
                autofocus_state = 2

            # collect data and move lens
            if (autofocus_state == 2) and (int(frame["2"]) < max_2):
                self.btn_autofocus.setText('Analyzing frames...')

                # save data
                metadata = frame
                metadata["img"] = None  # don't collect whole frame
                focus_data.append(metadata)

                # move lens
                value = self.dial_1.value()
                value += autofocus_step
                self.dial_1.setValue(value)

            if (autofocus_state == 2) and (int(frame["2"]) == max_2):
                autofocus_state = 3
                self.btn_autofocus.setText('Saving data...')
                # save collected data

            if (autofocus_state == 3):
                autofocus_state = 4
                max_focus_val = 0.0
                max_focus_pos = 0
                for frame in focus_data:
                    if max_focus_val < float(frame["blur"]):
                        max_focus_val = float(frame["blur"])
                        max_focus_pos = int(frame["2"])

                print(max_focus_val, max_focus_pos)
                autofocus_best = max_focus_pos + focus_backlash  # backlash in a lens

                self.btn_autofocus.setText('Analyzing data...')

            if (autofocus_state == 4):
                autofocus_state = 5
                self.dial_1.setValue(autofocus_best)
                self.btn_autofocus.setText('Moving to best spot...')

            if (autofocus_state == 5) and (int(frame["2"]) == autofocus_best):
                autofocus_state = 0
                self.btn_autofocus.setText('Autofocus')
                self.btn_autofocus.setEnabled(True)
                self.dial_2.setEnabled(True)
                self.dial_1.setEnabled(True)

            # self.label_temp.setText(str(len(focus_data)))
            # self.label_temp.setText(str(frame["1"]))

    def btn_autofocus_clicked(self):
        global autofocus_state

        if autofocus_state == 0:
            self.btn_autofocus.setEnabled(False)
            self.dial_2.setEnabled(False)
            self.dial_1.setEnabled(False)
            autofocus_state = 1
            # self.btn_autofocus.setText('Going to 0 focus point...')
            self.dial_1.setValue(0)  # change focus to 0

        '''
        start autofocus thread + state machine

        1 - set dial focus = 0
        2 - wait until feedback == 0
        3 - change focus slowly until feedback == max, collecta/analyze frames and save
        4 - analyze where is the best focus
        5 - goto 0
        6 - goto best focus position

        '''

    def start_video_clicked(self):
        global video_running
        video_running = True
        capture_thread.start()
        self.btn_video.setEnabled(False)
        self.btn_autofocus.setEnabled(True)
        self.btn_video.setText('Starting...')

    def update_pos(self):
        global boot_sequence
        if not q_labels.empty():
            f = q_labels.get()
            if not boot_sequence:
                self.label_2_real.setText(f["X"])
                self.label_1_real.setText(f["Y"])
            else:
                # Send command to adjust offset to controller
                cmd = 'G92 X' + str(config["1"]) + ' Y' + str(config["2"]) + '\n'
                ser.write(bytes(cmd, 'utf8'))

                # update dials
                self.dial_2.setValue(int(config["1"]))
                self.dial_1.setValue(int(config["2"]))

                # enable dials
                self.dial_1.setEnabled(True)
                self.dial_2.setEnabled(True)
                self.push_zero.setEnabled(True)
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

        except Exception as e:
            self.reply = QtWidgets.QMessageBox.warning(self, 'Serial port error', str(e))
            return 0

        self.group_controls.setEnabled(True)
        self.btn_connect.setEnabled(False)
        self.combo_ports.setEnabled(False)
        self.dial_1.setEnabled(False)
        self.dial_2.setEnabled(False)
        # self.push_zero.setEnabled(False)

    def adjust_2(self):
        value = self.dial_1.value()
        self.label_1.setText(str(value))
        cmd = 'G0 Y' + str(value) + '\n'
        ser.write(bytes(cmd, 'utf8'))

    def adjust_1(self):
        value = self.dial_2.value()
        self.label_2.setText(str(value))
        cmd = 'G0 X' + str(value) + '\n'
        ser.write(bytes(cmd, 'utf8'))

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
                rd = str(ser.readline())
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
                        config["1"] = feedback["X"]
                        config["2"] = feedback["Y"]

                line_old = line
            except e:
                pass


capture_thread = threading.Thread(target=grab, args=(0, q_video, 640, 360, 30))
threading.Thread(target=serial_sender).start()
app = QtWidgets.QApplication(sys.argv)
myWindow = MyWindowClass(None)
myWindow.show()
app.exec_()
