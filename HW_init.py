# import os
# if hasattr(os, "add_dll_directory"):
#     os.add_dll_directory(r"C:/Users/Lenovo/Downloads/libTSCANDemos-main/libTSCANDemos-main/Python/src/libTSCANAPI/windows/x64")

import can
import time
import can.interfaces
import threading
import udsoncan
import isotp
import traceback, os, ctypes.util
import logging
from udsoncan.connections import IsoTPSocketConnection
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
from udsoncan.exceptions import *
from udsoncan.services import *
# from Tosun.libtosun import libtosunBus
import time

# Get logger for this module
logger = logging.getLogger(__name__)

configs = [{'FChannel': 0, 'rate_baudrate': 500, 'data_baudrate': 2000, 'enable_120hm': True, 'is_fd': False},
           {'FChannel': 1, 'rate_baudrate': 500, 'data_baudrate': 2000, 'enable_120hm': True, 'is_fd': False},
           {'FChannel': 2, 'rate_baudrate': 500, 'data_baudrate': 2000, 'enable_120hm': True, 'is_fd': False},
           {'FChannel': 3, 'rate_baudrate': 500, 'data_baudrate': 2000, 'enable_120hm': True, 'is_fd': False}]


def CanDeInitt(can_handle,bus):
    logger.info("De-initializing CAN hardware...")
    try:
        bus.shutdown()
        logger.info("CAN bus shutdown successful")
        # can_handle.close()
    except Exception as e:
        logger.error(f"Error during CAN de-initialization: {e}", exc_info=True)

class TosunCleanBus(can.BusABC):
    """
    Wraps the Tosun python-can driver and cleans frames so ISO-TP sees valid classic CAN frames.
    """
    def __init__(self, real_bus):
        self.real_bus = real_bus
        super().__init__(channel=getattr(real_bus, "channel_info", "tosun-clean"), bitrate=None)

    def send(self, msg, timeout=None):
        msg.is_fd = False
        msg.bitrate_switch = False
        msg.dlc = min(msg.dlc, 8)
        return self.real_bus.send(msg, timeout)

    def recv(self, timeout=None):
        t0 = time.time()
        while time.time() - t0 < (timeout or 0.1):
            m = self.real_bus.recv(0.001)
            if m:
                m.is_fd = False
                m.bitrate_switch = False
                m.dlc = min(m.dlc, 8)
                # Strip any padding bytes (some Tosun DLLs pad up to 64)
                if len(m.data) > 8:
                    m.data = m.data[:8]
                return m
        return None

    def shutdown(self):
        try:
            self.real_bus.shutdown()
        except Exception:
            pass


def CanInit(hardware):
    logger.info("="*80)
    logger.info("CAN Hardware Initialization Starting")
    logger.info("="*80)
    print('Initializing CAN Hardware..\n')

    logger.info(f"Selected hardware: {hardware}")

    isotp_params = {
    'stmin': 32,                            # Will request the sender to wait 32ms between consecutive frame. 0-127ms or 100-900ns with values from 0xF1-0xF9

    'blocksize': 16,                         # Request the sender to send 8 consecutives frames before sending a new flow control message
    'wftmax': 0,                            # Number of wait frame allowed before triggering an error
    'tx_data_length': 8,                    # Link layer (CAN layer) works with 8 byte payload (CAN 2.0)
    # Minimum length of CAN messages. When different from None, messages are padded to meet this length. Works with CAN 2.0 and CAN FD.
    'tx_data_min_length': 8,
    'tx_padding': 0,                        # Will pad all transmitted CAN messages with byte 0x00.
    'rx_flowcontrol_timeout': 5000,         # Triggers a timeout if a flow control is awaited for more than 1000 milliseconds
    'rx_consecutive_frame_timeout': 5000,   # Triggers a timeout if a consecutive frame is awaited for more than 1000 milliseconds
    #'squash_stmin_requirement': False,      # When sending, respect the stmin requirement of the receiver. If set to True, go as fast as possible.
    'max_frame_size': 4095,                 # Limit the size of receive frame.
    'can_fd': False,                        # Does not set the can_fd flag on the output CAN messages // was changed from true to false
    'bitrate_switch': False,                # Does not set the bitrate_switch flag on the output CAN messages
    'rate_limit_enable': False,             # Disable the rate limiter
    'rate_limit_max_bitrate': 1000000,      # Ignored when rate_limit_enable=False. Sets the max bitrate when rate_limit_enable=True
    'rate_limit_window_size': 0.2,          # Ignored when rate_limit_enable=False. Sets the averaging window size for bitrate calculation when rate_limit_enable=True
    'listen_mode': False,                   # Does not use the listen_mode which prevent transmission.
    }

    logger.debug(f"ISO-TP parameters: {isotp_params}")

    uds_config = udsoncan.configs.default_client_config.copy()

    try:

        if hardware == "PCAN":
            logger.info("Initializing PCAN hardware on PCAN_USBBUS1 at 500kbps")
            bus = can.interface.Bus("PCAN_USBBUS1",interface="pcan",bitrate=500000)
            logger.info("PCAN bus initialized successfully")
        elif hardware == "TOSUN":
            logger.info("Initializing TOSUN hardware")
            # real_bus = can.interface.Bus(channel=0, bustype='libtosun')
            # bus = TosunCleanBus(real_bus)
            logger.debug("Registering libtosun backend")
            can.interfaces.BACKENDS["libtosun"] = ("Tosun.libtosun","libtosunBus")
            logger.debug(f"TOSUN configs: {configs}")
            bus = can.interface.Bus(0,interface="libtosun",configs=configs)
            logger.info("TOSUN bus initialized successfully")
############################### TESTING START TO CHECK IF MESSAGE SENDS ########################################

        # try:
        #     msg = can.Message(arbitration_id=0x7e0, data=[0x02,0x10,0x02,0xAA,0xAA,0xAA,0xAA,0xAA], is_extended_id=False)
        #     bus.send(msg)
        #     print("✅ Send succeeded.")
        # except Exception:
        #     traceback.print_exc()

        # # 2. Try to receive
        # try:
        #     print("Waiting for message (1s timeout)...")
        #     m = bus.recv(3.0)
        #     print("✅ Received:", m)
        # except Exception:
        #     traceback.print_exc()
        # finally:
        #     bus.shutdown()

        #     bus = can.interface.Bus(0,interface="libtosun",configs=configs)
        #     msg = can.Message(
        #     arbitration_id=0x123,        # CAN ID
        #     data=[0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88],  # up to 8 bytes for classical CAN
        #     is_extended_id=False         # False for 11-bit ID, True for 29-bit ID
        # )
            

        
            
        #     time.sleep(2)
        #     try:
        #         bus.send(msg)
        #         print("Message sent on {}".format(bus.channel_info))
        #     except can.CanError:
        #         print("Message NOT sent")

############################### TESTING ENDS TO CHECK IF MESSAGE SENDS ########################################


        # bus = can.Bus(interface="libtosun", configs=configs, is_recv_error=True, is_include_tx=True, hwserial=b"")
    


    except Exception as e:
        logger.error(f"CAN bus initialization failed: {e}", exc_info=True)
        logger.error("Returning BUS_INIT_ERROR")
        return "","BUS_INIT_ERROR"


    # print("Active threads before notifier:", threading.enumerate())

    # notifier = can.Notifier(bus, [can.Printer()], 0.01)   # 10 ms period
    # print("Active threads after notifier:", threading.enumerate())

    # for t in threading.enumerate():
    #     print(t.name, t.is_alive(), getattr(t, '_target', None))

    logger.info("Setting up CAN notifier with message printer")
    notifier = can.Notifier(bus, [can.Printer()])                                       # Add a debug listener that print all messages

    logger.info("Configuring ISO-TP address: TX=0x7E0, RX=0x7E8")
    tp_addr = isotp.Address(isotp.AddressingMode.Normal_11bits, txid=0x7E0, rxid=0x7E8) # Network layer addressing scheme

    logger.info("Creating ISO-TP stack (NotifierBasedCanStack)")
    try:
        stack = isotp.NotifierBasedCanStack(bus=bus, notifier=notifier, address=tp_addr, params=isotp_params)  # Network/Transport layer (IsoTP protocol). Register a new listenenr
        logger.info("ISO-TP stack created successfully")
    except Exception as e:
        logger.error(f"ISO-TP stack creation failed: {e}", exc_info=True)
        return "CAN_INIT_ERR",""

    # stack = isotp.CanStack(bus=bus,address=tp_addr,params=isotp_params)
    logger.info("Creating PythonIsoTpConnection")
    try:
        conn = PythonIsoTpConnection(stack)
        logger.info("PythonIsoTpConnection created successfully")

    except Exception as e:
        logger.error(f"PythonIsoTpConnection creation failed: {e}", exc_info=True)
        logger.error("Returning CAN_INIT_ERR")
        return "CAN_INIT_ERR",""

    logger.info("="*80)
    logger.info("CAN Hardware Initialization Complete - SUCCESS")
    logger.info("="*80)
    return conn,bus