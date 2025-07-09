"""
File: wil_aouttest2.py

Purpose: More testing. Writing most code from scratch instead of copy + paste.
"""

from time import sleep
import traceback

from mcculw import ul
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import ULRange
from mcculw.ul import ULError

# Board Num
use_device_detection = True
board_num = 0

# Displaying active device
deviceInfo = DaqDeviceInfo(board_num)
if not deviceInfo.supports_analog_input:
    raise Exception('Error: The DAQ device does not support analog input')
    
print('Active DAQ Device: ' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')


# Device Info
ao_info = deviceInfo.get_ao_info()
ao_range = ao_info.supported_ranges[0]
ai_info = deviceInfo.get_ai_info()
ai_range = ai_info.supported_ranges[0]
channel = 0

# Pushing value out of output channel
outValue = 150
try:
    ul.a_out(board_num, channel, ao_range, outValue)
except ULError as e:
    # Print error
    print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
    traceback.print_exc()
    input("Press enter to close script...")
# Print output value
print('Output Value: ' + str(outValue))

# Reading the input channel
try:
    # Get value from device
    inValue = ul.a_in(board_num, channel, ai_range)
    # Convert value to readable units
    eng_units_value = ul.to_eng_units(board_num, ai_range, inValue)
    
    # Print value
    print("Raw Value:" + str(inValue))
    # Print converted value
    print("Engineering Value: " + str(eng_units_value))
    
    # Success! Delay closing input
    print('Test completed! Press enter to close the script.')
    input()
except ULError as e:
    # Print error
    print("A UL error occurred. Code: " + str(e.errorcode) + " Message: " + e.message)
    traceback.print_exc()
    input("Press enter to close script...")