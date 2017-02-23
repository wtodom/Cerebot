#!/usr/bin/env python3

"""cerebot: A Discord chat bot that can relay queries to the IRC
knowledge bots for DCSS.

"""

import argparse

import asyncio
if hasattr(asyncio, "async"):
    ensure_future = asyncio.async
else:
    ensure_future = asyncio.ensure_future

from beem.dcss import DCSSManager
import functools
import logging
import os
import signal
import sys

from .discord import DiscordManager
from .config import CerebotConfig
from .version import version

## Will be configured by Cerebot after the config is loaded.
_log = logging.getLogger()

_DEFAULT_CONFIG_FILE = "cerebot_config.toml"

class Cerebot:
    """Cerebot. Load the configuration and runs the tasks for the DCSS
    and Discord managers.

    """

    def __init__(self, config_file):
        self.dcss_task = None
        self.discord_task = None
        self.loop = asyncio.get_event_loop()
        self.shutdown_error = False

        self.conf = CerebotConfig(config_file)

        try:
            self.conf.load()
        except Exception as e:
            err_reason = type(e).__name__
            if len(e.args):
                err_reason = e.args[0]
            _log.critical(err_reason)
            sys.exit(1)

        self.dcss_manager = DCSSManager(self.conf.dcss)
        self.discord_manager = DiscordManager(self.conf.discord,
                                              self.dcss_manager)

    def start(self):
        """Start the bot, set up the event loop and signal handlers,
        and exit when the manager tasks finish.

        """

        _log.info("Starting Cerebot.")

        def do_exit(signame):
            is_error = True if signame == "SIGTERM" else False
            msg = "Shutting down server due to signal: {}".format(signame)
            if is_error:
                _log.error(msg)
            else:
                _log.info(msg)
            self.stop(is_error)

        for signame in ("SIGINT", "SIGTERM"):
            self.loop.add_signal_handler(getattr(signal, signame),
                                           functools.partial(do_exit, signame))

        print("Event loop running forever, press Ctrl+C to interrupt.")
        print("pid %s: send SIGINT or SIGTERM to exit." % os.getpid())

        try:
            self.loop.run_until_complete(self.process())
        except asyncio.CancelledError:
            pass

        self.loop.close()
        sys.exit(self.shutdown_error)

    def stop(self, is_error=False):
        """Stop the app by canceling any ongoing manager tasks, which
        will cause this app process to exit.

        """

        _log.info("Stopping Cerebot.")
        self.shutdown_error = is_error

        if self.dcss_task and not self.dcss_task.done():
            self.dcss_task.cancel()

        if self.discord_task and not self.discord_task.done():
            ensure_future(self.discord_manager.disconnect())

    @asyncio.coroutine
    def process(self):
        tasks = []

        self.discord_task = ensure_future(self.discord_manager.start())
        tasks.append(self.discord_task)

        self.dcss_task = ensure_future(self.dcss_manager.start())
        tasks.append(self.dcss_task)

        yield from asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

        self.dcss_manager.disconnect()
        yield from self.discord_manager.disconnect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("-c", dest="config_file", metavar="<toml-file>",
                        default=_DEFAULT_CONFIG_FILE,
                        help="The Cerebot config file.")
    parser.add_argument("--version", action="version", version=version)
    args = parser.parse_args()

    bot = Cerebot(args.config_file)
    bot.start()
