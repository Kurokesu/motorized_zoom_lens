# -*- coding: utf-8 -*-

__author__      = "Saulius Lukse"
__copyright__   = "Copyright 2016, kurokesu.com"
__version__     = "0.1"
__license__     = "GPL"

'''
Future ideas:
 * Remember last lens position inside controller
 * Read position while moving
 * Move Focus/Zoom axis simultaneously
'''

from enum import Enum


# -------------------------------------------
#             LV8044 enumerations
# -------------------------------------------
class e_mode(Enum):
    PHASE_2         = 0b00
    PHASE_12FULL    = 0b01
    PHASE_12        = 0b10
    PHASE_4W        = 0b11


class e_current(Enum):
    C_100           = 0b00
    C_67            = 0b01
    C_50            = 0b10
    C_33            = 0b11


class e_direction(Enum):
    CW              = 0
    CCW             = 1


class e_hold(Enum):
    CANCEL          = 0
    HOLD            = 1


class e_counter(Enum):
    RESET           = 0
    CANCEL          = 1


class e_output(Enum):
    OFF             = 0
    ON              = 1


class e_pwm_microstep(Enum):
    PWM             = 0
    MICROSTEP          = 1


class e_pwm_direction(Enum):
    OFF             = 0b00
    OUTAB           = 0b01
    OUTBA           = 0b10
    BRAKE           = 0b11


class e_ch34_pwm_decay(Enum):
    BRAKE           = 0
    STANDBY         = 1


class e_ch(Enum):
    CH5             = 0
    CH6             = 1


class e_voltage(Enum):
    V0300             = 0b0000
    V0200             = 0b1000
    V0190             = 0b0100
    V0180             = 0b1100
    V0170             = 0b0010
    V0165             = 0b1010
    V0160             = 0b0110
    V0155             = 0b1110
    V0150             = 0b0001
    V0145             = 0b1001
    V0140             = 0b0101
    V0135             = 0b1101
    V0130             = 0b0011
    V0120             = 0b1011
    V0110             = 0b0111
    V0100             = 0b1111


class e_pi_drive(Enum):
    OFF               = 0
    ON                = 1


class e_pi3_mo(Enum):
    PI3               = 0
    MO                = 1


class e_mo_ch(Enum):
    CH12              = 0
    CH34              = 1


class e_mo_position(Enum):
    INITIAL           = 0
    PHASE12           = 1


class e_freq(Enum):
    F130             = 0b00
    F065             = 0b01
    F200             = 0b10
    F100             = 0b11


# -------------------------------------------
#             Bit manipulation
# -------------------------------------------
def test(val, offset):
    mask = 1 << offset
    return (val & mask)


def test_logic(val, offset):
    mask = 1 << offset
    return (val & mask)>>offset


def set(val, offset):
    mask = 1 << offset
    return (val | mask)


def clear(val, offset):
    mask = ~(1 << offset)
    return val & mask


def toggle(val, offset):
    mask = 1 << offset
    return val ^ mask


def replace(val, bit, offset):
    if bit == 1:
        mask = 1 << offset
        return val | mask
    elif bit == 0:
        mask = ~(1 << offset)
        return val & mask


def reverse(val):
    ret = 0
    for i in xrange(8):
        B = test_logic(val, i)
        ret = replace(ret, B, 7-i)
    return ret


def to_binary(n):
    return ''.join(str(1 & int(n) >> i) for i in range(8)[::-1])


# -----------------------------------------------------------------------------------
#             LV8044 class
# -----------------------------------------------------------------------------------
class LV8044:
    # -------------------------------------------------------------------------------
    def __init__(self):
        self.config = [	0b00000000, # B0
                           0b00000001, # B1
                           0b10000010, # B2, D7 = microstep
                           0b00000011, # B3
                           0b00000100, # B4
                           0b00000101, # B5
                           0b00000110, # B6
                           0b00000111] # B7

    # -------------------------------------------------------------------------------
    def ch12_1(	self,
                mode=None,
                current=None):

        if mode != None:
            B0 = test_logic(mode.value, 0)
            B1 = test_logic(mode.value, 1)
            self.config[0] = replace(self.config[0], B0, 3)
            self.config[0] = replace(self.config[0], B1, 4)

        if current != None:
            B0 = test_logic(current.value, 0)
            B1 = test_logic(current.value, 1)
            self.config[0] = replace(self.config[0], B0, 5)
            self.config[0] = replace(self.config[0], B1, 6)

        return self.config[0]

    # -------------------------------------------------------------------------------
    def ch12_2(	self,
                direction=None,
                hold=None,
                counter_reset=None,
                output=None):

        if direction != None:
            B0 = test_logic(direction.value, 0)
            self.config[1] = replace(self.config[1], B0, 3)

        if hold != None:
            B0 = test_logic(hold.value, 0)
            self.config[1] = replace(self.config[1], B0, 4)

        if counter_reset != None:
            B0 = test_logic(counter_reset.value, 0)
            self.config[1] = replace(self.config[1], B0, 5)

        if output != None:
            B0 = test_logic(output.value, 0)
            self.config[1] = replace(self.config[1], B0, 6)

        return self.config[1]

    # -------------------------------------------------------------------------------
    def ch34_1(	self,
                mode=None,
                current=None,
                pwm_microstep=None):

        if mode != None:
            B0 = test_logic(mode.value, 0)
            B1 = test_logic(mode.value, 1)
            self.config[2] = replace(self.config[2], B0, 3)
            self.config[2] = replace(self.config[2], B1, 4)

        if current != None:
            B0 = test_logic(current.value, 0)
            B1 = test_logic(current.value, 1)
            self.config[2] = replace(self.config[2], B0, 5)
            self.config[2] = replace(self.config[2], B1, 6)

        if pwm_microstep != None:
            B0 = test_logic(pwm_microstep.value, 0)
            self.config[2] = replace(self.config[2], B0, 7)

        return self.config[2]

    # -------------------------------------------------------------------------------
    def ch34_2(	self,
                pwm_ch3_direction=None,
                pwm_ch4_direction=None,
                pwm_decay=None,
                direction=None,
                hold=None,
                counter_reset=None,
                output=None):

        # For PWM group
        if pwm_ch3_direction != None:
            B0 = test_logic(pwm_ch3_direction.value, 0)
            B1 = test_logic(pwm_ch3_direction.value, 1)
            self.config[3] = replace(self.config[3], B0, 3)
            self.config[3] = replace(self.config[3], B1, 4)

        if pwm_ch4_direction != None:
            B0 = test_logic(pwm_ch4_direction.value, 0)
            B1 = test_logic(pwm_ch4_direction.value, 1)
            self.config[3] = replace(self.config[3], B0, 5)
            self.config[3] = replace(self.config[3], B1, 6)

        if pwm_decay != None:
            B0 = test_logic(pwm_decay.value, 0)
            self.config[3] = replace(self.config[3], B0, 7)

        # For MICROSTEP group
        if direction != None:
            B0 = test_logic(direction.value, 0)
            self.config[3] = replace(self.config[3], B0, 3)

        if hold != None:
            B0 = test_logic(hold.value, 0)
            self.config[3] = replace(self.config[3], B0, 4)

        if counter_reset != None:
            B0 = test_logic(counter_reset.value, 0)
            self.config[3] = replace(self.config[3], B0, 5)

        if output != None:
            B0 = test_logic(output.value, 0)
            self.config[3] = replace(self.config[3], B0, 6)

        return self.config[3]

    # -------------------------------------------------------------------------------
    def ch56_1(	self,
                pwm_ch5_direction=None,
                pwm_ch6_direction=None):

        if pwm_ch5_direction != None:
                B0 = test_logic(pwm_ch5_direction.value, 0)
                B1 = test_logic(pwm_ch5_direction.value, 1)
                self.config[4] = replace(self.config[4], B0, 3)
                self.config[4] = replace(self.config[4], B1, 4)

        if pwm_ch6_direction != None:
                B0 = test_logic(pwm_ch6_direction.value, 0)
                B1 = test_logic(pwm_ch6_direction.value, 1)
                self.config[4] = replace(self.config[4], B0, 5)
                self.config[4] = replace(self.config[4], B1, 6)

        return self.config[4]

    # -------------------------------------------------------------------------------
    def ch56_2(	self,
                ch=None,
                voltage=None):

        if ch != None:
            B0 = test_logic(ch.value, 0)
            self.config[5] = replace(self.config[5], B0, 3)

        if voltage != None:
            B0 = test_logic(voltage.value, 0)
            B1 = test_logic(voltage.value, 1)
            B2 = test_logic(voltage.value, 2)
            B3 = test_logic(voltage.value, 3)
            self.config[5] = replace(self.config[5], B0, 7)
            self.config[5] = replace(self.config[5], B1, 6)
            self.config[5] = replace(self.config[5], B2, 5)
            self.config[5] = replace(self.config[5], B3, 4)

        return self.config[5]

    # -------------------------------------------------------------------------------
    def chPI_1(	self,
                ch1_sensor_drive=None,
                ch2_sensor_drive=None,
                ch3_sensor_drive=None):

        if ch1_sensor_drive != None:
            B0 = test_logic(ch1_sensor_drive.value, 0)
            self.config[6] = replace(self.config[6], B0, 3)

        if ch2_sensor_drive != None:
            B0 = test_logic(ch2_sensor_drive.value, 0)
            self.config[6] = replace(self.config[6], B0, 4)

        if ch3_sensor_drive != None:
            B0 = test_logic(ch3_sensor_drive.value, 0)
            self.config[6] = replace(self.config[6], B0, 5)

        return self.config[6]

    # -------------------------------------------------------------------------------
    def chPI_2(	self,
                pi3_mo_select=None,
                mo_ch=None,
                mo_position=None,
                frequency=None):

        if pi3_mo_select != None:
            B0 = test_logic(pi3_mo_select.value, 0)
            self.config[7] = replace(self.config[7], B0, 3)

        if mo_ch != None:
            B0 = test_logic(mo_ch.value, 0)
            self.config[7] = replace(self.config[7], B0, 4)

        if mo_position != None:
            B0 = test_logic(mo_position.value, 0)
            self.config[7] = replace(self.config[7], B0, 5)

        if frequency != None:
            B0 = test_logic(frequency.value, 0)
            B1 = test_logic(frequency.value, 1)
            self.config[7] = replace(self.config[7], B0, 6)
            self.config[7] = replace(self.config[7], B1, 7)

        return self.config[7]

    # -------------------------------------------------------------------------------
    def get_config(self):
        return self.config

if __name__ == "__main__":
    e = LV8044()

    val = e.ch12_2(output=e_output.ON)
    #val = e.ch34_1(mode=e_mode.PHASE_12, current=e_current.C_100, pwm_microstep=e_pwm_microstep.MICROSTEP)
    #val = e.ch34_2(pwm_ch4_direction=e_pwm_direction.OUTAB)
    #val = e.ch56_1(pwm_ch5_direction=e_pwm_direction.OUTAB)
    #val = e.ch56_2(ch=e_ch.CH5, voltage=e_voltage.V0200)
    #val = e.chPI_1(ch3_sensor_drive=e_pi_drive.ON)
    #val = e.chPI_2(frequency=e_freq.F200)

    val = reverse(val)
    print 'val:', val, to_binary(val)
