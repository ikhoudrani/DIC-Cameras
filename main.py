import os
import PySpin
import sys
from AcquisitionMultipleCamera import launch_acquisition
from DisplayCameras import launch_display


def main():

    print("1 : AcquisitionMultipleCamera to take multiple pictures from 1 or 2 cameras")
    print("2 : AcquireAndDisplay to display one or 2 cameras")
    code = input("Choose which code you want to launch : ")

    if code == "1":

        # launch the AcquisitionMultipleCamera code

        launch_acquisition()


    if code == "2":

        # launch DisplayCameras code

        launch_display()

if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)