#!/usr/bin/env python3
# -*- coding:utf-8 -*-
__author__ = 'shangxc'
from twisted.internet.protocol import Protocol, connectionDone, ServerFactory, Factory
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from src.dataAccessFactory import DataAccessFactory
from conf.config import *
import logging
from src.tools import MyLogHandler
from src.mqclient import MqClient


def main():
    formater = '%(asctime)s %(levelname)s: %(message)s' + ' '*11 + ' %(pathname)s: %(lineno)s'
    loghandler = MyLogHandler(max_bytes=LOG_MAX_BYTES,
                              when=LOG_NEW_AT_CLOCK)
    logging.basicConfig(level=logging.INFO,
                        format=formater,
                        # handlers=(loghandler,)
                        )
    endpoint = TCP4ServerEndpoint(reactor=reactor,
                                  port=DATAACCESS_PORT)
    endpoint.listen(DataAccessFactory(mq_ip=RABBIT_MQ_IP,
                                      mq_port=RABBIT_MQ_PORT,
                                      mq_user_name=RABBIT_MQ_USER,
                                      mq_password=RABBIT_MQ_PASSWORD,
                                      timeout=TIMEOUT))
    reactor.run()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logging.error(repr(e))

