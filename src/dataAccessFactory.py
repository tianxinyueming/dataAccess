# -*- coding:utf-8 -*-
from twisted.internet.protocol import ServerFactory
import logging

from src.dataAccessProtocol import DataAccessProtocol
from src.mqclient import MqClient
# from src.asynch import ExampleConsumer as MqClient
from twisted.internet import task

__author__ = 'shangxc'


class DataAccessFactory(ServerFactory):
    protocol = DataAccessProtocol

    def __init__(self, mq_ip='127.0.0.1', mq_port=5672, mq_user_name='guest', mq_password='guest', timeout=120):
        # self.mq_ip = mq_ip
        # self.mq_port = mq_port
        # self.mq_user_name = mq_user_name
        # self.mq_password = mq_password
        self.mq = MqClient(mq_ip, mq_port, mq_user_name, mq_password)
        self.timeout = timeout

    def buildProtocol(self, addr):
        p = self.protocol()
        p.timeOut = self.timeout
        p.factory = self
        return p

    def startFactory(self):
        # self.mq = MqClient(self.mq_ip, self.mq_port, self.mq_user_name, self.mq_password)
        self.mq.start()
        logging.info('Factory start')

    def stopFactory(self):
        self.mq.close()
        logging.info('Factory stop')


if __name__ == '__main__':
    pass
