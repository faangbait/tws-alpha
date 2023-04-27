#!/usr/bin/env python

import argparse
import datetime
from pprint import pp
import logging
from api.conf import set_logger
from api.conf import Config
from api.db import twsDatabase
from api.strategy import twsStrategy


def main():
    logger = set_logger(file_level=logging.DEBUG, console_level=logging.INFO)
    logger.debug("now is %s", datetime.datetime.now())

    cmd = argparse.ArgumentParser("tws-alpha api automation")
    cmd.add_argument("-p", "--port", action="store", type=int, dest="port", default=7490, help="Client TCP Port")
    cmd.add_argument("-H", "--host", action="store", type=str, dest="host", default="localhost", help="Client host")
    cmd.add_argument("-C", "--global-cancel", action="store_true", dest="global_cancel", default=False, help="cancel all")
    cmd.add_argument("--wipe", action="store_true", dest="wipe_database", default=False, help="wipe the database on load")

    args = cmd.parse_args()
    logger.debug(f"Using args: {args}")

    if args.wipe_database:
        logger.warn("Wiping database...")
        twsDatabase(fresh=True)
    app = twsStrategy()

    if args.global_cancel:
        app.global_cancel = True

    try:
        app.connect(args.host, args.port, clientId=0)
        logger.debug(f"server version: {app.serverVersion()}, connection time: {app.twsConnectionTime()}")
        app.run()
    except:
        raise Exception(f"Could not connect to {args.host}:{args.port} as client 0")

if __name__ == "__main__":
    pp(f"Ally Alpha Seeker v{Config.VERSION} Started")
    main()
