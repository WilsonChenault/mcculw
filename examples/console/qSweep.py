"""
File: qSweep.py

Purpose: Runs a q-sweep from defined low, high, and step frequencies. Write these in at the bottom of the document, where the function qSweep() is run with its three arguments.

Currently runs on 9 points per cycle (line 63) and builds frequency off sample rate and points (line 134).

Includes a logging function that outputs to an external file named "console.txt". Contains various pieces of information, such as the frequencies run, input data collected, scan status during which run, timings, date, and debug lines such as traceback errors.

This file can be run from the mcculw/examples/console folder, but no where else and I don't exactly have the time or technincal know-how to fix that for now. 

Required: numpy, scipy, mcculw, matplotlib
"""

import traceback
import logging

import numpy as np
import scipy as sp
import matplotlib.pyplot as plt

from time import sleep
from time import time
from ctypes import cast, POINTER, c_ushort

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import ScanOptions, FunctionType, Status, TrigType, DigitalIODirection
from mcculw.ul import ULError

# Logging function
log = logging.getLogger(__name__)
logging.basicConfig(
    filename = 'console.log',
    filemode = 'w',
    format = '%(asctime)s - %(filename)s - %(lineno)d :: %(message)s', 
    level=logging.INFO
)

# Board/Device
use_device_detection = True
board_num = 0
deviceInfo = DaqDeviceInfo(board_num)
if not deviceInfo.supports_analog_input:
    raise Exception('Error: The DAQ device does not support analog input')
if not deviceInfo.supports_analog_output:
    raise Exception('Error: The DAQ device does not support analog output')
print('Active DAQ Device: ' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')
log.info('Active DAQ Device: ' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')

# Device Info
ao_info = deviceInfo.get_ao_info()
ao_range = ao_info.supported_ranges[0]
ai_info = deviceInfo.get_ai_info()
ai_range = ai_info.supported_ranges[0]
dio_info = deviceInfo.get_dio_info()
port = next((port for port in dio_info.port_info if port.supports_output), None) # Find port
if port.is_port_configurable: # Configure port for output
    ul.d_config_port(board_num, port.type, DigitalIODirection.OUT)
port_value, bit_num = 0xFF, 0
bitHigh, bitLow = 1, 0
channel, low_chan, high_chan = 0, 0, 0 # Channel defining for qSweep()
wavePoints = 10 # Defining for both fit loop and sine function. Real points is wavePoints - 1 because the final 0 must be dropped or else you don't get clean cycles of sin(x); you instead get 0, ..., 0, 0, ... because it ends and begins on a 0.

# Defining Sine Wave Generation
def sine(numPoints):
    global sineOutput
    xData = np.linspace(0, 2 * np.pi, numPoints)
    sineHold = np.ndarray.tolist(np.sin(xData) * 10)
    sineOutput = []
    for i in sineHold:
        valueHold = ul.from_eng_units(board_num, ao_range, i)
        sineOutput.append(valueHold)
        
# Define function for fitting datasets
def curveFit(xdata, offset, ampl, phase, cycles):
    return offset + ampl * np.sin(cycles * xdata + phase)

def fit(xdata, ydata, cycles):
    global params, paramsError
    offset = np.average([min(ydata), max(ydata)])
    ampl = 0.5 * (max(ydata) + min(ydata))
    params, paramsError = sp.optimize.curve_fit(curveFit, xdata, ydata, 
                                                p0 = [offset, ampl, 0, cycles], 
                                                bounds = ([-np.inf, 0, 0, 0], 
                                                [np.inf, np.inf, 2 * np.pi, np.inf]),
                                                max_nfev = 1500
                                            )
    return params, paramsError

# Defining QSweep function
def qSweep(minFreq, maxFreq, stepFreq):
    # Handling memory buffer
    totalPoints = 46 # Total number of points that get scanned.
    inputPoints = 46
    scanBuffer = ul.win_buf_alloc(totalPoints)
    inputBuffer = ul.win_buf_alloc(inputPoints)
    outputArray = cast(scanBuffer, POINTER(c_ushort))
    inputArray = cast(inputBuffer, POINTER(c_ushort))
    compFreq = 0 # Defining for terminal print
    
    # Writing scan data into buffer
    sineExtend = sineOutput[1::] * (int(totalPoints/len(sineOutput)))
    sineOutput.extend(sineExtend) # Copying the sine output over the course of the buffer
    for i in range(len(sineOutput)):
        outputArray[i] = sineOutput[i]
    
    # Setting trigger for simultaneous activation of scans
    ul.set_trigger(board_num, TrigType.TRIG_HIGH, 0, 36045)
    
    # Frequencies that are specified to be tested
    log.info('Minimum Frequency: ' + str(minFreq))
    log.info('Maximum Frequency: ' + str(maxFreq))
    log.info('Step Frequency: ' + str(stepFreq))
    frequencies = []
    while maxFreq >= minFreq:
        frequencies.append(minFreq)
        minFreq = minFreq + stepFreq
    
    # Main body loop
    # Outputs a frequency (numPoints/rate) to the coil. Reads back the data sent out.
    inData = [] # Defining measured data to append
    print('Scan in progress...')
    startTime = time()
    for freq in frequencies:
    
        # Initial Status and Starting Loop
        outStatus, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
        inStatus, _, _ = ul.get_status(board_num, FunctionType.AIFUNCTION)
        log.info('Frequency: ' + str(freq))
        log.info('Loop begin: ' + str(outStatus) + ', ' + str(inStatus))
    
        # Define rate. This is our way of adjusting the frequency outputted
        rate = freq * 9 # * n for n points/cycle
        inputHold = []
        ul.d_out(board_num, port.type, port_value)
        ul.d_bit_out(board_num, port.type, bit_num, bitLow) # Set bit to OFF
        try:
            ul.a_out_scan(board_num, low_chan, high_chan, totalPoints, rate, ao_range, scanBuffer, ScanOptions.BACKGROUND | ScanOptions.EXTTRIGGER)
            outStatus, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
        except ULError as e:
            print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            log.error('ERROR: ' + '\n' + "A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            traceback.print_exc()
            input("Press enter to close script...")
  
        # Reading input. Using the scan feature to create an array for each sample set of data.
        try:
            ul.a_in_scan(board_num, low_chan, high_chan, inputPoints, rate, ai_range, inputBuffer, ScanOptions.BACKGROUND | ScanOptions.EXTTRIGGER)
        except ULError as e:
            print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            log.error('ERROR: ' + '\n' + "A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
            traceback.print_exc()
            input("Press enter to close script...")
            
        # Activate trigger
        ul.d_bit_out(board_num, port.type, bit_num, bitHigh) # Set logic output to HIGH
        inStatus, _, _ = ul.get_status(board_num, FunctionType.AIFUNCTION)
        log.info('Before data col.: ' + str(inStatus))
        while inStatus != inStatus.IDLE:
            inStatus, _, _ = ul.get_status(board_num, FunctionType.AIFUNCTION)
        ul.win_buf_to_array(inputBuffer, inputArray, 0, 50)
        for i in range(inputPoints - 1):
            inputHold.append(inputArray[i + 1])
        inData.append(inputHold)
        
        # Slow down mildly to prevent CPU overflow
        outStatus = Status.RUNNING
        while outStatus != outStatus.IDLE:
            sleep(0.1)
            outStatus, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
            
        # Check to make sure both scans are idle
        while outStatus or inStatus == Status.RUNNING:
            outStatus, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
            inStatus, _, _ = ul.get_status(board_num, FunctionType.AIFUNCTION)
        log.info('Loop end: ' + str(outStatus) + ', ' + str(inStatus))
        compFreq += 1
        print('Frequencies completed: ' + str(compFreq) + '/' + str(len(frequencies)), end='\r') # Display for progress. Nice to have but unnecessary
    
    endTime = time()
    
    # Fitting each data set and gathering the amplitude
    numCycles = 4.8 # currently not very adaptable but will be refined
    xdata = np.linspace(0, 2 * np.pi, totalPoints - 1)
    paramsList = [] # Defining params list for function fits
    amplList = []
    for i in range(len(inData)):
        fit(xdata, inData[i], numCycles)
        paramsList.append(params)
        amplList.append(params[1])
    
    # Plotting the amplitude vs. frequency
    plt.figure()
    plt.scatter(frequencies, amplList)
    plt.show()
    
    # Success
    print('\n')
    log.info('\n' + 'Frequencies: ' + str(frequencies))
    log.info('Resonance Data: ' + str(inData) + '\n')
    log.info(endTime - startTime)
    print('Time taken: ' + str(round(endTime - startTime, 2)) + ' sec')
    print('Test successful! Press enter to close the script.')
    input()

if __name__ == '__main__':
    try:
        sine(wavePoints)
        qSweep(1000, 55000, 100)
    except Exception as e:
        file = open('console.log', 'a')
        file.write(traceback.format_exc())
        f.close()