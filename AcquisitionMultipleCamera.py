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
    im_savepath = cfg['file_path']
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

def configure_cam(cam):
    result = True

    try:
        nodemap = cam.GetNodeMap()
        # Ensure trigger mode off
        # The trigger must be disabled in order to configure whether the source
        # is software or hardware.
        node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
        if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
            print('Unable to disable trigger mode 129 (node retrieval). Aborting...')
            return False

        node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
        if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
            print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

        node_trigger_source = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerSource'))
        if not PySpin.IsAvailable(node_trigger_source) or not PySpin.IsWritable(node_trigger_source):
            print('Unable to get trigger source 163 (node retrieval). Aborting...')
            return False

        # Set primary camera trigger source to line0 (hardware trigger)
        if framerate == 'hardware':
            node_trigger_source_set = node_trigger_source.GetEntryByName('Line0')

        else:
            node_trigger_source_set = node_trigger_source.GetEntryByName('Software')


        if not PySpin.IsAvailable(node_trigger_source_set) or not PySpin.IsReadable(
                node_trigger_source_set):
            print('Unable to set trigger source (enum entry retrieval). Aborting...')
            return False

        node_trigger_source.SetIntValue(node_trigger_source_set.GetValue())
        node_trigger_mode_on = node_trigger_mode.GetEntryByName('On')

        if not PySpin.IsAvailable(node_trigger_mode_on) or not PySpin.IsReadable(node_trigger_mode_on):
            print('Unable to enable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_on.GetValue())

        # Set acquisition mode to continuous
        node_acquisition_mode = PySpin.CEnumerationPtr(nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False

        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(
                node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()

        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)
        print('Camera acquisition mode set to continuous...' )

        # Retrieve Stream Parameters device nodemap
        s_node_map = cam.GetTLStreamNodeMap()

        # Retrieve Buffer Handling Mode Information
        handling_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsAvailable(handling_mode) or not PySpin.IsWritable(handling_mode):
            print('Unable to set Buffer Handling mode (node retrieval). Aborting...\n')
            return False

        handling_mode_entry = PySpin.CEnumEntryPtr(handling_mode.GetCurrentEntry())
        if not PySpin.IsAvailable(handling_mode_entry) or not PySpin.IsReadable(handling_mode_entry):
            print('Unable to set Buffer Handling mode (Entry retrieval). Aborting...\n')
            return False

        # Set stream buffer Count Mode to manual
        stream_buffer_count_mode = PySpin.CEnumerationPtr(s_node_map.GetNode('StreamBufferCountMode'))
        if not PySpin.IsAvailable(stream_buffer_count_mode) or not PySpin.IsWritable(stream_buffer_count_mode):
            print('Unable to set Buffer Count Mode (node retrieval). Aborting...\n')
            return False

        stream_buffer_count_mode_manual = PySpin.CEnumEntryPtr(stream_buffer_count_mode.GetEntryByName('Manual'))
        if not PySpin.IsAvailable(stream_buffer_count_mode_manual) or not PySpin.IsReadable(
                stream_buffer_count_mode_manual):
            print('Unable to set Buffer Count Mode entry (Entry retrieval). Aborting...\n')
            return False

        stream_buffer_count_mode.SetIntValue(stream_buffer_count_mode_manual.GetValue())


        # Access trigger overlap info
        node_trigger_overlap = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerOverlap'))
        if not PySpin.IsAvailable(node_trigger_overlap) or not PySpin.IsWritable(node_trigger_overlap):
            print('Unable to set trigger overlap to "Read Out". Aborting...')
            return False

        # Retrieve enumeration for trigger overlap Read Out
        if framerate == 'hardware':
            node_trigger_overlap_ro = node_trigger_overlap.GetEntryByName('ReadOut')
        else:
            node_trigger_overlap_ro = node_trigger_overlap.GetEntryByName('Off')

        if not PySpin.IsAvailable(node_trigger_overlap_ro) or not PySpin.IsReadable(
                node_trigger_overlap_ro):
            print('Unable to set trigger overlap (entry retrieval). Aborting...')
            return False

        # Retrieve integer value from enumeration
        trigger_overlap_ro = node_trigger_overlap_ro.GetValue()

        # Set trigger overlap using retrieved integer from enumeration
        node_trigger_overlap.SetIntValue(trigger_overlap_ro)

        # Access exposure auto info
        node_exposure_auto = PySpin.CEnumerationPtr(nodemap.GetNode('ExposureAuto'))
        if not PySpin.IsAvailable(node_exposure_auto) or not PySpin.IsWritable(node_exposure_auto):
            print('Unable to get exposure auto. Aborting...')
            return False

        # Retrieve enumeration for trigger overlap Read Out
        node_exposure_auto_off = node_exposure_auto.GetEntryByName('Off')
        if not PySpin.IsAvailable(node_exposure_auto_off) or not PySpin.IsReadable(
                node_exposure_auto_off):
            print('Unable to get exposure auto "Off" (entry retrieval). Aborting...')
            return False

        # Set exposure auto to off
        node_exposure_auto.SetIntValue(node_exposure_auto_off.GetValue())
        #cam.ExposureAuto.SetValue(PySpin.ExposureAuto_Off)

        # Access exposure info
        node_exposure_time = PySpin.CFloatPtr(nodemap.GetNode('ExposureTime'))
        if not PySpin.IsAvailable(node_exposure_time) or not PySpin.IsWritable(node_exposure_time):
            print('Unable to get exposure time. Aborting...')
            return False

        # Set value
        node_exposure_time.SetValue(exp_time * 1000000)
        cam.GainAuto.SetValue(PySpin.GainAuto_Off)
        cam.Gain.SetValue(gain)

    # General exception
    except PySpin.SpinnakerException as ex:
        print('Error (237): %s' % ex)
        return False

    return result


def print_device_info(nodemap, cam_num):
    # This function prints the device information of the camera

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
    thread = []
    #result = True

    #print('*** DEVICE INFORMATION ***\n')

    for i, cam in enumerate(cam_list):
        cam.Init()
        nodemap = cam.GetNodeMap()
        # Retrieve TL device nodemap
        nodemap_tldevice = cam.GetTLDeviceNodeMap()

        # Print device information
        #result &= print_device_info(nodemap_tldevice, i)

        #cam.BeginAcquisition()
        print('Camera %d started acquiring images...' % i)

        thread.append(ThreadCapture(cam, i, nodemap))
        thread[i].start()

    for t in thread:
        t.join()

    for i, cam in enumerate(cam_list):
        #reset_trigger(cam)
        cam.DeInit()


# Trigger reset
def reset_trigger(cam):
    nodemap = cam.GetNodeMap()
    try:
        result = True
        node_trigger_mode = PySpin.CEnumerationPtr(nodemap.GetNode('TriggerMode'))
        if not PySpin.IsAvailable(node_trigger_mode) or not PySpin.IsReadable(node_trigger_mode):
            print('Unable to disable trigger mode 630 (node retrieval). Aborting...')
            return False

        node_trigger_mode_off = node_trigger_mode.GetEntryByName('Off')
        if not PySpin.IsAvailable(node_trigger_mode_off) or not PySpin.IsReadable(node_trigger_mode_off):
            print('Unable to disable trigger mode (enum entry retrieval). Aborting...')
            return False

        node_trigger_mode.SetIntValue(node_trigger_mode_off.GetValue())

    except PySpin.SpinnakerException as ex:
        print('Error : %s' % ex)
        result = False

    return result

def main():
    # launch the AcquisitionMultipleCamera code

    try:
        test_file = open('test.txt', 'w+')
    except IOError:
        print('Unable to write to current directory. Please check permissions.')
        input('Press Enter to exit...')
        return False

    test_file.close()
    os.remove(test_file.name)

    result = True

    # Retrieve singleton reference to system object
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    num_cameras = cam_list.GetSize()

    print('Number of cameras detected: %d' % num_cameras)

    # Finish if there are no cameras
    if num_cameras == 0:

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        return False

    # Run example on all cameras
    print('Running example for all cameras...')

    run_multiple_cameras(cam_list)

    # Clear camera list before releasing system
    cam_list.Clear()

    # Release system instance
    system.ReleaseInstance()

    print('DONE')
    time.sleep(.5)
    print('Goodbye')
    time.sleep(2)
    return result

if __name__ == '__main__':
    main()