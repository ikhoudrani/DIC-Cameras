import sys
import os
import PySpin
import numpy as np
import cv2
import yaml
from pathlib import Path
import ruamel.yaml
from ThreadFile import ThreadCapture_DisplayCameras, read_config

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



def set_trigger_mode_software(cam):
    cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
    cam.TriggerSource.SetValue(PySpin.TriggerSource_Software)
    cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
    print("set trigger mode software")


def reset_trigger_mode_software(cam):
    cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
    print("reset trigger mode")



def AcquireAndDisplay(cam_list, system, cameras):


    print("Number of cameras detected: {}".format(cam_list.GetSize()))

    if cam_list.GetSize() == 0:
        print('Not enough cameras!')
        input('Done! Press Enter to exit...')
        system.ReleaseInstance()
        del system
        sys.exit()

    for i in range(cam_list.GetSize()):
        cam = cam_list.GetByIndex(i)
        print("camera {} serial: {}".format(i, cam.GetUniqueID()))
        cam.Init()
        cam.AcquisitionMode.SetValue(PySpin.AcquisitionMode_Continuous)
        set_trigger_mode_software(cam)
        cam.BeginAcquisition()
        cameras.append(cam)


    count = 0
    frame = {}

    while 1:

        key = cv2.waitKey(1)

        if key == 27: # ESC
            cv2.destroyAllWindows()
            break
        elif key == 32: # SPACE
            print("take picture")
            thread = []

            for i, cam in enumerate(cam_list):

                #cam.BeginAcquisition()
                print('Camera %d started acquiring images...' % i)

                thread.append(ThreadCapture_DisplayCameras(cam, i, count))
                thread[i].start()

            for t in thread:
                t.join()
            count += num_images
            '''for key, value in frame.items():
                for i, cam in enumerate(cameras):
                    cv2.imwrite("{:04}_{}.jpg".format(count,0), value)
                count = count + 1'''


        for j, cam in enumerate(cameras):
            try:
                cam.TriggerSoftware()
                i = cam.GetNextImage()

                # retrieve id cams
                node_device_serial_number = PySpin.CStringPtr(cam.GetTLDeviceNodeMap().GetNode('DeviceSerialNumber'))
                device_serial_number = node_device_serial_number.GetValue()
                #print('Camera %d serial number set to %s...' % (j, device_serial_number))

                #print(i.GetWidth(), i.GetHeight(), i.GetBitsPerPixel())

                if i.IsIncomplete():
                    pass
                else:
                    cam_id = cam.GetUniqueID()
                    image_converted = i.Convert(PySpin.PixelFormat_BGR8, PySpin.DIRECTIONAL_FILTER)
                    image_data = image_converted.GetData()
                    cvi = np.frombuffer(image_data, dtype=np.uint8)
                    cvi = cvi.reshape((i.GetHeight(),i.GetWidth(),3))
                    frame[cam_id] = cvi
                    res = cv2.resize(cvi, (int(1280/4),int(1024/4)))
                    line = cv2.line(res, (int(1280/8), 0), (int(1280/8),int(1024/4)), (0, 0, 255), 2)
                    line = cv2.line(res, (0, int(1024/8)), (int(1280/4),int(1024/8)), (0, 0, 255), 2)
                    cv2.imshow("cam {}".format(device_serial_number), line)

                i.Release()
                del i

            except PySpin.SpinnakerException as ex:
                print("Error: {}".format(ex))

def launch_display():
    system = PySpin.System.GetInstance()

    # Get current library version
    version = system.GetLibraryVersion()
    print('Library version: %d.%d.%d.%d' % (version.major, version.minor, version.type, version.build))

    # Retrieve list of cameras from the system
    cam_list = system.GetCameras()

    cameras = []

    result = AcquireAndDisplay(cam_list, system, cameras)

    # Clean up

    for cam in cam_list:
        cam.EndAcquisition()
        reset_trigger_mode_software(cam)
        cam.DeInit()
        del cam
    del cameras
    del cam_list

    system.ReleaseInstance()
    del system

    input('Done! Press Enter to exit...')
    return result
