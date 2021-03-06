#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
#    Copyright (C) 2021 by YOUR NAME HERE
#
#    This file is part of RoboComp
#
#    RoboComp is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    RoboComp is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with RoboComp.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
from PySide2.QtCore import QTimer
from PySide2.QtWidgets import QApplication
from genericworker import *
import pyrealsense2 as rs
import numpy as np
from pytransform3d.transform_manager import TransformManager
import pytransform3d.transformations as pytr
import pytransform3d.rotations as pyrot

class SpecificWorker(GenericWorker):
    def __init__(self, proxy_map, startup_check=False):
        super(SpecificWorker, self).__init__(proxy_map)

        self.Period = 50
        if startup_check:
            self.startup_check()
        else:
            self.timer.timeout.connect(self.compute)
            self.timer.start(self.Period)

    def __del__(self):
        print('SpecificWorker destructor')

    def setParams(self, params):

        self.device_serial = params["device_serial"]
        self.print = params["print"] == "true"
        print(self.device_serial)
        # realsense configuration
        try:
            config = rs.config()
            config.enable_device(self.device_serial)
            config.enable_stream(rs.stream.pose)
            self.pipeline = rs.pipeline()
            self.pipeline.start(config)

        except Exception as e:
            print("Error initializing camera")
            print(e)
            sys.exit(-1)

        # Transform managet
        self.tm = TransformManager()

        #initial empty translation
        self.tm.add_transform("world", "robot", pytr.transform_from(pyrot.active_matrix_from_intrinsic_euler_xyz
                                                                    ([0.0,0.0,0.0]),
                                                                     [0.0,0.0,0.0]))
        # get slam_sensor_0 coordinates in the robot's frame. Read them from config file
        self.tm.add_transform("robot", "slam_sensor",
                              pytr.transform_from(pyrot.active_matrix_from_intrinsic_euler_xyz([0, 0, 0]), [0, 0, 0])
                              )
        # insert here the second slam sensor
        #

        # when requested return an average of both sensors.

        return True


    @QtCore.Slot()
    def compute(self):
        frames = self.pipeline.wait_for_frames()
        f = frames.first_or_default(rs.stream.pose)
        # Cast the frame to pose_frame and get its data
        data = f.as_pose_frame().get_pose_data()
        self.tm.add_transform("world", "robot", pytr.transform_from(pyrot.matrix_from_quaternion
                                                                    ([data.rotation.w,
                                                                      data.rotation.x,
                                                                      data.rotation.y,
                                                                      data.rotation.z]),
                                                                    [data.translation.x*1000.0,
                                                                     data.translation.y*1000.0,
                                                                     data.translation.z*1000.0]))

        if self.print:
            print("\r Device Position: ", data.translation, data.rotation, end="\r")


    def startup_check(self):
        QTimer.singleShot(200, QApplication.instance().quit)

    # =============== Methods for Component Implements ==================
    # ===================================================================

    #
    # IMPLEMENTATION of getFullPoseEuler method from FullPoseEstimation interface
    #
    def FullPoseEstimation_getFullPoseEuler(self):
        print("hola")
        t = self.tm.get_transform("origin", "slam_sensor")
        rot = t[0:3, 0:3]
        angles = pyrot.extrinsic_euler_xyz_from_active_matrix(rot)
        ret = RoboCompFullPoseEstimation.FullPoseEuler()
        ret.x = t[0][3]
        ret.y = t[1][3]
        ret.z = t[2][3]
        ret.rx = angles[0]
        ret.ry = angles[1]
        ret.rz = angles[2]
        return ret
    #
    # IMPLEMENTATION of getFullPoseMatrix method from FullPoseEstimation interface
    #
    def FullPoseEstimation_getFullPoseMatrix(self):
        ret = RoboCompFullPoseEstimation.FullPoseMatrix()
        t = self.tm.get_transform("origin", "slam_sensor")
        m = RoboCompFullPoseEstimation.FullPoseMatrix()
        m.m00 = t[0][0]
        m.m01 = t[0][1]
        m.m02 = t[0][2]
        m.m03 = t[0][3]
        m.m10 = t[1][0]
        m.m11 = t[1][1]
        m.m12 = t[1][2]
        m.m13 = t[1][3]
        m.m20 = t[2][0]
        m.m21 = t[2][1]
        m.m22 = t[2][2]
        m.m23 = t[2][3]
        m.m30 = t[3][0]
        m.m31 = t[3][1]
        m.m32 = t[3][2]
        m.m33 = t[3][3]
        return m
    #
    # IMPLEMENTATION of setInitialPose method from FullPoseEstimation interface
    #
    def FullPoseEstimation_setInitialPose(self, x, y, z, rx, ry, rz):

        self.tm.add_transform("origin", "world",
                               pytr.transform_from(pyrot.active_matrix_from_intrinsic_euler_xyz([rx, ry, rz]), [x, y, z])
                             )

    # ===================================================================
    # ===================================================================


    ######################
    # From the RoboCompFullPoseEstimationPub you can publish calling this methods:
    # self.fullposeestimationpub_proxy.newFullPose(...)

    ######################
    # From the RoboCompFullPoseEstimation you can use this types:
    # RoboCompFullPoseEstimation.FullPoseMatrix
    # RoboCompFullPoseEstimation.FullPoseEuler

