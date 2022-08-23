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
num_images = cfg['num_images']
exp_time = cfg['exp_time']
gain = cfg['gain']
bin_val = int(1)  # bin mode (WIP)
if cfg['file_path'] == 0:
    im_savepath = os.path.join(dname, 'images')
else:
    im_savepath = os.path.join(dname, 'images')
filename = cfg['file_name'] + str(cfg['stim_run'])
framerate = cfg['framerate']

# Create webcam and aux save folder
if not os.path.exists(im_savepath):
    os.makedirs(im_savepath)
os.chdir(im_savepath)


# Thread process for saving .
# offloading it to separate CPU threads allows continuation of image capture
class ThreadWrite(threading.Thread):
    def __init__(self, data, out):
        threading.Thread.__init__(self)
        self.data = data
        self.out = out

    def run(self):
        self.data.Save(self.out)


# Capturing is also threaded, to increase performance
class ThreadCapture(threading.Thread):
    def __init__(self, cam, camnum, nodemap):
        threading.Thread.__init__(self)
        self.cam = cam
        self.camnum = camnum

    def run(self):
        times = []
        nodemap = self.cam.GetNodeMap()

        # num of the selected cam
        if self.camnum == 0:
            primary = 1
        else:
            primary = 0

        self.cam.BeginAcquisition()
        for i in range(num_images):
            try:
                #  Retrieve next received image
                if framerate == 'hardware':
                    image_result = self.cam.GetNextImage()
                else:
                    node_softwaretrigger_cmd = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
                    if not PySpin.IsAvailable(node_softwaretrigger_cmd) or not PySpin.IsWritable(
                            node_softwaretrigger_cmd):
                        print('Unable to execute trigger. Aborting...')
                        return False
                    node_softwaretrigger_cmd.Execute()
                    image_result = self.cam.GetNextImage()

                node_device_serial_number = PySpin.CStringPtr(self.cam.GetTLDeviceNodeMap().GetNode('DeviceSerialNumber'))

                if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
                    device_serial_number = node_device_serial_number.GetValue()
                    print('Image %d serial number set to %s...' % (i, device_serial_number))


                times.append(str(datetime.datetime.now()))

                if primary:
                    print('COLLECTING IMAGE ' + str(i + 1) + ' of ' + str(num_images), end='\r')
                    sys.stdout.flush()

                # Compose filename, write image to disk
                fullfilename = '000' + str(i+1) + '_' + str(primary)+  '.tif'
                background = ThreadWrite(image_result, fullfilename)
                background.start()
                image_result.Release()


            except PySpin.SpinnakerException as ex:
                print('Error : %s' % ex)
                return False

        self.cam.EndAcquisition()

        # Save frametime data
        with open(filename + '_t' + str(self.camnum) + '.txt', 'a') as t:
            for item in times:
                t.write(item + ',\n')



class ThreadCapture_DisplayCameras(threading.Thread):
    def __init__(self, cam, camnum, count):
        threading.Thread.__init__(self)
        self.cam = cam
        self.camnum = camnum
        self.count = count

    def run(self):
        times = []
        nodemap = self.cam.GetNodeMap()

        # num of the selected cam
        if self.camnum == 0:
            primary = 1
        else:
            primary = 0

        for i in range(num_images):
            try:
                #  Retrieve next received image
                if framerate == 'hardware':
                    image_result = self.cam.GetNextImage()
                else:
                    node_softwaretrigger_cmd = PySpin.CCommandPtr(nodemap.GetNode('TriggerSoftware'))
                    if not PySpin.IsAvailable(node_softwaretrigger_cmd) or not PySpin.IsWritable(
                            node_softwaretrigger_cmd):
                        print('Unable to execute trigger. Aborting...')
                        return False
                    node_softwaretrigger_cmd.Execute()
                    image_result = self.cam.GetNextImage()

                node_device_serial_number = PySpin.CStringPtr(self.cam.GetTLDeviceNodeMap().GetNode('DeviceSerialNumber'))

                if PySpin.IsAvailable(node_device_serial_number) and PySpin.IsReadable(node_device_serial_number):
                    device_serial_number = node_device_serial_number.GetValue()
                    print('Image %d serial number set to %s...' % (i, device_serial_number))


                times.append(str(datetime.datetime.now()))

                if primary:
                    print('COLLECTING IMAGE ' + str(i + 1) + ' of ' + str(num_images), end='\r')
                    sys.stdout.flush()

                # Compose filename, write image to disk
                fullfilename = '000' + str(i+1+self.count) + '_' + str(primary)+  '.tif'
                background = ThreadWrite(image_result, fullfilename)
                background.start()
                image_result.Release()


            except PySpin.SpinnakerException as ex:
                print('Error : %s' % ex)
                return False


        # Save frametime data
        with open(filename + '_t' + str(self.camnum) + '.txt', 'a') as t:
            for item in times:
                t.write(item + ',\n')
