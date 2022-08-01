import os
import PySpin
import sys
from AcquisitionMultipleCamera import run_multiple_cameras
from DisplayCameras import AcquireAndDisplay, reset_trigger_mode_software


def main():

    print("1 : AcquisitionMultipleCamera to take multiple pictures from 1 or 2 cameras")
    print("2 : AcquireAndDisplay to display one or 2 cameras")
    code = input("Choose which code you want to launch : ")

    if code == "1":

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

        result = run_multiple_cameras(cam_list)

        print('Example complete... \n')

        # Clear camera list before releasing system
        cam_list.Clear()

        # Release system instance
        system.ReleaseInstance()

        input('Done! Press Enter to exit...')
        return result


    if code == "2":

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

    if code == "":
        return False

    else:
        print(" ")
        print("Please choose a code or press Enter to exit")
        print(" ")
        return main()

if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)