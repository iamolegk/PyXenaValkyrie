"""
Classes and utilities that represents Xena XenaManager-2G stream.

:author: yoram@ignissoft.com
"""

import re
import binascii
from enum import Enum
from collections import OrderedDict

from pypacker.layer12 import ethernet

from xenamanager.xena_object import XenaObject


class XenaModifierType(Enum):
    standard = 0
    extended = 1


class XenaModifierAction(Enum):
    increment = 'INC'
    decrement = 'DEC'
    random = 'RANDOM'


class XenaStream(XenaObject):

    stats_captions = ['bps', 'pps', 'bytes', 'packets']

    def __init__(self, parent, index):
        """
        :param parent: parent port object.
        :param index: stream index in format module/port/stream.
        """

        super(self.__class__, self).__init__(objType='stream', index=index, parent=parent)

    def build_index_command(self, command, *arguments):
        module, port, sid = self.ref.split('/')
        return ('{}/{} {} [{}]' + len(arguments) * ' {}').format(module, port, command, sid, *arguments)

    def extract_return(self, command, index_command_value):
        module, port, sid = self.ref.split('/')
        return re.sub('{}/{}\s*{}\s*\[{}\]\s*'.format(module, port, command.upper(), sid), '', index_command_value)

    def get_index_len(self):
        return 2

    def get_command_len(self):
        return 1

    def read_stats(self):
        """
        :return: dictionary {stat name: value}
            Sea XenaStream.stats_captions
        """
        return self.read_stat(self.stats_captions, 'pt_stream')

    def get_packet_headers(self):
        """
        :return: current packet headers
        :rtype: pypacker.layer12.ethernet
        """

        bin_headers = self.get_attribute('ps_packetheader')
        return ethernet.Ethernet(binascii.unhexlify(bin_headers[2:]))

    def set_packet_headers(self, headers):
        """
        :param headers: current packet headers
        :type headers: pypacker.layer12.ethernet
        """

        bin_headers = '0x' + binascii.hexlify(headers.bin()).decode('utf-8')
        self.set_attribute('ps_packetheader', bin_headers)

    #
    # Modifiers.
    #

    def add_modifier(self, m_type=XenaModifierType.standard, **kwargs):
        """ Add modifier.

        :param m_type: modifier type - standard or extended.
        :type: xenamanager.xena_stram.ModifierType
        :return: newly created modifier.
        :rtype: xenamanager.xena_stream.XenaModifier
        """

        modifier_index = len(self.modifiers)
        if m_type == XenaModifierType.standard:
            modifier_index = len(self.standard_modifiers)
            self.set_attribute('ps_modifiercount', modifier_index + 1)
        else:
            modifier_index = len(self.extended_modifiers)
            self.set_attribute('ps_modifierextcount', modifier_index + 1)
        modifier = XenaModifier(self, index='{}/{}'.format(self.ref, modifier_index), m_type=m_type)
        modifier.set(**kwargs)
        return modifier

    def remove_modifier(self, position):
        """ Remove modifier.

        :param position: position of modifier to remove.
        """

        current_modifiers = OrderedDict(self.modifiers)
        del current_modifiers[position]

        self.set_attribute('ps_modifiercount', 0)
        try:
            self.set_attribute('ps_modifierextcount', 0)
        except Exception as _:
            pass
        self.del_objects_from_parent('modifier')

        for modifier in current_modifiers.values():
            self.add_modifier(modifier.m_type, position=modifier.position).set(mask=modifier.mask,
                                                                               action=modifier.action,
                                                                               repeat=modifier.repeat,
                                                                               min_val=modifier.min_val,
                                                                               step=modifier.step,
                                                                               max_val=modifier.max_val)

    #
    # Properties.
    #

    @property
    def modifiers(self):
        """
        :return: dictionary {position: object} of all modifiers.
        """

        if not self.get_objects_by_type('modifier'):
            for index in range(int(self.get_attribute('ps_modifiercount'))):
                XenaModifier(self, index='{}/{}'.format(self.ref, index), m_type=XenaModifierType.standard)
            try:
                for index in range(int(self.get_attribute('ps_modifierextcount'))):
                    XenaModifier(self, index='{}/{}'.format(self.ref, index), m_type=XenaModifierType.extended)
            except Exception as _:
                pass
        return {m.position: m for m in self.get_objects_by_type('modifier')}

    @property
    def standard_modifiers(self):
        """
        :return: dictionary {position: object} of standard modifiers.
        """
        return {p: m for p, m in self.modifiers.items() if m.m_type == XenaModifierType.standard}

    @property
    def extended_modifiers(self):
        """
        :return: dictionary {position: object} of extended modifiers.
        """
        return {p: m for p, m in self.modifiers.items() if m.m_type == XenaModifierType.standard}


class XenaModifier(XenaObject):

    def __init__(self, parent, index, m_type):
        """
        :param parent: parent stream object.
        :param index: modifier index in format module/port/stream/modifier.
        :param m_type: modifier type - standard or extended.
        :type: xenamanager.xena_stram.ModifierType
        """

        module, port, sid = parent.ref.split('/')
        self.mid = index.split('/')[-1]
        command = 'ps_modifier' if m_type == XenaModifierType.standard else 'ps_modifierext'
        reply = parent.api.sendQuery('{}/{} {} [{},{}] ?'.format(module, port, command, sid, self.mid))

        index = '/'.join(index.split('/')[:-1]) + '/' + reply.split()[-4]
        super(self.__class__, self).__init__(objType='modifier', index=index, parent=parent)
        self.m_type = m_type
        self.get()

    def to_dict(self):
        return str({v: getattr(self, v) for v in
                    ['m_type', 'position', 'action', 'repeat', 'min_val', 'step', 'max_val', 'mask']})

    def build_index_command(self, command, *arguments):
        module, port, sid, _ = self.ref.split('/')
        return ('{}/{} {} [{},{}]' + len(arguments) * ' {}').format(module, port, command, sid, self.mid, *arguments)

    def extract_return(self, command, index_command_value):
        module, port, sid, _ = self.ref.split('/')
        return re.sub('{}/{}\s*{}\s*\[{},{}\]\s*'.
                      format(module, port, command.upper(), sid, self.mid), '', index_command_value)

    def get_index_len(self):
        return 2

    def get_command_len(self):
        return 1

    def set(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.m_type == XenaModifierType.standard:
            self.set_attribute('ps_modifier', '{} {} {} {}'.format(self.position, self.mask,
                                                                   self.action.value, self.repeat))
        else:
            self.set_attribute('ps_modifierext', '{} {} {} {}'.format(self.position, self.mask,
                                                                      self.action.value, self.repeat))
        if self.action != XenaModifierAction.random:
            if self.m_type == XenaModifierType.standard:
                self.set_attribute('ps_modifierrange', '{} {} {}'.format(self.min_val, self.step, self.max_val))
            else:
                self.set_attribute('ps_modifierextrange', '{} {} {}'.format(self.min_val, self.step, self.max_val))

    def get(self):
        if self.m_type == XenaModifierType.standard:
            position, mask, action, repeat = self.get_attribute('ps_modifier').split()
        else:
            position, mask, action, repeat = self.get_attribute('ps_modifierext').split()
        self.position = int(position)
        self.mask = '0x{:x}'.format(int(mask, 16))
        self.action = XenaModifierAction(action)
        self.repeat = int(repeat)
        if self.action != XenaModifierAction.random:
            if self.m_type == XenaModifierType.standard:
                min_val, step, max_val = self.get_attribute('ps_modifierrange').split()
            else:
                min_val, step, max_val = self.get_attribute('ps_modifierextrange').split()
            self.min_val = int(min_val)
            self.step = int(step)
            self.max_val = int(max_val)
