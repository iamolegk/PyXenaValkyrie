"""
Classes and utilities that represents Xena statistics as tables like the GUI.

Statistics views represent statistics as tables.
There are three different views - ports, streams and TPLD.

:author: yoram@ignissoft.com
"""

from collections import OrderedDict


class XenaStats(object):
    """ Base class for all statistics views. """

    def __init__(self, session):
        """
        :param session: current session
        :type session: xenamanager.xena_app.XenaSession
        """
        self.session = session

    def get_flat_stats(self):
        flat_stats = OrderedDict()
        for obj_name, port_stats in self.statistics.items():
            flat_obj_stats = OrderedDict()
            for group_name, group_values in port_stats.items():
                for stat_name, stat_value in group_values.items():
                    full_stat_name = group_name + '_' + stat_name
                    flat_obj_stats[full_stat_name] = stat_value
            flat_stats[obj_name] = flat_obj_stats
        return flat_stats


class XenaPortsStats(XenaStats):
    """ Ports statistics view.

    Represents all ports statistics as table:

    Port Name      | pt_total_pps | pt_total_packets | ...
    ---------------+--------------+------------------+----
    IP/Module/Port | value        | value            | ...
    IP/Module/Port | value        | value            | ...
    """

    def read_stats(self):
        """ Read current ports statistics from chassis.

        :return: dictionary <port name, <stat name, stat value>>
        """

        self.statistics = OrderedDict()
        for name, port in self.session.ports.items():
            self.statistics[name] = port.read_port_stats()
        return self.statistics


class XenaStreamsStats(XenaStats):
    """ Streams statistics view.

    Represents all streams statistics as table:

    Stream Full Index | pps   | packets | ...
    ------------------+-------+---------+----
    Module/Port/Index | value | value   | ...
    Module/Port/Index | value | value   | ...
    """

    def read_stats(self):
        """ Read current statistics from chassis.

        :return: dictionary <stream full index, <stat name, stat value>>
        """

        self.statistics = OrderedDict()
        for port in self.session.ports.values():
            for stream in port.streams.values():
                self.statistics[stream.ref] = stream.read_stats()
        return self.statistics


class XenaTpldsStats(XenaStats):
    """ TPLDs statistics view.

    Represents all TPLDs statistics as table:

    TPLD Full   Index | pr_tplderrors   | pr_tpldtraffic | ...
    ------------------+-----------------+----------------+----
    Module/Port/Index | value           | value          | ...
    Module/Port/Index | value           | value          | ...
    """

    def read_stats(self):
        """ Read current statistics from chassis.

        :return: dictionary <tpld full index, <stat name, stat value>>
        """

        self.statistics = OrderedDict()
        for port in self.session.ports.values():
            for tpld in port.tplds.values():
                self.statistics[tpld.ref] = tpld.read_stats()
        return self.statistics
