# -*- coding:utf-8 -*-
import binascii
import datetime

import functools
import logging
import operator
import os

import time
from stat import ST_MTIME

__author__ = 'shangxc'

TIME_FOMMAT_MDVR = '%y%m%d%H%M%S'
TIME_FOMMAT_JSON = '%Y-%m-%d %H:%M:%S'


def printfuled(message):
    return str(binascii.b2a_hex(message))[2: -1]


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


def word_to_int(value):
    assert isinstance(value, bytes)
    assert len(value) == 2
    return (value[0] << 8) | value[1]


def byte_to_str(value):
    assert isinstance(value, bytes)
    return value.decode()


def string_to_str(value):
    assert isinstance(value, bytes)
    return value.decode('gbk')


def int_to_word(value):
    if isinstance(value, int) and value <= 65535:
        return bytes((value >> 8,)) + bytes((value & 255,))


def int_to_byte(value):
    if isinstance(value, int) and value <= 255:
        return bytes((value,))


def str_to_string(value):
    if isinstance(value, str):
        return value.encode('GBK')


def int_to_bcd(value, n):
    if isinstance(value, int):
        return binascii.a2b_hex(('%0' + str(2 * n) + 'd') % value)


def dword_to_bitlist(value):
    assert isinstance(value, bytes)
    assert len(value) == 4
    return int_to_bitlist(dword_to_int(value), 32)


def dword_to_int(value):
    assert isinstance(value, bytes)
    assert len(value) == 4
    return (value[0] << 24) | (value[1] << 16) | (value[2] << 8) | value[3]


def int_to_bitlist(value, n, is_low_to_up=True):
    alist = []
    for i in range(n):
        alist.append(1 if value & (1 << i) else 0)
    if not is_low_to_up:
        alist.reverse()
    return alist


def int_to_dword(value):
    if isinstance(value, int) and value <= 4294967295:
        return int_to_word(value >> 16) + int_to_word(value & 65535)


def bitlist_to_int(alist, is_low_to_up=True):
    if is_low_to_up:
        alist = alist.reverse()
    return functools.reduce(lambda a, b: (a << 1) | b, alist)


def bcd_to_time(value):
    assert isinstance(value, bytes)
    assert len(value) == 6
    time_without_line = printfuled(value)
    return datetime.datetime.strptime(time_without_line, TIME_FOMMAT_MDVR)


def bcd_to_time_for_mq(value):
    assert isinstance(value, bytes)
    assert len(value) == 6
    time_list = tuple(i for i in value)
    # for i in value:
    #     time_list.append('%02x' % i)
    return '20%02x-%02x-%02x %02x:%02x:%02x' % time_list
    # + '-'.join(time_list[: 3]) + ' ' + ':'.join(time_list[3:])


def time_to_time_str(value):
    assert isinstance(value, datetime.datetime)
    return value.strftime(TIME_FOMMAT_JSON)


def time_str_to_time(value):
    assert isinstance(value, str)
    return datetime.datetime.strptime(value, TIME_FOMMAT_JSON)


def time_to_bcd(value):
    assert isinstance(value, datetime.datetime)
    return binascii.a2b_hex(value.strftime(TIME_FOMMAT_MDVR))


class TwoWayDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        super().__init__({self[i]: i for i in self})

    def __setitem__(self, *args, **kwargs):
        if args[1] in self:
            self.pop(args[1], None)
        super().__setitem__(*args, **kwargs)
        super().__setitem__(*reversed(args))

    def pop(self, k, d=None):
        super().pop(self[k], d)
        return super().pop(k, d)


class MyLogHandler(logging.FileHandler):
    def __init__(self, max_bytes, when):
        self.suffix = '.%Y-%m-%d_%H-%M-%S.log'
        self.file_name = os.path.abspath('log/dataAccess')
        filename = self.file_name + time.strftime(self.suffix)
        if not os.path.isdir('log'):
            os.mkdir('log')
        super().__init__(filename=filename, mode='a', encoding='utf8', delay=False)
        self.maxBytes = max_bytes
        self.atTime = datetime.time(hour=when)
        self.interval = 60 * 60 * 24
        if os.path.exists(filename):
            t = os.stat(filename)[ST_MTIME]
        else:
            t = int(time.time())
        self.rolloverAt = self.computeRollover(t)

    def emit(self, record):
        """
        Emit a record.

        Output the record to the file, catering for rollover as described
        in doRollover().
        """
        try:
            if self.shouldRollover(record):
                self.doRollover()
            logging.FileHandler.emit(self, record)
        except Exception:
            self.handleError(record)

    def computeRollover(self, currentTime):
        """
        Work out the rollover time based on the specified time.
        """
        result = currentTime + self.interval
        # If we are rolling over at midnight or weekly, then the interval is already known.
        # What we need to figure out is WHEN the next interval is.  In other words,
        # if you are rolling over at midnight, then your base interval is 1 day,
        # but you want to start that one day clock at midnight, not now.  So, we
        # have to fudge the rolloverAt value in order to trigger the first rollover
        # at the right time.  After that, the regular interval will take care of
        # the rest.  Note that this code doesn't care about leap seconds. :)
        # This could be done with less code, but I wanted it to be clear
        t = time.localtime(currentTime)
        currentHour = t[3]
        currentMinute = t[4]
        currentSecond = t[5]
        currentDay = t[6]
        # r is the number of seconds left between now and the next rotation
        rotate_ts = ((self.atTime.hour * 60 + self.atTime.minute)*60 +
            self.atTime.second)

        r = rotate_ts - ((currentHour * 60 + currentMinute) * 60 +
            currentSecond)
        if r < 0:
            # Rotate time is before the current time (for example when
            # self.rotateAt is 13:45 and it now 14:15), rotation is
            # tomorrow.
            r += 60 * 60 * 24
        result = currentTime + r
        return result

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        record is not used, as we are just comparing times, but it is needed so
        the method signatures are the same
        """
        t = time.time()
        if t >= self.rolloverAt:
            return 1
        # if self.stream is None:                 # delay was set...
        #     self.stream = self._open()
        if self.maxBytes > 0:                   # are we rolling over?
            # msg = "%s\n" % self.format(record)
            # self.stream.seek(0, 2)  #due to non-posix-compliant Windows feature
            # if self.stream.tell() + len(msg) >= self.maxBytes:
            #     return 1
            if self.stream.tell() >= self.maxBytes:
                return 1
        return 0

    def doRollover(self):
        """
        do a rollover; in this case, a date/time stamp is appended to the filename
        when the rollover happens.  However, you want the file to be named for the
        start of the interval, not the current time.  If there is a backup count,
        then we have to get a list of matching filenames, sort them and remove
        the one with the oldest suffix.
        """
        if self.stream:
            self.stream.close()
            self.stream = None
        # get the time that this sequence started at and make it a TimeTuple
        currentTime = int(time.time())
        dstNow = time.localtime(currentTime)[-1]
        dfn = self.file_name + time.strftime(self.suffix)
        self.baseFilename = dfn
        i = 1
        while os.path.exists(self.baseFilename):
            self.baseFilename = '%s.%d' % (dfn, i)
            i += 1
        if not self.delay:
            self.stream = self._open()
        newRolloverAt = self.computeRollover(currentTime)
        while newRolloverAt <= currentTime:
            newRolloverAt = newRolloverAt + self.interval
        #If DST changes and midnight or weekly rollover, adjust for this.
        dstAtRollover = time.localtime(newRolloverAt)[-1]
        if dstNow != dstAtRollover:
            if not dstNow:  # DST kicks in before next rollover, so we need to deduct an hour
                addend = -3600
            else:           # DST bows out before next rollover, so we need to add an hour
                addend = 3600
            newRolloverAt += addend
        self.rolloverAt = newRolloverAt


class Message(object):
    ID_TERMINAL_COMMON_REPLY = b'\x00\x01'
    ID_PLATFORM_COMMON_REPLY = b'\x80\x01'
    ID_HEART_BEAT = b'\x00\x02'
    ID_REQUEST_MESSAGE_AFRESH = b'\x80\x03'
    ID_TERMINAL_REGISTER = b'\x01\x00'
    ID_TERMINAL_REGISTER_REPLY = b'\x81\x00'
    ID_TERMINAL_LOGOUT = b'\x00\x03'
    ID_TERMINAL_AUTHENTICATION = b'\x01\x02'
    ID_LOCATION_INFORMATION = b'\x02\x00'
    ID_SET_POLYGONS_REGION = b'\x86\x04'
    ID_DEL_POLYGONS_REGION = b'\x86\x05'
    ID_SET_ROUTE = b'\x86\x06'
    ID_DEL_ROUTE = b'\x86\x07'
    ID_QUERY_ALL_PARAM = b'\x81\x04'
    ID_QUERY_PART_PARAM = b'\x81\x06'
    ID_SET_PARAM = b'\x81\x03'
    ID_QUERY_PARAM_REPLY = b'\x01\x04'
    MESSAGE_START = b'\x7e'
    MESSAGE_END = b'\x7e'

    def __init__(self, message_id, phone_num, message_body, message_num, is_separate=False, is_rsa=False):
        self.message_id = message_id
        self.phone_num = int(phone_num)
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

if __name__ == '__main__':
    import timeit
    print(timeit.timeit(lambda : bcd_to_time_for_mq(b'\x11\x11\x11\x11\x11\x11')))
