# -*- coding:utf-8 -*-
import logging

import binascii

__author__ = 'shangxc'

from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory, ReconnectingClientFactory
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from test import mdvr

class Greeter(Protocol, mdvr.MDVR):
    def send(self, message, log_tips='bytes', add_to_waiting_response=True):
        bytes_message = bytes(message)
        self.transport.write(bytes_message)
        logging.info('%012d send %-20s : %s' % (self.phoneNum, log_tips, str(binascii.b2a_hex(bytes_message))))
        if isinstance(message, mdvr.Message) and add_to_waiting_response:
            self.waiting_response[message.message_num] = message

    def connectionMade(self):
        self.send_terminal_authentication()
        reactor.callLater(2, self.send_location_information)

    # def dataReceived(self, data):
        # reactor.callLater(2, self.send_location_information)
        # self.send_location_information()

    def send_location_information(self):
        super().send_location_information()
        reactor.callLater(2, self.send_location_information)


def gotProtocol(p):
    p.sendMessage("Hello")
    reactor.callLater(1, p.sendMessage, "This is sent in a second")
    reactor.callLater(2, p.transport.loseConnection)


class EchoClientFactory1(ReconnectingClientFactory):
    def __init__(self, phone_num, authentication_code=''):
        self.phone_num = phone_num
        self.authentication_code = authentication_code

    def startedConnecting(self, connector):
        print('Started to connect.')

    def buildProtocol(self, addr):
        print('Connected.')
        print('Resetting reconnection delay')
        self.resetDelay()
        return Greeter(phone_num=self.phone_num, authentication_code=self.authentication_code)

    def clientConnectionLost(self, connector, reason):
        print('Lost connection.  Reason:', reason)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed. Reason:', reason)
        ReconnectingClientFactory.clientConnectionFailed(self, connector,
                                                         reason)

if __name__ == '__main__':
    import time
    # point = TCP4ClientEndpoint(reactor, "localhost", 9876)
    # for i in range(5):
    #     d = connectProtocol(point, Greeter(12345678901))
    #     d.addCallback(gotProtocol)
    #     time.sleep(1)
    #     print(i)
    # reactor.run()
    reactor.connectTCP('localhost', 9876, EchoClientFactory1(123, '111222333442'))
    reactor.connectTCP('localhost', 9876, EchoClientFactory1(124, '111222333443'))
    reactor.run()
