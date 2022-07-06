import sys
import time
import PySpin

import numpy as np
import cv2



def set_trigger_mode_software(cam):
    cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
    cam.TriggerSource.SetValue(PySpin.TriggerSource_Software)
    cam.TriggerMode.SetValue(PySpin.TriggerMode_On)
    print("set trigger mode software")


def reset_trigger_mode_software(cam):
    cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
    print("reset trigger mode")


#
#   setup
#
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
            for key, value in frame.items():
                for i, cam in enumerate(cameras):
                    cv2.imwrite("{:04}_{}.jpg".format(count,i), value)
                count = count + 1


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
                    img = cv2.imshow("cam {}".format(device_serial_number), line)

                i.Release()
                del i

            except PySpin.SpinnakerException as ex:
                print("Error: {}".format(ex))

def main():
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


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)