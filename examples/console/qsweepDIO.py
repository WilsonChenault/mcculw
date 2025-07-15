'''
Digital Trigger Test

'''

# Imports
import logging
import numpy as np
import traceback

from mcculw import ul
from mcculw.enums import DigitalIODirection
from mcculw.device_info import DaqDeviceInfo

# Logging function
log = logging.getLogger(__name__)
logging.basicConfig(
    filename = 'console.log',
    filemode = 'w',
    format = '%(asctime)s - %(filename)s - %(lineno)d :: %(message)s', 
    level=logging.INFO
)

use_device_detection = True
dev_id_list = []
board_num = 0

# Board info
try:
    deviceInfo = DaqDeviceInfo(board_num)
except ULError as e:
    print('Failed!')
    
print('Active DAQ Device' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')
log.info('Active DAQ Device' + deviceInfo.product_name + ' (' + deviceInfo.unique_id + ')')

ai_info = deviceInfo.get_ai_info()
ai_range = ai_info.supported_ranges[0]
dio_info = deviceInfo.get_dio_info()
channel = 1

def digOutTest():
    # First port
    port = next((port for port in dio_info.port_info if port.supports_output), None)
    log.info(port)
    if not port:
        raise Exception('Error: the DAQ device does not support digital output')
        
    # Configure for output
    if port.is_port_configurable:
        ul.d_config_port(board_num, port.type, DigitalIODirection.OUT)
        
    port_value = 0xFF

    log.info('Setting ' + str(port.type.name) +  ' to ' + str(port_value))
    print('Setting', port.type.name, 'to', port_value)
    
    # Actually set port
    ul.d_out(board_num, port.type, port_value)
    
    # Set bit output
    bit_num = np.arange(8)
    bit_value = 1
    
    for i in range(len(bit_num)):
        ul.d_bit_out(board_num, port.type, bit_num[i], bit_value)
    
    #ul.d_bit_out(board_num, port.type, bit_num, bit_value)
    log.info('Setting ' + str(port.type.name) + ' bit ' + str(bit_num) + ' to ' + str(bit_value))
    print('Setting ' + port.type.name + ' bit ' + str(bit_num) + ' to ' + str(bit_value))
    
    # Read input channel
    value = ul.a_in(board_num, channel, ai_range)
    log.info('Channel 1 Input: ' + str(value))
    
try:
    digOutTest()
except Exception as e:
    file = open('console.log', 'a')
    file.write(traceback.format_exc())
    f.close()