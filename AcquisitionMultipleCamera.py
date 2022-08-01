# ============================================================================
# Copyright (c) 2001-2021 FLIR Systems, Inc. All Rights Reserved.

# This software is the confidential and proprietary information of FLIR
# Integrated Imaging Solutions, Inc. ("Confidential Information"). You
# shall not disclose such Confidential Information and shall use it only in
# accordance with the terms of the license agreement you entered into
# with FLIR Integrated Imaging Solutions, Inc. (FLIR).
#
# FLIR MAKES NO REPRESENTATIONS OR WARRANTIES ABOUT THE SUITABILITY OF THE
# SOFTWARE, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
# PURPOSE, OR NON-INFRINGEMENT. FLIR SHALL NOT BE LIABLE FOR ANY DAMAGES
# SUFFERED BY LICENSEE AS A RESULT OF USING, MODIFYING OR DISTRIBUTING
# THIS SOFTWARE OR ITS DERIVATIVES.
# ============================================================================
#
# AcquisitionMultipleCamera.py shows how to capture images from
# multiple cameras simultaneously. It relies on information provided in the
# Enumeration, Acquisition, and NodeMapInfo examples.
#
# This example reads similarly to the Acquisition example,
# except that loops are used to allow for simultaneous acquisitions.

import os
import PySpin
import sys
import time
import threading
import yaml
import ruamel.yaml
from pathlib import Path
import numpy as np
import datetime


def read_config(configname):
    """
    Reads structured config file
    """
    ruamelFile = ruamel.yaml.YAML()
    path = Path(configname)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                cfg = ruamelFile.load(f)
        except Exception as err:
            if err.args[2] == "could not determine a constructor for the tag '!!python/tuple'":
                with open(path, 'r') as ymlfile:
                    cfg = yaml.load(ymlfile, Loader=yaml.SafeLoader)
                    write_config(configname, cfg)
    else:
        raise FileNotFoundError(
            "Config file is not found. Please make sure that the file exists and/or there are no unnecessary spaces in the path of the config file!")
    return (cfg)

# Change cwd to script folder
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# Read cfg yaml file
cfg = read_config('params.yaml')
NUM_IMAGES = cfg['num_images']
exp_time = cfg['exp_time']
gain = cfg['gain']
bin_val = int(1)  # bin mode (WIP)
if cfg['file_path'] == 0:
    im_savepath = os.path.join(dname, 'images')
else:
    im_savepath = cfg['file_path']
filename = cfg['file_name'] + str(cfg['stim_run'])

# Create webcam and aux save folder
if not os.path.exists(im_savepath):
    os.makedirs(im_savepath)
os.chdir(im_savepath)

# Thread process for saving . This is super important, as the writing process takes time inline,
# so offloading it to separate CPU threads allows continuation of image capture
class ThreadWrite(threading.Thread):
    def __init__(self, data, out):
        threading.Thread.__init__(self)
        self.data = data
        self.out = out

    def run(self):
        # These commands are legacy, and not needed (kept for documentation)
        # image_result = self.data
        # image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
        self.data.Save(self.out)

# Capturing is also threaded, to increase performance
class ThreadCapture(threading.Thread):
    def __init__(self, cam, camnum, nodemap):
        threading.Thread.__init__(self)
        self.cam = cam
        self.camnum = camnum

    def run(self):
        times = []
        t1 = []
        if self.camnum == 0:
            primary = 1
        else:
            primary = 0

        for i in range(NUM_IMAGES):
            fstart = time.time()
            try:
                node_softwaretrigger_cmd = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
                if not PySpin.IsAvailable(node_softwaretrigger_cmd) or not PySpin.IsWritable(
                        node_softwaretrigger_cmd):
                    print('Unable to execute trigger. Aborting...')
                    return False
                node_softwaretrigger_cmd.Execute()
                image_result = self.cam.GetNextImage()

                times.append(str(time.time()))
                if i == 0 and primary == 1:
                    t1 = time.time()
                    print('*** ACQUISITION STARTED ***\n')

                if i == int(NUM_IMAGES - 1) and primary == 1:
                    t2 = time.time()
                if primary:
                    print('COLLECTING IMAGE ' + str(i + 1) + ' of ' + str(NUM_IMAGES), end='\r')
                    sys.stdout.flush()

                # Compose filename, write image to disk
                fullfilename = filename + '_' + str(i + 1) + '_cam' + str(primary) + '.jpg'
                background = ThreadWrite(image_result, fullfilename)
                background.start()
                image_result.Release()
                ftime = time.time() - fstart

            except PySpin.SpinnakerException as ex:
                print('Error (577): %s' % ex)
                return False

        self.cam.EndAcquisition()
        if primary:
            print('Effective frame rate: ' + str(NUM_IMAGES / (t2 - t1)))
        # Save frametime data
        with open(filename + '_t' + str(self.camnum) + '.txt', 'a') as t:
            for item in times:
                t.write(item + ',\n')


def acquire_images(cam_list):
    """
    This function acquires and saves 10 images from each device.

    :param cam_list: List of cameras
    :type cam_list: CameraList
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    times_0 = []
    times_1 = []
    diff_time0 = []*NUM_IMAGES
    diff_time1 = []*NUM_IMAGES

    print('*** IMAGE ACQUISITION ***\n')
    try:
        result = True

        # Prepare each camera to acquire images
        #
        # *** NOTES ***
        # For pseudo-simultaneous streaming, each camera is prepared as if it
        # were just one, but in a loop. Notice that cameras are selected with
        # an index. We demonstrate pseduo-simultaneous streaming because true
        # simultaneous streaming would require multiple process or threads,
        # which is too complex for an example.
        #

        for i, cam in enumerate(cam_list):

            # Set acquisition mode to continuous
            node_acquisition_mode = PySpin.CEnumerationPtr(cam.GetNodeMap().GetNode('AcquisitionMode'))
            if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
                print('Unable to set acquisition mode to continuous (node retrieval; camera %d). Aborting... \n' % i)
                return False

            node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
            if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                    node_acquisition_mode_continuous):
                print('Unable to set acquisition mode to continuous (entry \'continuous\' retrieval %d). \
                Aborting... \n' % i)
                return False

            acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

            node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

            print('Camera %d acquisition mode set to continuous...' % i)

            # Begin acquiring images
            cam.BeginAcquisition()

            print('Camera %d started acquiring images...' % i)

            print()

        # Retrieve, convert, and save images for each camera
        #
        # *** NOTES ***
        # In order to work with simultaneous camera streams, nested loops are
        # needed. It is important that the inner loop be the one iterating
        # through the cameras; otherwise, all images will be grabbed from a
        # single camera before grabbing any images from another.
        for n in range(NUM_IMAGES):
            for i, cam in enumerate(cam_list):

                try:
                    # Retrieve device serial number for filename
                    node_device_serial_number = PySpin.CStringPtr(cam.GetTLDeviceNodeMap().GetNode('DeviceSerialNumber'))

                    # Set value for gain and exposure time
                    cam.GainAuto.SetValue(PySpin.GainAuto_Off)
                    cam.Gain.SetValue(gain)
                    cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)
                    cam.ExposureTime.SetValue(min(cam.ExposureTime.GetMax(), exp_time * 1000000))


                    if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
                        device_serial_number = node_device_serial_number.GetValue()
                        print('Camera %d serial number set to %s...' % (i, device_serial_number))

                    # Retrieve next received image and ensure image completion
                    image_result = cam.GetNextImage(1000)
                    if i==0:
                        times_0.append(str(datetime.datetime.now()))
                        diff_time0.append(time.time())

                    if i==1:
                        times_1.append(str(datetime.datetime.now()))
                        diff_time1.append(time.time())


                    if image_result.IsIncomplete():
                        print('Image incomplete with image status %d ... \n' % image_result.GetImageStatus())
                    else:
                        # Print image information
                        width = image_result.GetWidth()
                        height = image_result.GetHeight()
                        print('Camera %d grabbed image %d, width = %d, height = %d' % (i, n, width, height))

                        # Convert image to mono 8
                        image_converted = image_result.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)

                        # Create a unique filename
                        #fullfilename = filename + '_' + str(n) + '_cam' + str(i+1)+  '.jpg'
                        fullfilename = '000' + str(n) + '_' + str(i)+  '.tif'


                        background = ThreadWrite(image_result, fullfilename)
                        background.start()

                        image_result.Release()
                        # Save image
                        image_converted.Save(filename)
                        print('Image saved at %s' % filename)


                    # Release image
                    image_result.Release()
                    print()

                except PySpin.SpinnakerException as ex:
                    print('Error: %s' % ex)
                    result = False

        # End acquisition for each camera
        #
        # *** NOTES ***
        # Notice that what is usually a one-step process is now two steps
        # because of the additional step of selecting the camera. It is worth
        # repeating that camera selection needs to be done once per loop.
        #
        # It is possible to interact with cameras through the camera list with
        # GetByIndex(); this is an alternative to retrieving cameras as
        # CameraPtr objects that can be quick and easy for small tasks.
        for cam in cam_list:

            # End acquisition
            cam.EndAcquisition()
        for i, cam in enumerate(cam_list):
            if i==0:
                # Save frametime data
                with open(filename + '_t' + str(i) + '.txt', 'a') as t:
                    for item in times_0:
                        t.write(item + ',\n')

            if i==1:
                # Save frametime data
                with open(filename + '_' + str(i) + '.txt', 'a') as t:
                    for item in times_1:
                        t.write(item + ',\n')

        # diff times for performance
        diff_time = [b - a for a, b in zip(diff_time0, diff_time1)]
        with open('diff_times' + '.txt', 'a') as t:
            for item in diff_time:
                t.write(str(item) + ',\n')



    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result


def print_device_info(nodemap, cam_num):
    """
    This function prints the device information of the camera from the transport
    layer; please see NodeMapInfo example for more in-depth comments on printing
    device information from the nodemap.

    :param nodemap: Transport layer device nodemap.
    :param cam_num: Camera number.
    :type nodemap: INodeMap
    :type cam_num: int
    :returns: True if successful, False otherwise.
    :rtype: bool
    """

    print('Printing device information for camera %d... \n' % cam_num)

    try:
        result = True
        node_device_information = PySpin.CCategoryPtr(nodemap.GetNode('DeviceInformation'))

        if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
            features = node_device_information.GetFeatures()
            for feature in features:
                node_feature = PySpin.CValuePtr(feature)
                print('%s: %s' % (node_feature.GetName(),
                                  node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

        else:
            print('Device control information not available.')
        print()

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        return False

    return result

def run_multiple_cameras(cam_list):
    """
    This function acts as the body of the example; please see NodeMapInfo example
    for more in-depth comments on setting up cameras.

    :param cam_list: List of cameras
    :type cam_list: CameraList
    :return: True if successful, False otherwise.
    :rtype: bool
    """
    try:
        result = True

        # Retrieve transport layer nodemaps and print device information for
        # each camera
        # *** NOTES ***
        # This example retrieves information from the transport layer nodemap
        # twice: once to print device information and once to grab the device
        # serial number. Rather than caching the nodem#ap, each nodemap is
        # retrieved both times as needed.
        print('*** DEVICE INFORMATION ***\n')

        for i, cam in enumerate(cam_list):

            # Retrieve TL device nodemap
            nodemap_tldevice = cam.GetTLDeviceNodeMap()

            # Print device information
            result &= print_device_info(nodemap_tldevice, i)

        # Initialize each camera
        #
        # *** NOTES ***
        # You may notice that the steps in this function have more loops with
        # less steps per loop; this contrasts the AcquireImages() function
        # which has less loops but more steps per loop. This is done for
        # demonstrative purposes as both work equally well.
        #
        # *** LATER ***
        # Each camera needs to be deinitialized once all images have been
        # acquired.
        for i, cam in enumerate(cam_list):

            # Initialize camera
            cam.Init()

        # Acquire images on all cameras
        result &= acquire_images(cam_list)

        # Deinitialize each camera
        #
        # *** NOTES ***
        # Again, each camera must be deinitialized separately by first
        # selecting the camera and then deinitializing it.
        for cam in cam_list:

            # Deinitialize camera
            cam.DeInit()

        # Release reference to camera
        # NOTE: Unlike the C++ examples, we cannot rely on pointer objects being automatically
        # cleaned up when going out of scope.
        # The usage of del is preferred to assigning the variable to None.
        del cam

    except PySpin.SpinnakerException as ex:
        print('Error: %s' % ex)
        result = False

    return result
