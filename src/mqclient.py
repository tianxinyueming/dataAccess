#!/usr/bin/python
# -*- coding:utf-8 -*-
import pika
import time
import json
import logging
from uuid import uuid4
import threading
# import queue
from src.dataAccessProtocol import DataAccessProtocol
from src.tools import *
from src.jsonMessageHandle import on_message

__author__ = 'shangxc'


# BINDIND_KEY = (# 'Register',
#                'RegisterResponse',
#                # 'UnRegister',
#                'UnRegisterResponse',
#                # 'Authenticate',
#                'AuthenticateResponse',
#                'OnOffline',
#                'AlarmInfo',
#                'ManualConfirmAlert',
#                'BusinessAlert',
#                'DeviceAlert',
#                # 'RoundRegion',
#                # 'DelRoundRegion',
#                # 'SquareRegion',
#                # 'DelSquareRegion',
#                'PolygonsRegion',
#                'DelPolygonsRegion',
#                'RouteInfo',
#                'DelRouteRegion',
#                # 'GenenalResponse',
#                'QueryAllParam',
#                'QueryPartParam',
#                'SetTermParam',
#                # 'QueryParaResponse',
#                'Test808')

class MqClient(object):
    BINDIND_KEY = (# 'Register',
                   'RegisterResponse',
                   # 'UnRegister',
                   'UnRegisterResponse',
                   # 'Authenticate',
                   'AuthenticateResponse',
                   # 'OnOffline',
                   # 'AlarmInfo',
                   'ManualConfirmAlert',
                   # 'BusinessAlert',
                   # 'DeviceAlert',
                   # 'RoundRegion',
                   # 'DelRoundRegion',
                   # 'SquareRegion',
                   # 'DelSquareRegion',
                   'PolygonsRegion',
                   'DelPolygonsRegion',
                   'RouteInfo',
                   'DelRouteRegion',
                   # 'GenenalResponse',
                   'QueryAllParam',
                   'QueryPartParam',
                   'SetTermParam',
                   # 'QueryParaResponse',
                   'Test808')

    # waiting_send = queue.Queue()

    def __init__(self, ip='127.0.0.1', port=5672, username='guest', password='guest'):
        self.credential = pika.PlainCredentials(username, password)
        self.param = pika.ConnectionParameters(host=ip, port=port, credentials=self.credential)

    def send_message(self, routing_key, uid, message, exchange='MDVR_EXCHANGE'):
        self._sender_channel.basic_publish(exchange, 'MDVR.%s.%s' % (routing_key, uid), message)

    # def send_message(self, routing_key, uid, message, exchange='MDVR_EXCHANGE'):
    #     self.waiting_send.put((routing_key, uid, message, exchange))

    def start(self):
        self.th = threading.Thread(target=self._start_rec)
        self.th.setDaemon(True)
        self.th.start()
        # self.th1 = threading.Thread(target=self._start_sending)
        # self.th1.setDaemon(True)
        # self.th1.start()

    def _start_rec(self):
        while True:
            try:
                self.connection = pika.BlockingConnection(parameters=self.param)
                # self._sender_connection = pika.BlockingConnection(parameters=self.param)
                self._sender_channel = self.connection.channel()
                self.channel = self.connection.channel()
                self.channel.exchange_declare('MDVR_EXCHANGE', 'topic', durable=True)
                self.channel.exchange_declare('GPS_EXCHANGE', 'topic', durable=True)
                self.queue_name = 'PTMS.dataAccess.' + str(uuid4())
                self.queue = self.channel.queue_declare(queue=self.queue_name, auto_delete=True)
                for key in self.BINDIND_KEY:
                    self.channel.queue_bind(queue=self.queue_name, exchange='MDVR_EXCHANGE', routing_key='MDVR.%s.*' % key)
                self.channel.basic_consume(on_message, self.queue_name, True)
                try:
                    self.channel.start_consuming()
                except KeyboardInterrupt:
                    self.channel.stop_consuming()
                    break
            except Exception as e:
                try:
                    self.close()
                except Exception:
                    pass
                logging.warning('an error about rabbitmq occured, reconnect to rabbitmq')
                logging.error(repr(e))

    # def _start_sending(self):
    #     while True:
    #         routing_key, uid, message, exchange = self.waiting_send.get()
    #         self._sender_channel.basic_publish(exchange, 'MDVR.%s.%s' % (routing_key, uid), message)


    def close(self):
        self.channel.queue_delete(self.queue_name)
        self.channel.close()
        self._sender_channel.close()
        self.connection.close()
        # self._sender_connection.close()


if __name__ == '__main__':
    a = MqClient('127.0.0.1')
    for i in BINDIND_KEY:
        a.send_message(i, 'dsljf', i)

