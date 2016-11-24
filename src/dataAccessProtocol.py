# -*- coding:utf-8 -*-
import json
# from decimal import Decimal

from twisted.internet.protocol import Protocol, connectionDone
import binascii
from twisted.protocols.policies import TimeoutMixin
import logging
from src.tools import *

__author__ = 'shangxc'

MDVR_EXCHANGE = 'MDVR_EXCHANGE'
GPS_EXCHANGE = 'GPS_EXCHANGE'
PARAM_MAP = {1: int_to_byte,
             2: int_to_word,
             3: str_to_string,
             4: int_to_dword}
PARAM_REPLY_MAP = {1: lambda value: value[0],
                   2: word_to_int,
                   3: string_to_str,
                   4: dword_to_int}

message_handle = {}


def reg_handle(message_id):
    def f(func):
        message_handle[message_id] = func
        return func

    return f


class ProtocolNotFoundError(Exception):
    pass


class DataAccessProtocol(Protocol, TimeoutMixin):
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
    # BUSINESS_ALERT_RECEIVE_RESET_0 = {
    #     1: 20,  # 进出区域
    #     2: 21,  # 进出路线
    #     5: 3,  # 危险预警
    #     8: 22,  # 路段行驶时间不足或过长
    #     10: 27,  # 车辆非法点火
    #     11: 28,  # 车辆非法位移
    # }
    # BUSINESS_ALERT_CONTINUED = {
    #     0: 1,  # 超速告警
    #     3: 23,  # 路线偏离
    #     4: 2,  # 疲劳驾驶
    #     6: 13,  # 超速预警
    #     7: 14,  # 疲劳驾驶预警
    #     9: 26,  # 车辆被盗
    #     12: 29,  # 碰撞预警
    #     13: 30,  # 侧翻预警
    # }
    # DEVICE_ALERT_CONTINUED = {
    #     0: 4,  # GNSS模块发生故障
    #     1: 5,  # GNSS天线未接或被剪掉
    #     2: 6,  # GNSS天线短路
    #     3: 7,  # 终端主电源欠压
    #     4: 8,  # 终端主电源掉电
    #     5: 9,  # 终端LED或显示器故障
    #     6: 10,  # TTS模块故障
    #     7: 11,  # 摄像头故障
    # }

    BUSINESS_ALERT_RECEIVE_RESET_0 = {
        1: 1 << 20,  # 进出区域
        2: 1 << 21,  # 进出路线
        5: 1 << 3,  # 危险预警
        8: 1 << 22,  # 路段行驶时间不足或过长
        10: 1 << 27,  # 车辆非法点火
        11: 1 << 28,  # 车辆非法位移
    }
    BUSINESS_ALERT_CONTINUED = {
        0: 1 << 1,  # 超速告警
        3: 1 << 23,  # 路线偏离
        4: 1 << 2,  # 疲劳驾驶
        6: 1 << 13,  # 超速预警
        7: 1 << 14,  # 疲劳驾驶预警
        9: 1 << 26,  # 车辆被盗
        12: 1 << 29,  # 碰撞预警
        13: 1 << 30,  # 侧翻预警
    }
    DEVICE_ALERT_CONTINUED = {
        0: 1 << 4,  # GNSS模块发生故障
        1: 1 << 5,  # GNSS天线未接或被剪掉
        2: 1 << 6,  # GNSS天线短路
        3: 1 << 7,  # 终端主电源欠压
        4: 1 << 8,  # 终端主电源掉电
        5: 1 << 9,  # 终端LED或显示器故障
        6: 1 << 10,  # TTS模块故障
        7: 1 << 11,  # 摄像头故障
    }

    auth_map = dict()  # authentication_code: DataAccessProtocol
    phone_map = dict()  # phone_num: DataAccessProtocol
    # registed_map = TwoWayDict()  # phone_num: authentication_code and authentication_code: phone_num
    # vehicle_map = dict()  # phone_num: vehicle_id

    def __init__(self):
        self.buffer = b''
        self.phone_num = None
        self.authentication_code = None
        self.vehicle_id = None
        self.next_message_num = 0
        self.last_alarm_flag = 0
        self.is_authenticated = False

    def connectionMade(self):
        logging.info('new connect come')
        self.setTimeout(self.timeOut)

    # def sendData(self, data):
    #     logging.debug('send to mdvr: %s' % printfuled(data))
    #     self.transport.write(data)
    #     self.next_message_num += 1
    #     self.next_message_num &= 65535

    def send_message(self, message_id, message_body, message_num):
        message = Message(message_id, int(self.phone_num), message_body, message_num)
        self.transport.write(bytes(message))
        logging.debug('send to mdvr: %s' % str(message))
        self.next_message_num += 1
        self.next_message_num &= 65535

    def send_regiser_reply(self, reply_num, result, authentication_code):
        message_body = int_to_word(reply_num) + int_to_byte(result)
        if result == 0:
            message_body += str_to_string(authentication_code)
        self.send_message(Message.ID_TERMINAL_REGISTER_REPLY, message_body, reply_num)
        if result == 0:
            # self.authentication_code = authentication_code
            # self.tmp_map.pop(self.phone_num, None)
            # self.mdvr_map[authentication_code] = self
            # self.registed_map[self.phone_num] = authentication_code
            pass

    def send_general_reply(self, reply_num, reply_id, result):
        # if result == 0 and reply_id == Message.ID_TERMINAL_AUTHENTICATION:
        #     self.send_on_off_line_to_mq(0)
        #     self.tmp_map.pop(self.phone_num, None)
        #     self.mdvr_map[self.authentication_code] = self
        #     self.vehicle_id = vehicle_id
        #     # self.registed_map[self.phone_num] = self.authentication_code
        #     self.is_authenticated = True
        message_body = int_to_word(reply_num) + reply_id + int_to_byte(result)
        self.send_message(self.MESSAGE_ID['platform common reply'], message_body, self.next_message_num)
        # if result == 0 and reply_id == Message.ID_TERMINAL_LOGOUT:
        #     # self.mdvr_map.pop(self.authentication_code, None)
        #     # self.registed_map.pop(self.phone_num, None)
        #     self.transport.loseConnection()
        if result == 3:
            logging.warning('message id %s is not support' % printfuled(reply_id))

    def send_authentication_reply(self, reply_num, result, vehicle_id):
        if result == 0:
            self.send_on_off_line_to_mq(1)
            # self.phone_map.pop(self.phone_num, None)
            self.phone_map[self.phone_num] = self
            self.auth_map[self.authentication_code] = self
            self.vehicle_id = vehicle_id
            self.is_authenticated = True
        self.send_general_reply(reply_num, Message.ID_TERMINAL_AUTHENTICATION, result)

    def send_logout_reply(self, reply_num, result):
        if result == 0:
            self.transport.loseConnection()
        self.send_general_reply(reply_num, Message.ID_TERMINAL_LOGOUT, result)

    def send_set_polygons_region(self, message_num, region_id, region_property, points_list,
                                 start_time=None, end_time=None, max_speed=None,
                                 over_speed_duration=None):
        message_body = int_to_dword(region_id) + int_to_word(region_property)
        if region_property & (1 << 0):
            message_body += (time_to_bcd(start_time) + time_to_bcd(end_time))
        if region_property & (1 << 1):
            message_body += (int_to_word(max_speed) + int_to_byte(over_speed_duration))
        message_body += int_to_word(len(points_list))
        points_message = b''
        for point in points_list:
            longitude = int(point['Longitude'] * 1000000)
            latitude = int(point['Latitude'] * 1000000)
            points_message += (int_to_dword(latitude) + int_to_dword(longitude))
        message_body += points_message
        self.send_message(Message.ID_SET_POLYGONS_REGION, message_body, message_num)

    def send_del_polygons_region(self, message_num, region_list):
        messagae_body = int_to_byte(len(region_list))
        for region in region_list:
            messagae_body += int_to_dword(region)
        self.send_message(Message.ID_DEL_POLYGONS_REGION, messagae_body,message_num)

    def send_set_route(self, message_num, route_id, route_property, points_list, start_time=None,
                       end_time=None):
        message_body = int_to_dword(route_id) + int_to_word(route_property)
        if route_property & (1 << 0):
            message_body += (time_to_bcd(start_time) + time_to_bcd(end_time))
        message_body += int_to_word(len(points_list))
        points_message = b''
        for point in points_list:
            inflexion_id = point['InflexionId']
            road_id = point['RoadId']
            longitude = int(point['Longitude'] * 1000000)
            latitude = int(point['Latitude'] * 1000000)
            road_width = point['RoadWidth']
            road_property = point['RoadAttribute']
            points_message += (int_to_dword(inflexion_id) + int_to_dword(road_id) +
                               int_to_dword(latitude) + int_to_dword(longitude) +
                               int_to_byte(road_width) + int_to_byte(road_property))
            if road_property & (1 << 0):
                max_route_time = point['MaxRoute']
                min_route_time = point['MinRoute']
                points_message += (int_to_word(max_route_time) + int_to_word(min_route_time))
            if road_property & (1 << 1):
                max_speed = point['MaxSpeed']
                over_speed_duration = point['OverSpeedDuration']
                points_message += (int_to_word(max_speed) + int_to_byte(over_speed_duration))
        message_body += points_message
        self.send_message(Message.ID_SET_ROUTE, message_body, message_num)

    def send_del_route(self, message_num, route_id_list):
        message_body = int_to_byte(len(route_id_list))
        for route_id in route_id_list:
            message_body += int_to_dword(route_id)
        self.send_message(Message.ID_DEL_ROUTE, message_body, message_num)

    def send_query_all_param(self, message_num):
        self.send_message(Message.ID_QUERY_ALL_PARAM, b'', message_num)

    def send_query_part_param(self, message_num, param_id_list):
        message_body = int_to_byte(len(param_id_list))
        for param_id in param_id_list:
            message_body += int_to_dword(param_id)
        self.send_message(Message.ID_QUERY_PART_PARAM, message_body, message_num)

    def send_set_param(self, message_num, params_list):
        message_body = int_to_byte(len(params_list))
        for param in params_list:
            param_id = param['ParaId']
            param_len = param['ParaLen']
            param_value = PARAM_MAP[param_len](param['ParaValue'])
            if param_len == 3:
                param_len = len(param_value)
            message_body += (int_to_dword(param_id) + int_to_byte(param_len) + param_value)
        self.send_message(Message.ID_SET_PARAM, message_body, message_num)

    def send_test808(self, message_id, message_body):
        self.send_message(message_id, message_body, self.next_message_num)

    def dataReceived(self, data):
        # assert isinstance(data, bytes)
        logging.debug('receive from mdvr: %s' % printfuled(data))
        self.resetTimeout()
        # self.sendData(binascii.a2b_hex('7e80010005018812345678fbd600000102002b7e'))
        if self.buffer:
            self.buffer += data
        else:
            if data.startswith(self.MESSAGE_START):
                self.buffer += data
            else:
                logging.warning('this message is not start with 7e, ignore it')

        while self.buffer:
            index = self.buffer.find(self.MESSAGE_END, 1)
            if index == -1:
                break
            else:
                message = self.buffer[: index + 1]
                self.buffer = self.buffer[index + 1:]
                message_head_body_checksum = recover_escape(message[1: -1])
                if not check_checksum(message_head_body_checksum):
                    logging.warning('checksum of this message is not correct, ignore it')
                else:
                    phone_num = printfuled(message_head_body_checksum[4: 10])
                    if self.phone_num is None:
                        self.phone_num = phone_num
                    if self.phone_num != phone_num:
                        logging.warning('phone number is not the same as before: '
                                        'this: %s, before: %s, ignore it' % (phone_num, self.phone_num))
                    else:
                        message_body_property = word_to_int(message_head_body_checksum[2: 4])
                        is_separate = message_body_property & 0b0010000000000000
                        is_rsa = message_body_property & 0b0000010000000000
                        message_body_len = message_body_property & 0b0000001111111111
                        if is_separate or is_rsa:
                            logging.warning('separate or rsa is not support, ignore it')
                        else:
                            message_head = message_head_body_checksum[:12]
                            message_body = message_head_body_checksum[12: -1]
                            message_id = message_head[: 2]
                            message_num = word_to_int(message_head[10: 12])
                            if len(message_body) != message_body_len:
                                logging.warning('message len in message head is not correct, ignore it')
                            else:
                                if (not self.is_authenticated) and message_id not in \
                                        (Message.ID_TERMINAL_REGISTER, Message.ID_TERMINAL_AUTHENTICATION):
                                    logging.warning('unauthenticated, close it')
                                    self.transport.loseConnection()
                                else:
                                    handle = message_handle.get(message_id, lambda *args:
                                    # logging.warning('message id %s is not support, ignore it' % printfuled(message_id))
                                    self.send_general_reply(message_num, message_id, 3)
                                                                )
                                    handle(self, message_body, message_num)

    @reg_handle(Message.ID_TERMINAL_REGISTER)
    def terminal_register_handle(self, message_body, message_num):
        self.phone_map[self.phone_num] = self
        province_id = word_to_int(message_body[: 2])
        city_id = word_to_int(message_body[2: 4])
        manufacturer_id = byte_to_str(message_body[4: 9])
        terminal_type = byte_to_str(message_body[9: 29].rstrip(b'\x00'))
        terminal_id = byte_to_str(message_body[29: 36].rstrip(b'\x00')).rjust(7, '0')
        plate_color = message_body[36]
        plate = string_to_str(message_body[37:])
        self.authentication_code = manufacturer_id + terminal_id
        self.vehicle_id = plate

        message_to_mq = {'UID': self.authentication_code,
                         'SerialNo': message_num,
                         'ManufactureId': manufacturer_id,
                         'Model': terminal_type,
                         'TerminalId': terminal_id,
                         'VehicleId': plate,
                         'SIM': self.phone_num}
        self.send_to_mq(MDVR_EXCHANGE, 'Register', message_to_mq)

    @reg_handle(Message.ID_TERMINAL_AUTHENTICATION)
    def terminal_authentication_handle(self, message_body, message_num):
        self.authentication_code = string_to_str(message_body)

        # if self.authentication_code == self.registed_map.get(self.phone_num, None):
        if self.is_authenticated:
            self.send_authentication_reply(message_num, 0, self.vehicle_id)
            # self.auth_map[self.authentication_code] = self
        else:
            self.phone_map[self.phone_num] = self
            message_to_mq = {'UID': self.authentication_code,
                             'SerialNo': message_num,
                             'RegisterNo': self.authentication_code,
                             'SIM': self.phone_num}
            self.send_to_mq(MDVR_EXCHANGE, 'Authenticate', message_to_mq)

    @reg_handle(Message.ID_LOCATION_INFORMATION)
    def location_information_handle(self, message_body, message_num):
        alarm_flag = dword_to_int(message_body[: 4])
        # alarm_flag_list = int_to_bitlist(alarm_flag, 32)
        status_flag = dword_to_int(message_body[4: 8])
        # status_flag_list = int_to_bitlist(status_flag, 32)
        # latitude = Decimal(str(dword_to_int(message_body[8: 12]))) / 1000000
        latitude = dword_to_int(message_body[8: 12]) / 1000000
        # if status_flag_list[2]:
        if status_flag & 0b100:
            latitude = -latitude
        # longitude = Decimal(str(dword_to_int(message_body[12: 16]))) / 1000000
        longitude = dword_to_int(message_body[12: 16]) / 1000000
        # if status_flag_list[3]:
        if status_flag & 0b1000:
            longitude = -longitude
        height = word_to_int(message_body[16: 18])
        # speed = Decimal(str(word_to_int(message_body[18: 20]))) / 10
        speed = word_to_int(message_body[18: 20]) / 10
        direction = word_to_int(message_body[20: 22])
        # gpstime_without_line = printfuled(message_body[22: 28])
        # gpstime = '-'.join(gpstime_without_line[i: i+2] for i in range(0, len(gpstime_without_line), 2))
        # gpstime = bcd_to_time(message_body[22: 28])
        gpstime = bcd_to_time_for_mq(message_body[22: 28])
        additional_index = 28
        additional_info_total = ''
        while True:
            try:
                additional_id = message_body[additional_index]
                additional_index += 1
                additional_len = message_body[additional_index]
                additional_index += 1
                additional_info = printfuled(message_body[additional_index: additional_index+additional_len])
                additional_index += additional_len
                additional_info_total += '%d,%d,%s;' % (additional_id, additional_len, additional_info)
            except IndexError:
                break

        gps_message_to_mq = {'UID': self.authentication_code,
                             # 'Valid': status_flag_list[1],
                             'Valid': 'A' if status_flag & 0b10 else 'N',
                             # 'Longitude': float(longitude),
                             # 'Latitude': float(latitude),
                             'Longitude': '%.6f' % longitude,
                             'Latitude': '%.6f' % latitude,
                             'Height': height,
                             # 'Speed': float(speed),
                             'Speed': '%.1f' % speed,
                             'Direction': '%d' % direction,
                             # 'GpsTime': time_to_time_str(gpstime),
                             'GpsTime': gpstime,
                             'AlarmFlag': alarm_flag,
                             'Status': status_flag,
                             'VehicleId': self.vehicle_id}
        self.send_to_mq(GPS_EXCHANGE, 'GpsInfo', gps_message_to_mq)
        self.send_general_reply(message_num, Message.ID_LOCATION_INFORMATION, 0)

        # if alarm_flag_list[0] == 1:
        if alarm_flag & 0x1:
            alarm_message_to_mq = {'UID': self.authentication_code,
                                   'SerialNo': message_num,
                                   'GpsInfo': gps_message_to_mq,
                                   'AdditionalInfo': additional_info_total}
            self.send_to_mq(MDVR_EXCHANGE, 'AlarmInfo', alarm_message_to_mq)

        for alert_type, alarm_flag_index in self.BUSINESS_ALERT_RECEIVE_RESET_0.items():
            # if alarm_flag_list[alarm_flag_index]:
            if alarm_flag & alarm_flag_index:
                business_alert_message_to_mq = {
                    'UID': self.authentication_code,
                    'SerialNo': message_num,
                    'GpsInfo': gps_message_to_mq,
                    'AlertType': alert_type,
                    'AdditionalInfo': additional_info_total
                }
                self.send_to_mq(MDVR_EXCHANGE, 'BusinessAlert', business_alert_message_to_mq)

        need_to_alert_flag = (alarm_flag ^ self.last_alarm_flag) & alarm_flag
        # need_to_alert_flag_list = int_to_bitlist(need_to_alert_flag, 32)
        for alert_type, alarm_flag_index in self.BUSINESS_ALERT_CONTINUED.items():
            # if need_to_alert_flag_list[alarm_flag_index]:
            if need_to_alert_flag & alarm_flag_index:
                business_alert_message_to_mq = {
                    'UID': self.authentication_code,
                    'SerialNo': message_num,
                    'GpsInfo': gps_message_to_mq,
                    'AlertType': alert_type,
                    'AdditionalInfo': additional_info_total
                }
                self.send_to_mq(MDVR_EXCHANGE, 'BusinessAlert', business_alert_message_to_mq)
        for alert_type, alarm_flag_index in self.DEVICE_ALERT_CONTINUED.items():
            # if need_to_alert_flag_list[alarm_flag_index]:
            if need_to_alert_flag & alarm_flag_index:
                business_alert_message_to_mq = {
                    'UID': self.authentication_code,
                    'SerialNo': message_num,
                    'GpsInfo': gps_message_to_mq,
                    'AlertType': alert_type,
                    'AdditionalInfo': additional_info_total
                }
                self.send_to_mq(MDVR_EXCHANGE, 'DeviceAlert', business_alert_message_to_mq)
        self.last_alarm_flag = alarm_flag

    @reg_handle(Message.ID_TERMINAL_LOGOUT)
    def terminal_logout_handle(self, message_body, message_num):
        message_to_mq = {'UID': self.authentication_code,
                         'SerialNo': message_num,
                         'RegisterNo': self.authentication_code,
                         'SIM': self.phone_num}
        self.send_to_mq(MDVR_EXCHANGE, 'UnRegister', message_to_mq)

    @reg_handle(Message.ID_HEART_BEAT)
    def heart_beat_handle(self, message_body, message_num):
        self.send_general_reply(message_num, Message.ID_HEART_BEAT, 0)

    @reg_handle(Message.ID_TERMINAL_COMMON_REPLY)
    def terminal_common_reply(self, message_body, message_num):
        reply_num = word_to_int(message_body[: 2])
        reply_id = word_to_int(message_body[2: 4])
        result = message_body[4]
        message_to_mq = {'UID': self.authentication_code,
                         'SerialNo': message_num,
                         'ResponseSerialNo': reply_num,
                         'MessageID': reply_id,
                         'Result': result}
        self.send_to_mq(MDVR_EXCHANGE, 'GenenalResponse', message_to_mq)

    @reg_handle(Message.ID_QUERY_PARAM_REPLY)
    def query_param_reply(self, message_body, message_num):
        reply_num = word_to_int(message_body[: 2])
        param_count = message_body[2]
        params_list = []
        cur_index = 3
        for i in range(param_count):
            param_id = dword_to_int(message_body[cur_index: cur_index + 4])
            cur_index += 4
            param_len = message_body[cur_index]
            cur_index += 1
            if param_len not in (1, 2, 4):
                param_len_json = 3
            else:
                param_len_json = param_len
            param_value = str(PARAM_REPLY_MAP[param_len_json](message_body[cur_index: cur_index + param_len]))
            cur_index += param_len
            params_list.append({'ParaId': param_id,
                                'ParaLen': param_len_json,
                                'ParaValue': param_value})
        message_to_mq = {'UID': self.authentication_code,
                         'SerialNo': message_num,
                         'ResponseSerialNo': reply_num,
                         'ParamCount': param_count,
                         'ParamList': params_list}
        self.send_to_mq(MDVR_EXCHANGE, 'QueryParaResponse', message_to_mq)

    def send_to_mq(self, exchange, routing_key, message):
        message_to_mq = json.dumps(message)
        self.factory.mq.send_message(routing_key=routing_key,
                                     uid=self.authentication_code,
                                     message=message_to_mq,
                                     exchange=exchange)
        logging.info('send to mq: exchange: %s, routing key: %s, json: %s' %
                     (exchange, routing_key, message_to_mq))

    def send_on_off_line_to_mq(self, on_off_line_flag):
        message = {'UID': self.authentication_code,
                   'OnOffLineTime': time_to_time_str(datetime.datetime.now()),
                   'IsOnline': on_off_line_flag}
        self.send_to_mq(MDVR_EXCHANGE, 'OnOffline', message)

    def timeoutConnection(self):
        logging.warning('time out')
        self.transport.loseConnection()

    def connectionLost(self, reason=connectionDone):
        self.setTimeout(None)
        if self.authentication_code:
            self.send_on_off_line_to_mq(0)
        self.auth_map.pop(self.authentication_code, None)
        self.phone_map.pop(self.phone_num, None)
        self.is_authenticated = False
        logging.info('connection close: SIM: %s, authentication code: %s' %
                     (self.phone_num, self.authentication_code))
        # logging.info('%s\n%s\n%s' % (self.mdvr_map, self.tmp_map, self.registed_map))

    @classmethod
    def get_protocol(cls, phone_num=None, authentication_code=None, default=None):
        protocol = default
        if authentication_code:
            protocol = cls.auth_map.get(authentication_code, None)
        if protocol == default or phone_num:
            protocol = cls.phone_map.get(phone_num, None)
        return protocol


if __name__ == '__main__':
    import timeit
    import cProfile
    a = DataAccessProtocol()
    a.authentication_code = '123459876543'
    a.vehicle_id = 'a00001'
    a.send_to_mq = lambda *args, **kwargs: None
    a.send_general_reply = lambda *args, **kwargs: None
    b = binascii.a2b_hex('000000000000000204567d8804567d880000000000001608011430490104000000000202000003020000')
    c = timeit.timeit(lambda: a.location_information_handle(b, 1), number=100000)
    d = binascii.a2b_hex('313233343539383736353433')
    e = binascii.a2b_hex('000000000000313233343561626364656637383930313233343536373839303938373635343301424a30303031')

    def kkk(n):
        for i in range(n):
            a.location_information_handle(b, 1)
    # cProfile.run('kkk(1000)', '111')
    # cProfile.main()
    print(c)
    print(timeit.timeit(lambda: a.heart_beat_handle(b'', 1), number=100000))
    print(timeit.timeit(lambda: a.terminal_authentication_handle(d, 1), number=100000))
    print(timeit.timeit(lambda: a.terminal_logout_handle(b'', 1), number=100000))
    print(timeit.timeit(lambda: a.terminal_register_handle(e, 1), number=100000))
