"""
Base class for all Xena package tests.

@author yoram@ignissoft.com
"""

from os import path

from trafficgenerator.tgn_utils import ApiType
from trafficgenerator.test.test_tgn import TgnTest
from xenamanager.xena_app import init_xena
from xenamanager.xena_stream import XenaStream


class XenaTestBase(TgnTest):

    TgnTest.config_file = path.join(path.dirname(__file__), 'XenaManager.ini')

    def setUp(self):
        super(XenaTestBase, self).setUp()
        self.xm = init_xena(ApiType[self.config.get('Xena', 'api')], self.logger, self.config.get('Xena', 'owner'))
        self.xm.session.add_chassis(self.config.get('Xena', 'chassis'))
        self.port1 = self.config.get('Xena', 'port1')
        self.port2 = self.config.get('Xena', 'port2')
        XenaStream.next_tpld_id = 0

    def tearDown(self):
        self.xm.logoff()

    def test_hello_world(self):
        pass
