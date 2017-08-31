#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import os

from pyppeteer.launcher import launch
from syncer import sync

from wdom.document import get_document
from wdom.server import server_config, start_server, stop_server
from wdom.tests.util import TestCase


class BaseTestCase(TestCase):
    if os.getenv('TRAVIS', False):
        wait_time = 0.1
    else:
        wait_time = 0.05

    @classmethod
    def setUpClass(cls):
        cls.browser = launch({'headless': True})
        cls.page = sync(cls.browser.newPage())

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()

    def setUp(self):
        super().setUp()
        self.doc = get_document()
        self.root = self.get_elements()
        self.doc.body.prepend(self.root)
        self.server = start_server(port=0)
        self.address = server_config['address']
        self.port = server_config['port']
        self.url = 'http://{}:{}'.format(self.address, self.port)
        sync(self.page.goto(self.url))
        self.element = sync(self.get_element_handle(self.root))

    def tearDown(self):
        stop_server(self.server)
        # sync(self.page.goto('about:blank'))
        super().tearDown()

    def get_elements(self):
        raise NotImplementedError

    async def get_element_handle(self, elm):
        return await self.page.querySelector(
            '[rimo_id="{}"]'.format(elm.rimo_id))

    async def get_text(self):
        return await self.element.evaluate('(elm) => elm.textContent')

    async def wait(self, timeout=None):
        timeout = timeout or self.wait_time
        _t = timeout / 10
        for _ in range(10):
            await asyncio.sleep(_t)

    async def wait_for_element(self, elm):
        await self.page.waitForSelector(
            '[rimo_id="{}"]'.format(elm.rimo_id),
            {'timeout': 100},
        )
