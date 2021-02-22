"""
Tests that does not require online ports - configurations etc.

@author yoram@ignissoft.com
"""
import logging
from pathlib import Path

from pypacker.layer12.ethernet import Ethernet, Dot1Q
from pypacker.layer3.ip import IP
from pypacker.layer3.ip6 import IP6
from pypacker.layer4.tcp import TCP
from pypacker.layer4.udp import UDP
from trafficgenerator.tgn_utils import ApiType

from xenavalkyrie.xena_app import XenaApp
from xenavalkyrie.xena_filter import XenaFilterState
from xenavalkyrie.xena_stream import XenaModifierAction
from xenavalkyrie.xena_stream import XenaStream


def test_hello_world(xm: XenaApp) -> None:
    """ Just make sure the setup is up and running. """
    pass


def test_inventory(xm: XenaApp, logger: logging.Logger) -> None:
    """ Read entire chassis inventory. """
    logger.info(test_inventory.__doc__.strip())

    xm.session.inventory()
    print('+++')
    for c_name, chassis in xm.session.chassis_list.items():
        print(c_name)
        for m_name, module in chassis.modules.items():
            print(f'\tmodule {m_name}')
            for p_name, port in module.ports.items():
                print(f'\t\tport {p_name}')
                for s_name, _ in port.streams.items():
                    print(f'\t\t\tstream {s_name}')
    print('+++')
    save_config = Path(__file__).parent.joinpath('configs/save_config.xmc')
    list(xm.session.chassis_list.values())[0].save_config(save_config)


def test_load_config(xm: XenaApp, locations: list, logger: logging.Logger) -> None:
    """ Load configuration and test various children and attributes. """
    logger.info(test_load_config.__doc__.strip())

    XenaStream.next_tpld_id = 0
    xm.session.reserve_ports(locations)
    port = list(xm.session.ports.values())[0]
    port.load_config(Path(__file__).parent.joinpath('configs', 'test_config_1.xpc'))

    assert len(port.streams) == 2
    assert XenaStream.next_tpld_id == 2

    packet = port.streams[0].get_packet_headers()
    assert packet.dst_s == '22:22:22:22:22:11'
    assert packet.upper_layer.dst_s == '2.2.2.1'
    packet.dst_s = '33:33:33:33:33:33'
    packet.upper_layer.dst_s = '3.3.3.3'
    port.streams[0].set_packet_headers(packet)
    packet = port.streams[0].get_packet_headers()
    assert packet.dst_s == '33:33:33:33:33:33'
    assert packet.upper_layer.dst_s == '3.3.3.3'

    packet = port.streams[1].get_packet_headers()
    assert packet.dst_s == '22:22:22:22:22:22'
    assert packet.upper_layer.dst_s == '22::22'
    packet.upper_layer.dst_s = u'33::33'
    port.streams[1].set_packet_headers(packet)
    packet = port.streams[1].get_packet_headers()
    assert packet.upper_layer.dst_s == '33::33'

    assert len(port.streams[0].modifiers) == 1
    assert port.streams[0].modifiers[0].action == XenaModifierAction.increment
    assert len(port.streams[1].modifiers) == 1
    assert port.streams[1].modifiers[0].action == XenaModifierAction.random
    modifier1 = port.streams[0].modifiers[0]
    assert modifier1.min_val == 0
    modifier2 = port.streams[0].add_modifier(position=12)
    assert len(port.streams[0].modifiers) == 2
    assert modifier2.position == 12

    port.streams[0].remove_modifier(0)
    assert port.streams[0].modifiers[0].max_val == 65535


def test_build_config(xm: XenaApp, locations: list, logger: logging.Logger) -> None:
    """ Build configuration and then read and test the configuration. """
    logger.info(test_build_config.__doc__.strip())

    XenaStream.next_tpld_id = 0
    xm.session.reserve_ports(locations)
    port = list(xm.session.ports.values())[0]

    assert XenaStream.next_tpld_id == 0
    assert len(port.streams) == 0
    assert port.get_attribute('ps_indices') == ''

    stream = port.add_stream('first stream')
    assert stream.get_attribute('ps_comment') == 'first stream'
    assert stream.get_attribute('ps_tpldid') == '0'
    assert XenaStream.next_tpld_id == 1
    assert len(port.streams) == 1

    stream = port.add_stream(tpld_id=7)
    assert stream.get_attribute('ps_tpldid') == '7'
    assert XenaStream.next_tpld_id == 8
    assert len(port.streams) == 2

    if xm.api == ApiType.rest:
        return

    match = port.add_match()
    # Order matters
    match.set_attributes(pm_protocol='ETHERNET VLAN')
    match.set_attributes(pm_position=14)
    match.set_attributes(pm_match='0x0FFF000000000000 0x0064000000000000')
    assert len(port.matches) == 1

    filter = port.add_filter(comment='New Filter')
    filter.set_attributes(pf_condition='0 0 0 0 1 0')
    filter.set_state(XenaFilterState.on)
    assert filter.get_attribute('pf_comment') == 'New Filter'
    assert len(port.filters) == 1

    length = port.add_length()
    assert len(port.lengthes) == 1

    port.remove_length(0)
    assert len(port.lengthes) == 0
    port.remove_filter(0)
    assert len(port.filters) == 0
    port.remove_match(0)
    assert len(port.matches) == 0

    port.remove_stream(0)
    assert len(port.streams) == 1
    assert port.streams.get(1)
    assert port.get_attribute('ps_indices').split()[0] == '1'

    save_file = Path(__file__).parent.joinpath('temp', 'save_config.xpc')
    port.save_config(save_file.as_posix())
    assert save_file.exists()


def test_layer_4_headers(xm: XenaApp, locations: list, logger: logging.Logger) -> None:
    """ Build stream with layer 4 configuration then read and test the configuration. """
    logger.info(test_layer_4_headers.__doc__.strip())

    xm.session.reserve_ports(locations)
    port = list(xm.session.ports.values())[0]

    tcp_stream = port.add_stream('tcp stream')

    eth = Ethernet(src_s='22:22:22:22:22:22')
    eth.dst_s = '11:11:11:11:11:11'
    vlan = Dot1Q(vid=17, prio=3)
    eth.vlan.append(vlan)
    ip = IP()
    tcp = TCP()
    headers = eth + ip + tcp
    tcp_stream.set_packet_headers(headers, l4_checksum=False)
    headerprotocol = tcp_stream.get_attribute('ps_headerprotocol')
    assert 'tcpcheck' not in headerprotocol.lower()
    tcp_stream.set_packet_headers(headers, l4_checksum=True)
    headerprotocol = tcp_stream.get_attribute('ps_headerprotocol')
    assert 'tcpcheck' in headerprotocol.lower()
    resulting_headers = tcp_stream.get_packet_headers()
    l4 = resulting_headers.upper_layer.upper_layer
    assert l4.sum == 0

    #: :type udp_stream: xenavalkyrie.xena_stream.XenaStream
    udp_stream = port.add_stream('udp stream')

    eth = Ethernet(src_s='44:44:44:44:44:44')
    eth.dst_s = '33:33:33:33:33:33'
    ip6 = IP6()
    udp = UDP()
    headers = eth + ip6 + udp
    udp_stream.set_packet_headers(headers, l4_checksum=False)
    headerprotocol = udp_stream.get_attribute('ps_headerprotocol')
    assert 'udpcheck' not in headerprotocol.lower()
    udp_stream.set_packet_headers(headers, l4_checksum=True)
    headerprotocol = udp_stream.get_attribute('ps_headerprotocol')
    assert 'udpcheck' in headerprotocol.lower()
    resulting_headers = udp_stream.get_packet_headers()
    l4 = resulting_headers.upper_layer.upper_layer
    assert l4.sum == 0


# def test_rest_server(self):
#
#     if self.api == ApiType.rest:
#         pytest.skip('Skip test - REST API')
#
#     if is_local_host(self.server_ip):
#         pytest.skip('Skip test - localhost')
#
#     #: :type chassis: xenavalkyrie.xena_app.XenaChassis
#     chassis = self.xm.session.chassis_list[self.chassis]
#     chassis.reserve()
#
#     chassis.set_attributes(c_restport=self.server_port)
#     assert int(chassis.get_attribute('c_restport')) == self.server_port)
#     assert chassis.get_attribute('c_reststatus').lower() == 'service_on')
#     assert chassis.get_attribute('c_restenable').lower() == 'on')
#     base_url = 'http://{}:{}'.format(self.server_ip, self.server_port)
#     requests.get(base_url)
#     chassis.set_attributes(c_restport=self.server_port + 10)
#     chassis.set_attributes(c_restcontrol='restart')
#     assert chassis.get_attribute('c_reststatus').lower() == 'service_on')
#     assert int(chassis.get_attribute('c_restport')) == self.server_port + 10)
#     base_url = 'http://{}:{}'.format(self.server_ip, self.server_port + 10)
#     requests.get(base_url)
#     chassis.set_attributes(c_restport=self.server_port)
#     chassis.set_attributes(c_restcontrol='stop')
#     assert chassis.get_attribute('c_reststatus').lower() == 'service_off')
#     base_url = 'http://{}:{}'.format(self.server_ip, self.server_port)
#     with pytest.raises(Exception) as _:
#         requests.get(base_url)
#     chassis.set_attributes(c_restcontrol='start')
#     assert chassis.get_attribute('c_reststatus').lower() == 'service_on')
#     requests.get(base_url)
#
#     chassis.set_attributes(c_restenable='off')
#     assert chassis.get_attribute('c_restenable').lower() == 'off')
#     chassis.shutdown(restart=True, wait=True)
#     assert chassis.get_attribute('c_restenable').lower() == 'off')
#     with pytest.raises(Exception) as _:
#         requests.get(base_url)
#     chassis.reserve()
#     chassis.set_attributes(c_restenable='on')
#     assert chassis.get_attribute('c_restenable').lower() == 'on')
#     chassis.shutdown(restart=True, wait=True)
#     assert chassis.get_attribute('c_restenable').lower() == 'on')
#     requests.get(base_url)


# def test_extended_modifiers(self):
#     try:
#         port = self.xm.session.reserve_ports([self.port3])[self.port3]
#     except Exception as e:
#         pytest.skip('Skip test - ' + str(e))
#     port.load_config(path.join(path.dirname(__file__), 'configs', 'test_config_100G.xpc'))
#
#     assert len(port.streams[0].modifiers) == 1)
#     #: :type modifier1: xenavalkyrie.xena_strea.XenaModifier
#     modifier1 = port.streams[0].modifiers[0]
#     assert modifier1.min_val == 0)
#     print(modifier1)
#     #: :type modifier2: xenavalkyrie.xena_strea.XenaXModifier
#     modifier2 = port.streams[0].add_modifier(m_type=XenaModifierType.extended, position=12)
#     assert len(port.streams[0].modifiers) == 1)
#     assert len(port.streams[0].xmodifiers) == 1)
#     assert modifier2.position == 12)
#     print(modifier2)
#
#     port.streams[0].remove_modifier(0)
#     assert len(port.streams[0].modifiers) == 0)
#     assert len(port.streams[0].xmodifiers) == 1)
#     port.streams[0].remove_modifier(0, m_type=XenaModifierType.extended)
#     assert len(port.streams[0].xmodifiers) == 0)
