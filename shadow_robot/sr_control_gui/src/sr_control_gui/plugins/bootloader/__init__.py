#!/usr/bin/env python
#
# Copyright 2011 Shadow Robot Company Ltd.
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import roslib; roslib.load_manifest('sr_control_gui')
import rospy

from generic_plugin import GenericPlugin
from sr_robot_msgs.srv import SimpleMotorFlasher, SimpleMotorFlasherResponse

from PyQt4 import QtCore, QtGui, Qt

class Motor(QtGui.QFrame):
    def __init__(self, parent, motor_name, motor_index):
        QtGui.QFrame.__init__(self, parent)

        self.motor_name = motor_name
        self.motor_index = motor_index

        self.layout = QtGui.QHBoxLayout()

        self.checkbox = QtGui.QCheckBox("", self)
        self.layout.addWidget(self.checkbox)

        self.label = QtGui.QLabel( motor_name + ": " + str(motor_index) )
        self.layout.addWidget(self.label)

        self.setLayout(self.layout)

class Bootloader(GenericPlugin):
    """
    Bootload the given firmware into the selected motors.
    """
    name = "Bootloader"

    def __init__(self):
        GenericPlugin.__init__(self)

        self.firmware_path = None

        self.frame = QtGui.QFrame()
        self.layout = QtGui.QVBoxLayout()

        self.file_frame = QtGui.QFrame()
        self.file_layout = QtGui.QHBoxLayout()

        self.file_btn = QtGui.QPushButton()
        self.file_btn.setText("Choose Firmware")
        self.file_btn.setToolTip("Choose which compiled firmware you want to load.")
        self.file_frame.connect(self.file_btn, QtCore.SIGNAL('clicked()'),self.choose_firmware)
        self.file_layout.addWidget(self.file_btn)

        self.file_label = QtGui.QLabel("No firmware chosen")
        self.file_layout.addWidget(self.file_label)

        self.file_frame.setLayout(self.file_layout)
        self.layout.addWidget(self.file_frame)

        self.motors_frame = QtGui.QFrame()
        self.motors_layout = QtGui.QGridLayout()

        self.motors = []
        self.motors_frame.setLayout(self.motors_layout)
        self.layout.addWidget(self.motors_frame)

        self.all_selected = False
        self.select_all_btn =  QtGui.QPushButton()
        self.select_all_btn.setText("Select/Deselect All")
        self.select_all_btn.setToolTip("Select or deselect all motors.")
        self.file_frame.connect(self.select_all_btn, QtCore.SIGNAL('clicked()'),self.select_all)
        self.layout.addWidget(self.select_all_btn)

        self.program_frame = QtGui.QFrame()
        self.program_layout = QtGui.QHBoxLayout()

        self.program_btn = QtGui.QPushButton()
        self.program_btn.setText("Program Motors")
        self.program_btn.setToolTip("Program the selected motors with the choosen firmware")
        self.program_btn.setEnabled(False)

        self.program_frame.connect(self.program_btn, QtCore.SIGNAL('clicked()'),self.program_motors)
        self.program_layout.addWidget(self.program_btn)

        self.progress_bar = QtGui.QProgressBar()
        self.program_layout.addWidget(self.progress_bar)

        self.program_frame.setLayout(self.program_layout)
        self.layout.addWidget(self.program_frame)

        self.frame.setLayout(self.layout)
        self.window.setWidget(self.frame)

    def choose_firmware(self):
        filename = QtGui.QFileDialog.getOpenFileName(self.file_frame, Qt.QString("Firmware file"), Qt.QString(""), Qt.QString("*.hex") )
        if filename == "":
            if self.firmware_path == None:
                self.program_btn.setEnabled(False)
            return
        self.firmware_path = filename
        self.file_label.setText(filename.split("/")[-1])
        self.program_btn.setEnabled(True)

    def select_all(self):
        if self.all_selected:
            for motor in self.motors:
                motor.checkbox.setCheckState( QtCore.Qt.Unchecked )
                self.all_selected = False
        else:
            for motor in self.motors:
                motor.checkbox.setCheckState( QtCore.Qt.Checked )
                self.all_selected = True

    def program_motors(self):
        self.progress_bar.setValue(0)
        nb_motors_to_program = 0.
        for motor in self.motors:
            if motor.checkbox.checkState() == QtCore.Qt.Checked:
                nb_motors_to_program += 1.
        if nb_motors_to_program == 0.:
            QtGui.QMessageBox.warning(self.frame, "Warning", "No motors selected for flashing.")
            return

        rospy.wait_for_service('SimpleMotorFlasher')
        flasher_service = rospy.ServiceProxy('SimpleMotorFlasher', SimpleMotorFlasher)

        programmed_motors = 0.
        for motor in self.motors:
            if motor.checkbox.checkState() == QtCore.Qt.Checked:
                resp = SimpleMotorFlasherResponse.FAIL
                try:
                    print self.firmware_path
                    resp = flasher_service(str( self.firmware_path ), motor.motor_index)
                except rospy.ServiceException, e:
                    QtGui.QMessageBox.warning(self.frame, "Warning", "Service did not process request: %s"%str(e))

                if resp == SimpleMotorFlasherResponse.FAIL:
                    QtGui.QMessageBox.warning(self.frame, "Warning", "Failed to bootload motor: "+str(motor.motor_name) )

                programmed_motors += 1.
                self.progress_bar.setValue(programmed_motors / nb_motors_to_program * 100.)

    def populate_motors(self):
        if rospy.has_param("joint_to_motor_mapping"):
            joint_to_motor_mapping = rospy.get_param("joint_to_motor_mapping")

        joint_names = [ ["FFJ0", "FFJ1", "FFJ2", "FFJ3", "FFJ4"],
                        ["MFJ0", "MFJ1", "MFJ2", "MFJ3", "MFJ4"],
                        ["RFJ0", "RFJ1", "RFJ2", "RFJ3", "RFJ4"],
                        ["LFJ0", "LFJ1", "LFJ2", "LFJ3", "LFJ4", "LFJ5"],
                        ["THJ1", "THJ2", "THJ3", "THJ4", "THJ5"],
                        ["WRJ1", "WRJ2"] ]

        row = 0
        col = 0
        index_jtm_mapping = 0
        for finger in joint_names:
            col = 0
            for joint_name in finger:
                motor_index = joint_to_motor_mapping[index_jtm_mapping]
                if motor_index != -1:
                    motor = Motor(self.motors_frame, joint_name, motor_index)
                    self.motors_layout.addWidget(motor, row, col)
                    self.motors.append( motor )
                    col += 1
                index_jtm_mapping += 1
            row += 1
        Qt.QTimer.singleShot(0, self.window.adjustSize)

    def activate(self):
        GenericPlugin.activate(self)
        self.set_icon(self.parent.parent.rootPath + '/images/icons/iconHand.png')
        self.populate_motors()

    def on_close(self):
        for motor in self.motors:
            motor.setParent(None)
        self.motors = []

        GenericPlugin.on_close(self)
























