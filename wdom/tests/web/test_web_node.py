#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from copy import deepcopy
import asyncio
from unittest.mock import MagicMock

from wdom.document import get_document
from wdom.server import get_app, Application
from wdom.misc import static_dir, install_asyncio
from wdom.web_node import WebElement
from wdom.tests.web.remote_browser import WDTest, NoSuchElementException


def setup_module():
    install_asyncio()


class ElementTestCase(WDTest):
    def setUp(self):
        self.document = get_document(autoreload=False)
        self.document.set_body(self.get_elements())
        super().setUp()

    def get_elements(self):
        raise NotImplementedError


class TestWebElement(ElementTestCase):
    def get_elements(self):
        self.root = WebElement('div')
        self.tag = WebElement('span', parent=self.root)
        return self.root

    def test_connection(self):
        self.assertTrue(self.root.connected)
        self.get('http://example.com/')
        self.assertIsFalse(self.root.connected)

    def test_text_content(self):
        self.set_element(self.tag)
        self.assertEqual(self.get_text(), '')
        self.tag.textContent = 'text'
        self.assertEqual(self.get_text(), 'text')

        child = WebElement('a')
        child.textContent = 'child'
        self.tag.appendChild(child)
        self.assertEqual(self.get_text(), 'textchild')

        self.tag.textContent = 'NewText'
        self.assertEqual(self.get_text(), 'NewText')
        with self.assertRaises(NoSuchElementException):
            self.set_element(child)

    def test_attr(self):
        self.set_element(self.tag)
        self.assertIsNone(self.get_attribute('src'))
        self.tag.setAttribute('src', 'a')
        self.assertEqual(self.get_attribute('src'), 'a')
        self.tag.removeAttribute('src')
        self.assertIsNone(self.get_attribute('src'))

    def test_addremove_child(self):
        child = WebElement('a')
        self.tag.appendChild(child)
        self.assertIsTrue(self.set_element(child))
        self.assertEqual(self.get_text(), '')
        child.textContent = 'Child'
        self.assertEqual(self.get_text(), 'Child')

        self.set_element(self.tag)
        self.assertEqual(self.get_text(), 'Child')

        self.tag.removeChild(child)
        with self.assertRaises(NoSuchElementException):
            self.set_element(child)

        self.set_element(self.tag)
        self.assertEqual(self.get_text(), '')

    def test_insert_child(self):
        self.set_element(self.tag)
        child1 = WebElement('a', parent=self.tag)
        child1.textContent = 'child1'
        child2 = WebElement('b')
        child2.textContent = 'child2'

        self.assertIsTrue(self.set_element(child1))
        with self.assertRaises(NoSuchElementException):
            self.set_element(child2)

        self.set_element(self.tag)
        self.assertEqual(self.get_text(), 'child1')

        self.tag.insertBefore(child2, child1)
        self.assertIsTrue(self.set_element(child2))

        self.set_element(self.tag)
        self.assertEqual(self.get_text(), 'child2child1')

        self.tag.empty()
        self.assertEqual(self.get_text(), '')
        with self.assertRaises(NoSuchElementException):
            self.set_element(child1)
        with self.assertRaises(NoSuchElementException):
            self.set_element(child2)

    def test_replace_child(self):
        self.set_element(self.tag)
        child1 = WebElement('a')
        child1.textContent = 'child1'
        child2 = WebElement('b')
        child2.textContent = 'child2'
        self.tag.appendChild(child1)
        with self.assertRaises(NoSuchElementException):
            self.set_element(child2)
        self.assertIsTrue(self.set_element(child1))
        self.assertEqual(self.get_text(), 'child1')

        self.tag.replaceChild(child2, child1)
        with self.assertRaises(NoSuchElementException):
            self.set_element(child1)
        self.assertIsTrue(self.set_element(child2))
        self.assertEqual(self.get_text(), 'child2')
        self.set_element(self.tag)
        self.assertEqual(self.get_text(), 'child2')

    def test_shortcut_attr(self):
        self.tag.textContent = 'TAG'
        self.set_element(self.tag)
        self.assertIsTrue(self.is_displayed())
        self.tag.hidden = True
        self.assertIsFalse(self.is_displayed())
        self.tag.hidden = False
        self.assertIsTrue(self.is_displayed())

    def test_get_rect(self):
        rect = WebElement('div', style='width:200px;height:100px;')
        self.tag.appendChild(rect)

        fut = asyncio.ensure_future(rect.getBoundingClientRect())
        asyncio.get_event_loop().run_until_complete(fut)
        data = fut.result()
        self.assertEqual(data['width'], 200)
        self.assertEqual(data['height'], 100)

    def test_scroll(self):
        rect = WebElement('div',
                          style='width:3000px;height:3000px;background:#eee;')
        self.tag.appendChild(rect)
        futX = asyncio.ensure_future(rect.scrollX())
        futY = asyncio.ensure_future(rect.scrollY())
        asyncio.get_event_loop().run_until_complete(futX)
        asyncio.get_event_loop().run_until_complete(futY)
        self.assertEqual(futX.result()['x'], 0)
        self.assertEqual(futY.result()['y'], 0)

        rect.scrollTo(200, 200)
        futX = asyncio.ensure_future(rect.scrollX())
        futY = asyncio.ensure_future(rect.scrollY())
        asyncio.get_event_loop().run_until_complete(futX)
        asyncio.get_event_loop().run_until_complete(futY)
        self.assertEqual(futX.result()['x'], 200)
        self.assertEqual(futY.result()['y'], 200)


class TestEvent(ElementTestCase):
    def get_elements(self):
        self.root = WebElement('div')
        self.tag = WebElement('span', parent=self.root)

        self.click_event_mock = MagicMock()
        self.click_event_mock._is_coroutine = False

        btn = WebElement('button')
        btn.textContent = 'click'
        btn.addEventListener('click', self.click_event_mock)
        self.btn_mock = MagicMock(btn)
        self.btn_mock.configure_mock(id=btn.id, html=btn.html, parentNode=None,
                                     nodeType=btn.nodeType)

        self.input_event_mock = MagicMock()
        self.input_event_mock._is_coroutine = False

        input = WebElement('input', type='text')
        input.addEventListener('input', self.input_event_mock)
        self.input_mock = MagicMock(input)
        self.input_mock.configure_mock(
            id=input.id,
            html=input.html,
            parentNode=input.html,
            nodeType=input.nodeType,
        )

        self.root.appendChild(self.btn_mock)
        self.root.appendChild(self.input_mock)
        return self.root

    def test_click(self):
        self.set_element(self.btn_mock)
        self.click()
        self.wait(0.1)
        self.assertEqual(self.click_event_mock.call_count, 1)
        self.btn_mock.remove.assert_not_called()
        self.btn_mock.setAttribute.assert_not_called()
        self.btn_mock.removeAttribute.assert_not_called()
        self.btn_mock.appendChild.assert_not_called()
        self.btn_mock.insertBefore.assert_not_called()
        self.btn_mock.removeChild.assert_not_called()
        self.btn_mock.replaceChild.assert_not_called()

    def test_input(self):
        self.set_element(self.input_mock)
        self.send_keys('abc')
        self.wait(0.1)
        self.assertEqual(self.input_event_mock.call_count, 3)
        self.btn_mock.remove.assert_not_called()
        self.btn_mock.setAttribute.assert_not_called()
        self.btn_mock.removeAttribute.assert_not_called()
        self.btn_mock.appendChild.assert_not_called()
        self.btn_mock.insertBefore.assert_not_called()
        self.btn_mock.removeChild.assert_not_called()
        self.btn_mock.replaceChild.assert_not_called()
