#
# SPDX-FileCopyrightText: 2022 Mike Dunston (atanisoft)
#
# SPDX-License-Identifier: MIT
#

from org.openpnp.model import Configuration, Location
from org.openpnp.machine.reference import ReferenceActuator
from org.openpnp.machine.reference.driver import GcodeDriver
from org.openpnp.machine.reference.feeder import ReferenceSlotAutoFeeder
from org.openpnp.spi import Actuator
from org.openpnp.model import LengthUnit

# Position of the first feeder
feeder_starting_x = 0
feeder_starting_y = 0

# Offset to the next feeder
feeder_spacing_x = 15
feeder_spacing_y = 0

# Number of slotted feeders to create
feeder_count = 32

# When set to True all registered parts will have a feeder created in the
# default bank. This is not the same as a slotted feeder.
use_part_id_for_feeder = False

# Name of Actuator that will be used to advance the feeder forward by 2mm.
feed_actuator_2mm = 'FeederAdvance2MM'

# Name of Actuator that will be used to advance the feeder forward by 4mm.
feed_actuator_4mm = 'FeederAdvance4MM'

# Name of Actuator that will be used as post-pick movement for the feeders.
postpick_actuator = 'FeederPostPick'

# Name of the Gcode Driver to create for controlling the feeders.
gcode_driver = 'FeederDriver'

# Gcode commands for the Esp32FeederController
esp32_0816_feeder_advance_2mm = 'M610 N{IntegerValue}'
esp32_0816_feeder_advance_4mm = None
esp32_0816_feeder_postpick = 'M611 N{IntegerValue}'
esp32_0816_feeder_enable = None
esp32_0816_feeder_disable = None

# Gcode commands for the AVR based Feeder Controller
avr_0816_feeder_advance_2mm = 'M600 N{IntegerValue} F2'
avr_0816_feeder_advance_4mm = 'M600 N{IntegerValue} F4'
avr_0816_feeder_postpick = 'M601 N{IntegerValue}'
avr_0816_feeder_enable = 'M610 S1'
avr_0816_feeder_disable = 'M610 S0'

def find_slotted_feeder(name):
    for feeder in machine.getFeeders():
        if feeder.getName().startswith('{} ('.format(name)):
            return feeder
    return None

def find_or_create_slotted_feeder(name, bank):
    feeder = find_slotted_feeder(name)
    if not feeder:
        print('Creating SlottedFeeder \'{}\''.format(name))
        feeder = ReferenceSlotAutoFeeder()
        feeder.setName(name)
        feeder.setBank(bank)
        machine.addFeeder(feeder)
    else:
        print('Updating SlottedFeeder \'{}\''.format(feeder.getName()))
    return feeder

def find_feeder_in_bank(name, bank):
    for feeder in bank.getFeeders():
        if feeder.getName() == name:
            return feeder
    return None

def find_actuator_by_name(name):
    for act in machine.getActuators():
        if act.getName() == name:
            return act
    return None

def create_feeders_for_all_parts(bank):
    for part in Configuration.get().getParts():
        if not find_feeder_in_bank(part.getId(), bank):
            print('Creating feeder for part \'{}\''.format(part.getId()))
            feeder = ReferenceSlotAutoFeeder.Feeder()
            feeder.setName(part.getId())
            feeder.setPart(part)
            bank.getFeeders().add(feeder)

def create_slotted_feeders(count, start_x, start_y, offset_x, offset_y, feed_actuator):
    # Get (or create) the default bank for the feeders.
    bank = ReferenceSlotAutoFeeder.getBanks()[0]
    # Create N feeders ReferenceSlotAutoFeeder
    for id in range(0, count):
        slot = find_or_create_slotted_feeder('SLOT-{}'.format(id), bank)
        slot.setLocation(Location(LengthUnit.Millimeters, start_x + (offset_x * id), start_y + (offset_y * id), 0, 0))
        slot.setActuatorName(feed_actuator)
        slot.setActuatorValue(id)
        slot.setPostPickActuatorName(postpick_actuator)
        slot.setPostPickActuatorValue(id)

def find_or_create_0816_actuator(name, driver):
    act = find_actuator_by_name(name)
    if not act:
        print('Creating Actuator \'{}\''.format(name))
        act = ReferenceActuator()
        act.setValueType(Actuator.ActuatorValueType.Double)
        act.setName(name)
        act.setDriver(driver)
        machine.addActuator(act)
    return act

def find_or_create_0816_gcode_driver(driver_name):
    target_driver = None
    for driver in machine.getDrivers():
        if driver.getName() == driver_name:
            target_driver = driver
    if not target_driver:
        print('Creating GCode driver \'{}\''.format(driver_name))
        target_driver = GcodeDriver()
        target_driver.setName(driver_name)
        machine.addDriver(target_driver)
    return target_driver

def configure_0816_feeder_gcode(driver_name, advance_gcode_2mm, advance_gcode_4mm, postpick_gcode, enable_gcode = None, disable_gcode = None):
    driver = find_or_create_0816_gcode_driver(driver_name)
    if advance_gcode_2mm != None and len(advance_gcode_2mm) > 0:
        act = find_or_create_0816_actuator(feed_actuator_2mm, driver)
        print('{}: Setting Gcode for Actuator \'{}\''.format(driver_name, feed_actuator_2mm))
        driver.setCommand(act, GcodeDriver.CommandType.ACTUATE_DOUBLE_COMMAND, advance_gcode_2mm)
    if advance_gcode_4mm != None and len(advance_gcode_4mm) > 0:
        act = find_or_create_0816_actuator(feed_actuator_4mm, driver)
        print('{}: Setting Gcode for Actuator \'{}\''.format(driver_name, feed_actuator_4mm))
        driver.setCommand(act, GcodeDriver.CommandType.ACTUATE_DOUBLE_COMMAND, advance_gcode_4mm)
    postpick_act = find_or_create_0816_actuator(postpick_actuator, driver)
    print('{}: Setting Gcode for Actuator \'{}\''.format(driver_name, postpick_actuator))
    driver.setCommand(postpick_act, GcodeDriver.CommandType.ACTUATE_DOUBLE_COMMAND, postpick_gcode)
    print('{}: Setting Gcode COMMAND_CONFIRM_REGEX'.format(driver_name))
    driver.setCommand(None, GcodeDriver.CommandType.COMMAND_CONFIRM_REGEX, '^ok.*')
    print('{}: Setting Gcode COMMAND_ERROR_REGEX'.format(driver_name))
    driver.setCommand(None, GcodeDriver.CommandType.COMMAND_ERROR_REGEX, '^error.*')
    if enable_gcode:
        print('{}: Setting Gcode ENABLE_COMMAND'.format(driver_name))
        driver.setCommand(None, GcodeDriver.CommandType.ENABLE_COMMAND, enable_gcode)
    if disable_gcode:
        print('{}: Setting Gcode DISABLE_COMMAND'.format(driver_name))
        driver.setCommand(None, GcodeDriver.CommandType.DISABLE_COMMAND, disable_gcode)

configure_0816_feeder_gcode(gcode_driver, avr_0816_feeder_advance_2mm, avr_0816_feeder_advance_4mm,
    avr_0816_feeder_postpick, avr_0816_feeder_enable, avr_0816_feeder_disable)
create_slotted_feeders(feeder_count, feeder_starting_x, feeder_starting_y, feeder_spacing_x, feeder_spacing_y, feed_actuator_4mm)

bank = ReferenceSlotAutoFeeder.getBanks()[0]
if use_part_id_for_feeder:
    create_feeders_for_all_parts(bank)
else:
    for id in range(0, feeder_count):
        name = 'Feeder-{}'.format(id)
        feeder = find_feeder_in_bank(name, bank)
        if not feeder:
            print('Creating feeder \'{}\''.format(name))
            feeder = ReferenceSlotAutoFeeder.Feeder()
            feeder.setName(name)
            feeder.setPart(Configuration.get().getPart('HOMING-FIDUCIAL'))
            bank.getFeeders().add(feeder)
        bank.setFeeder(find_slotted_feeder('SLOT-{}'.format(id)), feeder)