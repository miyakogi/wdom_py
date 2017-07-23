#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import asyncio
from typing import Optional

from tornado import autoreload

from wdom.misc import static_dir, install_asyncio
from wdom.options import config
from wdom.server.base import exclude_patterns, open_browser, watch_dir
from wdom.server import _tornado as module

__all__ = ('get_app', 'start_server', 'stop_server', 'exclude_patterns')
logger = logging.getLogger(__name__)
_server = None
server_config = module.server_config
_msg_queue = []


def is_connected() -> bool:
    """Check if the current server has a client connection."""
    return module.is_connected()


def push_message(msg: dict) -> None:
    """Push message on the message queue."""
    _msg_queue.append(msg)


def send_message() -> None:
    """Send message to all client connections."""
    if not _msg_queue:
        return
    msg = json.dumps(_msg_queue)
    _msg_queue.clear()
    for conn in module.connections:
        conn.write_message(msg)


def add_static_path(prefix, path, no_watch: bool = False) -> None:
    """Add directory to serve static files.

    First argument ``prefix`` is a URL prefix for the ``path``. ``path`` must
    be a directory. If ``no_watch`` is True, any change of the files in the
    path do not trigger restart if ``--autoreload`` is enabled.
    """
    app = get_app()
    app.add_static_path(prefix, path)
    if not no_watch:
        watch_dir(path)


def get_app(*args, **kwargs) -> 'Application':
    """Get root Application object."""
    return module.get_app()


@asyncio.coroutine
def _message_loop():
    while True:
        send_message()
        yield from asyncio.sleep(config.message_wait)


def start_server(browser: Optional[str] = None, address: Optional[str] = None,
                 check_time: Optional[int] = 500, **kwargs):
    """Start web server."""
    # Add application's static files directory
    from wdom.document import get_document
    add_static_path('_static', static_dir)
    doc = get_document()
    if os.path.exists(doc.tempdir):
        add_static_path('tmp', doc.tempdir, no_watch=True)
    if doc._autoreload or config.autoreload or config.debug:
        install_asyncio()
        autoreload.start(check_time=check_time)
    global _server
    _server = module.start_server(**kwargs)
    logger.info('Start server on {0}:{1:d}'.format(
        server_config['address'], server_config['port']))

    # start messaging loop
    asyncio.ensure_future(_message_loop())

    if config.open_browser:
        open_browser('http://{}:{}/'.format(server_config['address'],
                                            server_config['port']),
                     browser or config.browser)
    return _server


def stop_server(server=None):
    """Terminate web server."""
    module.stop_server(server or _server)


def start(**kwargs):
    """Start web server.
    Run until ``Ctrl-c`` pressed, or if auto-shutdown is enabled, until when
    window is closed.
    """
    start_server(**kwargs)
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        stop_server()
