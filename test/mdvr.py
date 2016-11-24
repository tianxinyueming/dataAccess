#!/usr/bin/python
# -*- coding:utf-8 -*-
__author__ = 'shangxc'
from socket import socket, AF_INET, SOCK_STREAM, error, SHUT_RDWR, timeout as timeoutError
from threading import Thread, Lock
from time import ctime, strftime, sleep, time
import re
from uuid import uuid1
import traceback
from os import mkdir, path
from datetime import datetime
import logging
import binascii
import functools
import operator
import multiprocessing
import decimal
import operator

MESSAGE_START = b'\x7e'
MESSAGE_END = b'\x7e'
MESSAGE_ID = {'terminal common reply': b'\x00\x01',
              'platform common reply': b'\x80\x01',
              'heart beat': b'\x00\x02',
              'request message afresh': b'\x80\x03',
              'terminal register': b'\x01\x00',
              'terminal register reply': b'\x81\x00',
              'terminal logout': b'\x00\x03',
              'terminal authentication': b'\x01\x02',
              'location information': b'\x02\x00',
              }

MESSAGE_FORMAT = {'terminal common reply': b'\x00\x01',
                  'platform common reply': b'\x80\x01',
                  'heart beat': b'\x00\x02',
                  'request message afresh': b'\x80\x03',
                  'terminal register': {'id': b'\x01\x00', 'message body': b'%s' * 7},
                  'terminal register reply': b'\x81\x00',
                  'terminal logout': b'\x00\x03',
                  'terminal authentication': b'\x01\x02',
                  }

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s ' + ' ' * 10 + ' %(pathname)s: %(lineno)s')
mdvr_list = {}
error_count = 0

def int_to_word(value):
    if isinstance(value, int) and value <= 65535:
        return bytes((value >> 8,)) + bytes((value & 255,))


def int_to_byte(value):
    if isinstance(value, int) and value <= 255:
        return bytes((value,))


def str_to_byte(value):
    if isinstance(value, str):
        return value.encode('ascii')


def str_to_string(value):
    if isinstance(value, str):
        return value.encode('GBK')


def string_to_str(value):
    if isinstance(value, bytes):
        return value.decode('GBK')


def printfuled(message):
    return str(binascii.b2a_hex(message))[2: -1]


def bitlist_to_int(alist, is_low_to_up=True):
    if is_low_to_up:
        alist = reversed(alist)
    return functools.reduce(lambda a, b: (a << 1) | b, alist)

def __bitlist_to_int(a, b):
    return (a << 1) | b


def int_to_dword(value):
    if isinstance(value, int) and value <= 4294967295:
        return int_to_word(value >> 16) + int_to_word(value & 65535)


def int_to_bcd(value, n):
    if isinstance(value, int):
        return binascii.a2b_hex(('%0' + str(2 * n) + 'd') % value)


class GPS(object):
    def __init__(self, longitude=0.0, latitude=0.0, height=0, speed=0, direction=0):
        # self.longitude = float(longitude)
        # self.latitude = float(latitude)
        # self.height = int(height)
        # self.speed = int(speed)
        # self.direction = int(direction)
        self.longitude = decimal.Decimal(str(longitude))
        self.latitude = decimal.Decimal(str(latitude))
        self.height = int(height)
        self.speed = int(speed)
        self.direction = int(direction)

    def get(self):
        return {'longitude': self.longitude,
                'latitude': self.latitude,
                'height': self.height,
                'speed': self.speed,
                'direction': self.direction}


class MDVR(object):
    def __init__(self, phone_num, province_id=0, city_id=0, manufacturer_id='12345', terminal_type='ATM0101',
                 terminal_id='9876', plate_color=0, plate='京A0001', authentication_code='', gps=GPS(),
                 mileage=0, oil=0, ip='127.0.0.1', port=9876):
        super(MDVR, self).__init__()
        self.phoneNum = int(phone_num)
        self.province_id = int(province_id)
        self.city_id = int(city_id)
        self.manufacturer_id = str(manufacturer_id.rjust(5))
        self.terminal_type = str(terminal_type)
        self.terminal_id = str(terminal_id)
        self.plate_color = int(plate_color)
        self.plate = str(plate)
        self.ip = str(ip)
        self.port = int(port)
        self.connected = False
        self.last_receive = ''
        self.next_message_num = 0
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.waiting_response = {}
        self.authentication_code = str(authentication_code)
        self.alarm_flag = [0 for i in range(32)]
        self.status = [0 for i in range(32)]
        self.gps = gps
        self.set_gps(gps)
        self.mileage = int(mileage)
        self.oil = int(oil)

    def set_gps(self, gps=GPS()):
        self.gps = gps
        if self.gps.longitude >= 0:
            self.status[3] = 0
        else:
            self.status[3] = 1
        if self.gps.latitude >= 0:
            self.status[2] = 0
        else:
            self.status[2] = 1
        if gps.direction or gps.height or gps.latitude or gps.longitude or gps.speed:
            self.status[1] = 1
        else:
            self.status[1] = 0

    def connect(self):
        try:
            self.sock = socket(AF_INET, SOCK_STREAM)
            self.sock.connect((self.ip, self.port))
            self.connected = True
            logging.info('%012d start connect', self.phoneNum)
        except error:
            logging.error('Connect fail!!!')
            return -1

    def close(self):
        self.connected = False
        self.sock.shutdown(SHUT_RDWR)
        self.sock.close()
        logging.info('%012d close connect' % self.phoneNum)

    def send_heart_beat(self):
        message_body = b''
        self.send_message(MESSAGE_ID['heart beat'], message_body, 'heart beat')

    def send_register(self):
        message_body = b'%s' * 7 % (int_to_word(self.province_id),
                                    int_to_word(self.city_id),
                                    str_to_byte(self.manufacturer_id),
                                    str_to_byte(self.terminal_type).ljust(20, b'\x00'),
                                    str_to_byte(self.terminal_id).ljust(7, b'\x00'),
                                    int_to_byte(self.plate_color),
                                    str_to_string(self.plate))
        self.send_message(MESSAGE_ID['terminal register'], message_body, 'terminal register')

    def send_logout(self):
        message_body = b''
        self.send_message(MESSAGE_ID['terminal logout'], message_body, 'terminal logout')

    def send_terminal_authentication(self):
        assert self.authentication_code != ''
        message_body = str_to_string(self.authentication_code)
        self.send_message(MESSAGE_ID['terminal authentication'], message_body, 'terminal authentication')

    def send_location_information(self):
        alarm_flag = int_to_dword(bitlist_to_int(self.alarm_flag))
        status = int_to_dword(bitlist_to_int(self.status))
        latitude = int_to_dword(abs(int(self.gps.latitude * 1000000)))
        longitude = int_to_dword(abs(int(self.gps.longitude * 1000000)))
        height = int_to_word(self.gps.height)
        speed = int_to_word(self.gps.speed)
        direction = int_to_word(self.gps.direction)
        time = int_to_bcd(int(strftime('%y%m%d%H%M%S')), 6)
        message_body_base = b'%s' * 8 % (alarm_flag,
                                         status,
                                         latitude,
                                         longitude,
                                         height,
                                         speed,
                                         direction,
                                         time,)
        message_body_addition = b'\x01\x04%s\x02\x02%s\x03\x02%s' % (int_to_dword(self.mileage),
                                                                     int_to_word(self.oil),
                                                                     int_to_word(self.gps.speed))#+b'\xe0\x53'+b'0'*83
        message_body = message_body_base + message_body_addition
        self.send_message(MESSAGE_ID['location information'], message_body, 'location information')

    def send_message(self, message_id, message_body, log_tips='bytes', add_to_waiting_response=True):
        # message = self.generate_message(message_id, message_body)
        # self.send(message, log_tips)
        message = Message(message_id, self.phoneNum, message_body, self.next_message_num)
        self.send(message, log_tips, add_to_waiting_response)
        if self.next_message_num < 65535:
            self.next_message_num += 1
        else:
            self.next_message_num = 0

    def send(self, message, log_tips='bytes', add_to_waiting_response=True):
        bytes_message = bytes(message)
        self.sock.send(bytes_message)
        logging.info('%012d send %-20s : %s' % (self.phoneNum, log_tips, str(binascii.b2a_hex(bytes_message))))
        if isinstance(message, Message) and add_to_waiting_response:
            self.waiting_response[message.message_num] = message

    def receive_message(self, timeout=None):
        if timeout is None:
            rec = self.sock.recv(4096)
        else:
            self.sock.settimeout(timeout)
            try:
                rec = self.sock.recv(4096)
            except timeoutError:
                logging.warning('no message to recv')
                return None
            finally:
                self.sock.settimeout(None)
        if rec:
            logging.info('receive : %s' % printfuled(rec))
            return rec
        else:
            logging.info('%12d receive none bytes closing connect' % self.phoneNum)
            self.close()

    def receive(self, timeout=None):
        if timeout is None:
            rec = self.sock.recv(4096)
        else:
            self.sock.settimeout(timeout)
            try:
                rec = self.sock.recv(4096)
            except timeoutError:
                logging.warning('no message to recv')
                return None, None
            finally:
                self.sock.settimeout(None)
        result = None
        message_id = None
        if rec:
            logging.info('receive : %s' % printfuled(rec))
            if message_start_end_right(rec):
                message_head_body_checksum = recover_escape(rec[1:-1])
                if check_checksum(message_head_body_checksum):
                    message_body_property = ((message_head_body_checksum[2] << 8) | message_head_body_checksum[3])
                    is_separate = message_body_property & 0b0010000000000000
                    is_rsa = message_body_property & 0b0000010000000000
                    message_body_len = message_body_property & 0b0000001111111111
                    if (not is_separate) and (not is_rsa):
                        message_head = message_head_body_checksum[:12]
                        message_body = message_head_body_checksum[12: -1]
                        message_id = message_head[: 2]
                        if len(message_body) == message_body_len:
                            if message_id == MESSAGE_ID['terminal register reply']:
                                result = self.receive_terminal_register_reply(message_body)
                            elif message_id == MESSAGE_ID['platform common reply']:
                                result = self.receive_plat_common_reply(message_body)
                            else:
                                logging.warning('reply id %s is not support' % printfuled(message_id))
                        else:
                            logging.warning('message len in message head is not correct')
                    else:
                        logging.warning('separate or rsa is not support')
                else:
                    logging.warning('checksum is not correct: %s' % printfuled(rec))
            else:
                logging.warning('message is not start or end with 0x7e')
        else:
            logging.info('%12d receive none bytes closing connect' % self.phoneNum)
            self.close()
        return result, message_id

    def receive_terminal_register_reply(self, message_body):
        message_reply_num = (message_body[0] << 8) | message_body[1]
        try:
            self.waiting_response.pop(message_reply_num)
        except KeyError as e:
            logging.warning('reply num is not correct: %d' % message_reply_num)
        else:
            result = message_body[2]
            if result == 0:
                self.authentication_code = string_to_str(message_body[3:])
                logging.info('register successful, authentication_code is %s' % repr(self.authentication_code))
            elif result == 1:
                logging.warning('this car is registered')
            elif result == 2:
                logging.warning('this car is not in database')
            elif result == 3:
                logging.warning('this terminal is registered')
            elif result == 4:
                logging.warning('this terminal is not in database')
            else:
                logging.warning('this result num is not support: %d' % result)
        return result

    def receive_plat_common_reply(self, message_body):
        message_reply_num = (message_body[0] << 8) | message_body[1]
        result = None
        try:
            original_message = self.waiting_response.pop(message_reply_num)
        except KeyError as e:
            logging.warning('reply num is not correct: %d' % message_reply_num)
        else:
            if original_message.message_id == message_body[2:4]:
                result = message_body[4]
                logging.info('reply %s : result num is %d' % (original_message, result))
                if original_message.message_id == MESSAGE_ID['location information'] and result == 0:
                    self.alarm_flag[0] = 0
                    self.alarm_flag[3] = 0
                    self.alarm_flag[20] = 0
                    self.alarm_flag[21] = 0
                    self.alarm_flag[22] = 0
                    self.alarm_flag[27] = 0
                    self.alarm_flag[28] = 0
                    self.alarm_flag[31] = 0
            else:
                logging.warning('message id in reply message is not correct')
        return result

    def send_terminal_common_reply(self, reply_num, reply_id, result):
        message_body = b'%s' * 3 % (int_to_word(reply_num),
                                    reply_id,
                                    int_to_byte(result))
        self.send_message(MESSAGE_ID['terminal common reply'], message_body, 'terminal common reply', False)

    def test(self):
        global error_count
        try:
            self.connect()
            self.send_terminal_authentication()
            for i in range(10):
                sleep(10)
                self.send_heart_beat()
            self.close()
        except:
            print(error_count)


def message_start_end_right(message):
    assert isinstance(message, bytes)
    if message.startswith(MESSAGE_END) and message.endswith(MESSAGE_END):
        return True
    else:
        return False


def recover_escape(message):
    result = message
    result = result.replace(b'\x7d\x02', b'\x7e')
    result = result.replace(b'\x7d\x01', b'\x7d')
    return result


def check_checksum(message):
    message_head_body = message[:-1]
    checksum = message[-1]
    if checksum == functools.reduce(operator.xor, message_head_body):
        return True
    else:
        return False


class Message(object):
    ID_TERMINAL_COMMON_REPLY = b'\x00\x01'
    ID_PLATFORM_COMMON_REPLY = b'\x80\x01'
    ID_HEART_BEAT = b'\x00\x02'
    ID_REQUEST_MESSAGE_AFRESH = b'\x80\x03'
    ID_TERMINAL_REGISTER = b'\x01\x00'
    ID_TERMINAL_REGISTER_REPLY = b'\x81\x00'
    ID_TERMINAL_LOGOUT = b'\x00\x03'
    ID_TERMINAL_AUTHENTICATION = b'\x01\x02'
    MESSAGE_START = b'\x7e'
    MESSAGE_END = b'\x7e'

    def __init__(self, message_id, phone_num, message_body, message_num, is_separate=False, is_rsa=False):
        self.message_id = message_id
        self.phone_num = phone_num
        self.message_body = message_body
        self.message_num = message_num
        self.checksum = b''
        self.message_head = b''
        self.message = b''
        self.is_separate = is_separate
        self.is_rsa = is_rsa
        self.generate_message_head()
        self.generate_checksum()
        self.generate_message()

    def generate_message_head(self):
        self.message_head = self.message_id
        message_body_property = len(self.message_body)
        if self.is_separate:
            message_body_property += (1 << 13)
        if self.is_rsa:
            message_body_property += (1 << 10)
        self.message_head += int_to_word(message_body_property)
        self.message_head += int_to_bcd(self.phone_num, 6)
        self.message_head += int_to_word(self.message_num)
        if self.is_separate:
            pass

    def generate_checksum(self):
        self.checksum = bytes((functools.reduce(operator.xor, self.message_head + self.message_body),))

    @staticmethod
    def make_message_escaped(message):
        assert isinstance(message, bytes)
        if b'\x7d' in message:
            message = message.replace(b'\x7d', b'\x7d\x01')
        if b'\x7e' in message:
            message = message.replace(b'\x7e', b'\x7d\x02')
        return message

    def generate_message(self):
        self.message = self.MESSAGE_START + self.make_message_escaped(
            self.message_head + self.message_body + self.checksum) + self.MESSAGE_END

    def __bytes__(self):
        return self.message

    def __str__(self):
        return printfuled(self.message)


class ChecksumError(Exception):
    def __init__(self):
        super(ChecksumError, self).__init__()
        self.message = 'checksum is invalid!!!'

    def __str__(self):
        return self.message


class BYTE(object):
    def __init__(self, value):
        self.value = None
        if value:
            if isinstance(value, int) and value <= 255:
                self.value = bytes((value,))
            elif isinstance(value, str) and len(value) <= 1:
                self.value = bytes(value, 'utf-8')
            elif isinstance(value, bytes) and len(value) <= 1:
                self.value = value
        else:
            self.value = b'\x00'

    def __str__(self):
        return str(self.value)


class WORD(object):
    def __init__(self, value):
        self.value = None
        if isinstance(value, int) and value <= 65535:
            self.value = BYTE(value // 255).value + BYTE(value % 255).value
        elif isinstance(value, str) and len(value) <= 2:
            if len(value) == 1:
                pass


def multiMDVR(total, thread_per_process=100, ip='127.0.0.1'):
    processes = []
    for i in range(0, total, thread_per_process):
        if total - i < thread_per_process:
            processes.append(multiprocessing.Process(target=multi_thread, args=(i, total - i, ip)))
        else:
            processes.append(multiprocessing.Process(target=multi_thread, args=(i, thread_per_process, ip)))
        processes[-1].start()
    return processes


def multi_thread(start_num, total, ip='127.0.0.1'):
    for i in range(total):
        Thread(target=MDVR(phone_num=start_num + i, ip=ip, authentication_code='%012d' % (start_num + i)).test).start()
        sleep(0.01)


if __name__ == '__main__':
    # gps = GPS(136.1234, 66.6543, 321, 123, 300)
    # a = MDVR(13488834791, ip='127.0.0.1', gps=gps)
    # print(BYTE('o').value)
    # print(BYTE(b'0').value)
    # print(BYTE(55).value)
    # a.connect()
    # print('au', a.authentication_code)
    # a.send_register()
    # print('wr', a.waiting_response)
    # # a.receive()
    # print('au', repr(a.authentication_code))
    # sleep(1)
    # a.send_location_information()
    # # a.send_heart_beat()
    # # a.send_logout()
    # a.close()
    # print(a.waiting_response)
    # for i in range(10):
    #     mdvr = []
    #     for i in range(100):
    #         mdvr.append(MDVR(100000+i, ip='127.0.0.1', gps=gps, authentication_code='1000%04d' % i))
    #     thread = []
    #     for i in range(100):
    #         thread.append(multiprocessing.Process(target=mdvr[i].test))
    #     for i in range(100):
    #         thread[i].start()
    #     for i in range(100):
    #         thread[i].join()
    # import time
    # a = time.time()
    # b = multiMDVR(1)
    # for i in b:
    #     i.join()
    # print(time.time()-a)
    gps = GPS(-136.1299, -66.6599, 321, 123, 300)
    a = MDVR(18812345678, authentication_code='123459876543', ip='172.16.50.98', manufacturer_id="12345",
             terminal_id='9876543', plate='BJ0001')
    a.connect()
    a.send_terminal_authentication()
    # a.send_register()
    # a.receive()
    # a.send_register()
    # a.receive()
    #
    # a.send_terminal_authentication()
    # a.receive()
    # sleep(10)
    # for i in range(10000):
    #     t = time()
    #     # a.send_location_information()
    #     a.send_heart_beat()
    #     if not a.receive_message(4):
    #         logging.error(time() - t)
    # a.status = [1 for i in a.status]
    # a.send_location_information()
    # for i in range(1000):
    #     a.alarm_flag = [1 for i in a.alarm_flag]
    #     a.send_location_information()
    #     a.receive()
    #     sleep(1)
    # a.alarm_flag[0] = 1
    # for i in range(10):
    #     sleep(1)
    #     a.send_heart_beat()
    #     sleep(1)
    #     a.send_location_information()
    # sleep(5)
    # a.send_heart_beat()
    # a.receive()
    # a.sock.send(b'7e00020000018812345678000d8e7e')
    # for i in range(100):
    #     a.send_location_information()
    #     a.receive()
    #     sleep(1)
    # sleep(5)
    # a.sock.send(binascii.a2b_hex('7e000200000188123456780001827e7e0200001c0188123456780002000000000000000e0254f9c8082a43d000c8001e012c160629155636f27e7e000200000188123456780003807e7e0200001c0188123456780002000000000000000e0254f9c8082a43d000c8001e012c160629155636f27e'))
    # sleep(5)
    # print(a.status)
    # a.receive()
    # for i in range(10):
    #     a.receive()
    # sleep(10)
    a.close()

