"""from pyfirmata import Arduino, util"""

import pyfirmata
import time
from scipy import signal
import matplotlib.pyplot as plt
import numpy as np
from AcquisitionMultipleCamera import read_config
import os

# Change cwd to script folder
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

# afin de lire la valeur du framerate directement depuis le fichier yaml

cfg = read_config('params.yaml')
framerate = cfg['framerate']


'''Square signal'''
t = np.linspace(0, 1, 500, endpoint=False)
signal = 1+signal.square(2 * np.pi * 5 * t)
plt.plot(t, signal)
plt.ylim(-1, 3)
# naming the x,y axis
plt.xlabel('Amplitude')
plt.ylabel('Time')
plt.title('Square signal')
# function to show the plot
plt.show()

board = pyfirmata.Arduino('COM6')
it = pyfirmata.util.Iterator(board)
it.start()

tension_input = board.get_pin('a:0:i')
trigger = board.get_pin('a:1:i')

while True:
    tension_value = tension_input.read()
    print(tension_value)
    tension_V = tension_value * (5.0 / 1023.0)
    print(tension_value + " V")
    time.sleep(0.1)

if tension_V == 5:
    # trouver comment insérer les fonctions python acquérir image etc
    trigger.write(signal)