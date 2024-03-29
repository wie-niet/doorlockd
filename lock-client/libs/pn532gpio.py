#
#
# PN532 User Manual  : https://www.nxp.com/docs/en/user-guide/141520.pdf
# PN532/C1 Data Sheet: https://www.nxp.com/docs/en/nxp/data-sheets/PN532_C1.pdf
#
# Using nfcpy to communicate with PN532.
#

import threading
import time

import logging

log = logging.getLogger(__name__)


class pn532Gpio:
    """
    GPIO interface to the PN532 rfid device, connected using nfcpy.
    including configuring AUX1 and AUX2

    Example:
    # initilialize
    clf = nfc.ContactlessFrontend('ttyS2:pn532')
    gpio = pn532Gpio(clf)

    # control gpio
    gpio.gpio_on('p72')           # set p72 on   (high: 1/True)
    gpio.gpio_off('p72')          # set p72 off  (low:  0/False)
    gpio.gpio_invert('p72')       # change value of p72
    gpio.gpio_set('p72', True)    # set value of p72 (high: 1/True)
    gpio.gpio_get('p71')          # read value of p71 (boolean)

    # configure
    gpio.cfg_gpio_set('p71', gpio.INPUT)   # set p71 as GPIO_TYPE 2: input (High Impedance)
    gpio.cfg_gpio_get('p72')      # get gpio config for p72, see cfg_gpio_get() for details.
    gpio.cfg_aux_set(aux1=0xb)    # set AUX1 to 'low' see comments or datasheet/PN532 for all options.
    gpio.cfg_aux_get('aux2')      # get AUX2 config.
    """

    # lookup dictionary with portname = [field, bit possition]
    _addr = {
        "p30": ["P3", 0x01],
        "p31": ["P3", 0x02],
        "p32": ["P3", 0x04],
        "p33": ["P3", 0x08],
        "p34": ["P3", 0x10],
        "p35": ["P3", 0x20],
        "p71": ["P7", 0x02],
        "p72": ["P7", 0x04],
    }

    # reference for cfg_gpio_set() / cfg_gpio_get()
    GPIO_TYPE = ["Open drain", "Quasi Bidirectional", "input", "Push/pull output"]
    OPEN_DRAIN = 0
    QUASI_BIDIRECTIONAL = 1
    INPUT = 2
    OUTPUT = 3

    def __init__(self, clf, hw_read_state=True, hw_read_cfg=True):
        # set Contact Less Frontend. PN532
        self.clf = clf

        #    _state[field] = value      	#  bit values  0x08  0x40  0x20  0x10  0x08  0x04  0x02  0x01
        self._state = {
            "P3": b"\x00"[
                0
            ],  #  bits: [change=1, None,  P35,  P34,  P33,  P32,  P31,  P30]
            "P7": b"\x00"[0],
        }  #  bits: [change=1, None, None, None, None,  P72,  P71, None]

        # The field P3 contains the state of the GPIO located on the P3 port
        # The field P7 contains the state of the GPIO located on the P7 port

        # register dictionary, see hw_read_cfg() how it's populated
        if hw_read_cfg:
            self.hw_read_cfg()
        else:
            self._cfg = {}

        # lock for self._state
        self._state_lock = threading.Lock()

        # read current state from hardware
        if hw_read_state:
            with self._state_lock:
                self.hw_read_state()

    def command(self, *args, **kwargs):
        # acquire lock for writing over TTY to pn53x
        with self.clf.lock:
            return self.clf.device.chipset.command(*args, **kwargs)

    def hw_read_state(self):
        """Read IO state of all ports into ._state[] and detect any RISING/FALING edge events.
        Use release_lock=True if this is only executed for event_detection and no lock is needed.


        this will obtain a lock on .state[], normaly it will be released by .commit().
        """
        if not self._state_lock.locked():
            raise RuntimeError("Need lock on self._state_lock for .hw_read_state().")

        # ReadGPIO command = 0x0c
        raw_state = self.command(0x0C, b"", 0.1)

        # b'\x00\x00'
        xor_event_detect = {"P3": 0x00, "P7": 0x00}

        # check rising/falling changes if we have any event_detect callbacks:
        if len(self._event_detect_list) != 0:
            # check for changes ( event_detect_mask AND old_value XOR new_value )
            xor_event_detect["P3"] = self._event_detect_mask["P3"] & (
                self._state["P3"] ^ raw_state[0]
            )
            xor_event_detect["P7"] = self._event_detect_mask["P7"] & (
                self._state["P7"] ^ raw_state[1]
            )

            # any faling/rising events?:
            if xor_event_detect != {"P3": 0x00, "P7": 0x00}:
                self._handle_event_detected(
                    xor_event_detect, {"P3": raw_state[0], "P7": raw_state[1]}
                )

        # update cache:
        self._state["P3"] = raw_state[0]
        self._state["P7"] = raw_state[1]
        # self._state['I0I1'] = raw_state[2]

    #
    # gpio config functions:
    #

    def hw_read_cfg(self):
        # initialize P3 and P7 dict
        _cfg = {"P3": {}, "P7": {}}

        # read registers
        result = self.command(0x06, b"\xff\xfc\xff\xfd\xff\xf4\xff\xf5", 0.1)
        _cfg["P3"]["A"] = result[0]  # P3CFGA FCh Port 3 configuration
        _cfg["P3"]["B"] = result[1]  # P3CFGB FDh Port 3 configuration
        _cfg["P7"]["A"] = result[2]  # P7CFGA F4h Port 7 configuration
        _cfg["P7"]["B"] = result[3]  # P7CFGB F5h Port 7 configuration

        self._cfg = _cfg

    def hw_write_cfg(self):
        # WriteRegister:
        # clf.device.chipset.command(0x08, [\xff + register address + value ] ... , 0.1)

        cmd = bytearray()
        # P3CFGA FCh Port 3 configuration
        cmd.append(0xFF)
        cmd.append(0xFC)
        cmd.append(self._cfg["P3"]["A"])
        # P3CFGB FDh Port 3 configuration
        cmd.append(0xFF)
        cmd.append(0xFD)
        cmd.append(self._cfg["P3"]["B"])
        # P7CFGA F4h Port 7 configuration
        cmd.append(0xFF)
        cmd.append(0xF4)
        cmd.append(self._cfg["P7"]["A"])
        # P7CFGB F5h Port 7 configuration
        cmd.append(0xFF)
        cmd.append(0xF5)
        cmd.append(self._cfg["P7"]["B"])

        result = self.command(0x08, cmd, 0.1)

    def cfg_gpio_get(self, port):
        """
        Get config type for GPIO port

        return int value:
                0: Open drain,
                1: Quasi Bidirectional,
                2: input,
                3: Push/pull output

        see pn532Gpio.GPIO_TYPE[(int)]
        """
        # lookup port in addr[], get state byte and bit position value
        (field, mask) = self._addr[port]

        # get cfg if missing
        if field not in self._cfg:
            self.hw_read_cfg()

        # At maximum 4 different controllable modes can be supported. These modes are defined with the following bits:
        # 0 • PxCFGA[n]=0 and PxCFGB[n]=0: Open drain
        # 1 • PxCFGA[n]=1 and PxCFGB[n]=0: Quasi Bidirectional (Reset mode)
        # 2 • PxCFGA[n]=0 and PxCFGB[n]=1: input (High Impedance)
        # 3 • PxCFGA[n]=1 and PxCFGB[n]=1: Push/pull output

        # boolean value for PxCFGA[n]
        pxcfga = self._cfg[field]["A"] | ~mask & 255 == 255
        # boolean value for PxCFGB[n]
        pxcfgb = self._cfg[field]["B"] | ~mask & 255 == 255

        # return value 0...4 [0: Open drain, 1: Quasi Bidirectional, 2: input, 3: Push/pull output]
        return (int(pxcfga) * 1) + (int(pxcfgb) * 2)

    def cfg_gpio_set(self, port, gpio_type, value=None, write=True):
        """
        gpio_type: int(0 ... 3)
        pn532Gpio.OPEN_DRAIN               0: Open drain
        pn532Gpio.QUASI_BIDIRECTIONAL      1: Quasi Bidirectional
        pn532Gpio.INPUT                    2: input
        pn532Gpio.OUTPUT                   3: Push/pull output

        value: value for output. 	None=leave hardware default,  True/1,  False/0

        use write=False if you have more changes, use hw_write_cfg() to write changes to hardware.
        """
        # lookup port in addr[], get state byte and bit position value
        (field, mask) = self._addr[port]

        # boolean value for PxCFGA[n] is 1st bit of gpio_type
        pxcfga = bool(gpio_type & 0b01)
        # boolean value for PxCFGB[n] is 2nd bit of gpio_type
        pxcfgb = bool(gpio_type & 0b10)

        # get cfg if missing
        if field not in self._cfg:
            self.hw_read_cfg()

        if pxcfga:
            # set bit position value to 1
            self._cfg[field]["A"] |= mask
        else:
            # set bit position value to 0
            self._cfg[field]["A"] &= ~mask

        if pxcfgb:
            # set bit position value to 1
            self._cfg[field]["B"] |= mask
        else:
            # set bit position value to 0
            self._cfg[field]["B"] &= ~mask

        if write:
            self.hw_write_cfg()

        if value is not None:
            self.gpio_set(port, value)

    #
    # gpio control functions
    #

    def commit(self):
        if not self._state_lock.locked():
            raise RuntimeError("Need lock on self._state_lock for .commit().")

        # WriteGPIO command = 0x0e
        result = self.command(
            0x0E, bytearray([self._state["P3"], self._state["P7"]]), 0.1
        )

        # reset 'change' bit
        self._state["P3"] &= ~0x80
        self._state["P7"] &= ~0x80

    def gpio_on(self, port):
        """
        set GPIO port on
        example: gpio_on('p33')
        """
        with self._state_lock:
            # lookup port in addr[], get state byte and bit position value
            (field, mask) = self._addr[port]
            # set bit position value to 1
            self._state[field] |= mask
            # update/change bit to 1
            self._state[field] |= 0x80

            # commit
            self.commit()

    def gpio_off(self, port):
        """
        set GPIO port off
        example: gpio_off('p33')
        """
        with self._state_lock:
            # lookup port in addr[], get state byte and bit position value
            (field, mask) = self._addr[port]
            # set bit position value to 0
            self._state[field] &= ~mask
            # update/change bit to 1
            self._state[field] |= 0x80

            # commit
            self.commit()

    def gpio_invert(self, port):
        """
        invert GPIO value, turn off when on and visa versa.
        example: gpio_invert('p33')
        """
        with self._state_lock:
            # lookup port in addr[], get state byte and bit position value
            (field, mask) = self._addr[port]
            # set bit position value to 1
            self._state[field] ^= mask
            # update/change bit to 1
            self._state[field] |= 0x80

            # commit
            self.commit()

    def gpio_set(self, port, value):
        """
        set GPIO port to bool(value)
        example: gpio_set('p33', True)
        """
        if value:
            self.gpio_on(port)
        else:
            self.gpio_off(port)

    def gpio_get(self, port):
        """return True/False if GPIO port is 1/0"""
        with self._state_lock:
            # read current IO values
            self.hw_read_state()

            # lookup port in addr[], get state byte and bit position value
            (field, mask) = self._addr[port]
            # return True if bit is set to 1
            value = self._state[field] | ~mask & 255 == 255

        return value

    #
    # get/set AUX1, AUX2 registers
    #

    def cfg_aux_get(self, aux="raw"):
        """
        read register 6328h, select AUX1 or AUX2 or Both by using RAW output.
        parameter (str) "aux1" | "aux2" | "raw"
        """
        # read registers
        result = self.command(0x06, b"\x63\x28", 0.1)

        if aux == "raw":
            # return raw result, both aux1 and aux2
            return result[0]
        if aux == "aux2":
            # return bit 4-7
            return result[0] >> 4
        if aux == "aux1":
            # return bit 0-3
            return result[0] & 0x0F

        # in other cases:
        raise ValueError("'aux' must be aux1 , aux2 or raw")

    def cfg_aux_set(self, aux1=None, aux2=None):
        """
        set value of aux1 and/or aux2: 0x0 ... 0xf

        see section 8.6.23.53, Table 279. Description of CIU_AnalogTest bits on Page 185.
        * references to https://www.nxp.com/docs/en/nxp/data-sheets/PN532_C1.pdf
        # 0x0    0000 Tristate
        # 0x1    0001 DAC output: register CIU_TestDAC1[1]
        # 0x2    0010 DAC output: test signal corr1[1]
        # 0x3    0011 DAC output: test signal corr2[1]
        # 0x4    0100 DAC output: test signal MinLevel[1]
        # 0x5    0101 DAC output: ADC_I[1]
        # 0x6    0110 DAC output: ADC_Q[1]
        # 0x7    0111 DAC output: ADC_I combined with ADC_Q[1]
        # 0x8    1000 Test signal for production test
        # 0x9    1001 secure IC clock
        # 0xa    1010 ErrorBusBit as described in Table 177 on page 145
        # 0xb    1011 Low
        # 0xc    1100 TxActive
        #             At 106 kbit/s: High during Start bit, Data bits, Parity and CRC
        #             At 212 kbit/s and 424 kbit/s: High during Preamble, Sync, Data bits and CRC
        # 0xd    1101 RxActive
        #             At 106 kbit/s: High during Data bits, Parity and CRC
        #             At 212 kbit/s and 424 kbit/s: High during Data bits and CRC
        # 0xe    1110 Subcarrier detected
        #             At 106 kbit/s: not applicable
        #             At 212 kbit/s and 424 kbit/s: High during last part of preamble, Sync, Data bits and CRC.
        # 0xf    1111 Test bus bit as defined by the TstBusBitSel in Table 265 on page 181
        """
        #
        # CIU_AnalogTest register (6328h) : AnalogSelAux1 AnalogSelAux2
        # bit allocation:   7    6    5    4   | 3    2    1    0
        # (4 bits each)    AnalogSelAux1 (7-4) | AnalogSelAux2 (3-0)
        #
        # Controls the AUX* pin. Note: All test signals are described in Section 8.6.21.3 “Test signals at pin AUX” on page 142.
        #  * references to https://www.nxp.com/docs/en/nxp/data-sheets/PN532_C1.pdf
        #
        if aux1 is None and aux2 is None:
            raise ValueError("Either set aux1 or aux2, no reason in setting nothing")

        if aux1 is None:
            aux1 = self.cfg_aux_get("aux1")
        if aux2 is None:
            aux2 = self.cfg_aux_get("aux2")

        # write settings to register 6328h
        cmd = bytearray()
        cmd.append(0x63)
        cmd.append(0x28)
        # combine aux1 and aux2 and write to hw:
        cmd.append(aux1 << 4 | aux2 & 0x0F)

        result = self.command(0x08, cmd, 0.1)

    #
    # Input Event detect loop
    #
    _event_detect_list = []
    _event_detect_thread = None
    _event_detect_wait = 0.2
    _event_detect_mask = {"P3": 0x00, "P7": 0x00}

    def add_event_detect(self, gpio_port, value, callback):
        """
        Add event callback for rising high/falling low value (true/false)
        """
        event = {}
        event["gpio_port"] = gpio_port
        event["value"] = value
        event["callback"] = callback

        # add event callback to list
        self._event_detect_list.append(event)

        # add bit mask to _event_detect_mask
        # lookup port in addr[], get state byte and bit position value
        (field, mask) = self._addr[gpio_port]
        # set bit position value to 1
        self._event_detect_mask[field] |= mask

        # start thread if needed, never starte or 1st added to list
        if self._event_detect_thread == None or len(self._event_detect_list) == 1:
            self._event_detect_loop_start()

    def remove_event_detect(self, gpio_port, value=None, callback=None):
        """Remove event_detect callback events."""

        if value is not None and callback is not None:
            # match everything
            event = {}
            event["gpio_port"] = gpio_port
            event["value"] = value
            event["callback"] = callback

            # remove callback from list
            self._event_detect_list.remove(event)

        else:
            # use None as joker '*'
            for event in self._event_detect_list:
                if event["gpio_port"] == gpio_port:
                    if event["value"] == value or value is None:
                        if event["callback"] == callback or callback is None:
                            # we have a match, let's remove event callback list
                            self._event_detect_list.remove(event)

        # do we need our event_detect_mask?
        for event in self._event_detect_list:
            if event["gpio_port"] == gpio_port:
                # yes we still need it,
                return

        # remove bit mask from _event_detect_mask
        # lookup port in addr[], get state byte and bit position value
        (field, mask) = self._addr[gpio_port]
        # set bit position value to 0
        self._event_detect_mask[field] &= ~mask

    def _event_detect_loop_start(self):
        self._event_detect_thread = threading.Thread(
            target=self._event_detect_run, args=()
        )
        self._event_detect_thread.daemon = True  # Daemonize thread
        self._event_detect_thread.start()  # Start the execution

    def _event_detect_run(self):

        while len(self._event_detect_list) != 0:
            # wait x seconds for each run
            time.sleep(self._event_detect_wait)

            # update GPIO cache, this will detect and handle rising/falling bits.
            with self._state_lock:
                self.hw_read_state()

        # self._event_detect_list[] has become 0 lenght,
        # so we are about to stop this thread, let's remove ourself:
        self._event_detect_thread = None

    def _handle_event_detected(self, xor_event_detect, raw_state):
        # log.debug("_handle_event_detected {0} xor_state[{1:08b}], raw_state[{2:08b}]".format( 'P3', xor_event_detect['P3'], raw_state['P3'] ))
        # log.debug("_handle_event_detected {0} xor_state[{1:08b}], raw_state[{2:08b}]".format( 'P7', xor_event_detect['P7'], raw_state['P7'] ))

        # itterate event_detect
        # do we need our event_detect_mask?
        for event in self._event_detect_list:
            gpio_port = event["gpio_port"]

            # lookup port in addr[], get state byte and bit position value
            (field, mask) = self._addr[gpio_port]
            # True if  bit position value = 1
            if xor_event_detect[field] | ~mask & 255 == 255:
                # True if new value match event value
                if event["value"] == (raw_state[field] | ~mask & 255 == 255):
                    # call callback in new thread:
                    log.debug(
                        "_handle_event_detected: start callback for {}, value {}".format(
                            gpio_port, event["value"]
                        )
                    )
                    threading.Thread(target=event["callback"], args=()).start()

    #
    # cleanup
    #
    def hw_exit(self):
        # close thread, remove all events
        self._event_detect_list = []
        self._event_detect_mask = {"P3": 0x00, "P7": 0x00}

        # join thread to wait for stop:
        if self._event_detect_thread:
            self._event_detect_thread.join()

    #
    # Debug and helper functions:
    #

    def debug(self):
        print(
            "DEBUG: P3 {0:08b}, P7 {1:08b}".format(self._state["P3"], self._state["P7"])
        )

    def debug_event_detect(self):
        """
        some debug overview on de the event_detect loop and configured callbacks
        """
        print(
            "DEBUG: number of event_detect callbacks: {}".format(
                len(self._event_detect_list)
            )
        )
        print("DEBUG: raw self._event_detect_mask: ", self._event_detect_mask)

        print(
            "DEBUG: event detect mask P3: {0:08b}".format(
                self._event_detect_mask.get("P3", 0)
            )
        )
        print(
            "DEBUG: event detect mask P7: {0:08b}".format(
                self._event_detect_mask.get("P7", 0)
            )
        )
        # if self._event_detect_mask.get('P7', None) is not None:
        # 	print("DEBUG: event detect mask P7: {1:08b}".format(self._event_detect_mask['P7']))

        # print("DEBUG: raw _event_detect_list:", self._event_detect_list)
        for event_info in self._event_detect_list:
            print(
                "..  gpio_port={} value={} callback={}".format(
                    event_info["gpio_port"], event_info["value"], event_info["callback"]
                )
            )

        print("DEBUG: raw self._event_detect_thread :", self._event_detect_thread)

    def debug_info(
        self,
    ):
        """
        some debug overview , handy when using bpython cli interface.
        """
        # get cfg if missing
        if "P3" not in self._cfg:
            self.hw_read_cfg()

        # read current IO values
        self.hw_read_cfg()

        with self._state_lock:
            self.hw_read_state()

            print("bin   ReadGPIO P3 {0:08b}".format(self._state["P3"]))
            print("bin   P3CFGA   P3 {0:08b}".format(self._cfg["P3"]["A"]))
            print("bin   P3CFGB   P3 {0:08b}".format(self._cfg["P3"]["B"]))

            print("bin   ReadGPIO P7 {0:08b}".format(self._state["P7"]))
            print("bin   P7CFGA   P7 {0:08b}".format(self._cfg["P7"]["A"]))
            print("bin   P7CFGB   P7 {0:08b}".format(self._cfg["P7"]["B"]))

        for p in ["p30", "p31", "p32", "p33", "p34", "p35", "p71", "p72"]:
            v = str(self.gpio_get(p))
            t = self.cfg_gpio_get(p)
            print(
                "GPIO port {} value {:5s} config: {}: {} ".format(
                    p, v, t, self.GPIO_TYPE[t]
                )
            )
