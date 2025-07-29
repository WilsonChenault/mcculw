"""
File: qSweep.py

Purpose: qSweep.py but it also provides a graph of raw voltages as well instead of the DAQ internal numbers. Weird stuff going on with the voltage conversion; needs to be made normal but I really can't figure out what is going on with the amplitudes and fits. 

Tried to have the same dataset twice, just once in engineering units and one in DAQ units, but that failed and is the current version of the script. The next step would be to try converting the final fit parameters into voltages instead, not duplicating any work and hopefully fixing the very odd graphs that come of this script.

Required: scipy, numpy, mcculw, matplotlib
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
wavePoints = 10 # Defining for both fit loop and sine function.

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
                                                bounds = ([-np.inf, -10, -10, -10], 
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
    print('Waiting for scan...')
    for freq in frequencies:
    
        # Some DEBUG code
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
            log.info(outStatus) # DEBUG
            
        # Check to make sure both scans are idle
        while outStatus or inStatus == Status.RUNNING:
            outStatus, _, _ = ul.get_status(board_num, FunctionType.AOFUNCTION)
            inStatus, _, _ = ul.get_status(board_num, FunctionType.AIFUNCTION)
        log.info('Loop end: ' + str(outStatus) + ', ' + str(inStatus))
    
    # Converting all data into volts
    voltData = []
    for i in range(len(inData)):
        voltHold = []
        for j in range(len(inData[i])):
            voltHolder = ul.to_eng_units(board_num, ai_range, inData[i][j])
            voltHold.append(voltHolder)
        voltData.append(voltHold)
    
    
    # Fitting each data set and gathering the amplitude
    numCycles = 4.8 # currently not very adaptable but will be refined
    xdata = np.linspace(0, 2 * np.pi, totalPoints - 1)
    paramsList = [] # Defining params list for function fits
    amplList = []
    for i in range(len(inData)):
        fit(xdata, inData[i], numCycles)
        paramsList.append(params)
        amplList.append(params[1])
    # Fitting volt data
    volt_paramsList = []
    volt_amplList = []
    for i in range(len(voltData)):
        fit(xdata, voltData[i], numCycles)
        volt_paramsList.append(params)
        volt_amplList.append(params[1])
    
    # Plotting the amplitude vs. frequency
    plt.figure()
    plt.scatter(frequencies, amplList)
    plt.figure()
    plt.scatter(frequencies, volt_amplList)
    plt.show()
    
    # DEBUG fits
    xFitted = np.linspace(0, 2 * np.pi, totalPoints * 5)
    plt.figure()
    plt.scatter(xdata, inData[38])
    plt.plot(xFitted, curveFit(xFitted, *paramsList[38]))
    plt.show()
    
    # Success
    print('\n' + 'Frequencies: ' + str(frequencies))
    print('Resonance Data: ' + str(inData) + '\n')
    print('Test successful! Press enter to close the script.')
    input()

if __name__ == '__main__':
    try:
        sine(wavePoints)
        qSweep(20000, 50000, 700)
    except Exception as e:
        file = open('console.log', 'a')
        file.write(traceback.format_exc())
        f.close()