# -*- coding:utf-8 -*-
import json
import logging
from decimal import Decimal
import traceback

from src.dataAccessProtocol import DataAccessProtocol
from src.tools import *

__author__ = 'shangxc'

REGION_PROPERTY_MAP = {
    # 0：根据时间；1：限速；2：进区域报警给驾驶员；3：进区域报警给平台；4：出区域报警给驾驶员；
    # 5：出区域报警给平台；6：北纬；7：南纬；8：东经；9：西经；
    0: 1 << 0,
    1: 1 << 1,
    2: 1 << 2,
    3: 1 << 3,
    4: 1 << 4,
    5: 1 << 5,
    6: 0,
    7: 1 << 6,
    8: 0,
    9: 1 << 7,
}

ROUTE_PROPERTY_MAP = {
    # 0：根据时间；2：进路线报警给驾驶员；3：进路线报警给平台；4：出路线报警给驾驶员；5：出路线报警给平台；
    0: 1 << 0,
    2: 1 << 2,
    3: 1 << 3,
    4: 1 << 4,
    5: 1 << 5,
}

ROAD_PROPERTY_MAP = {
    # 0：根据时间；1：限速；2：北纬；3：南纬；4：东经；5：西经；
    0: 1 << 0,
    1: 1 << 1,
    2: 0,
    3: 1 << 2,
    4: 0,
    5: 1 << 3,
}

json_message_handle = {}


def reg_handle(routing_key):
    def f(func):
        json_message_handle[routing_key] = func
        return func

    return f


def send_message(callback, *args, phone_num=None, authentication_code=None, **kwargs):
    protocol = DataAccessProtocol.get_protocol(phone_num, authentication_code)
    if protocol:
        callback(protocol, *args, **kwargs)
    else:
        logging.warning('mdvr is offline')


@reg_handle('RegisterResponse')
def register_response_handle(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    result_type = int(message['ResultType'])
    register_no = str(message['RegisterNo'])
    sim = str(message['SIM'])
    vehicle_id = message['VehicleId']
    send_message(DataAccessProtocol.send_regiser_reply,
                 *(serial_no, result_type, register_no),
                 phone_num=sim)


@reg_handle('AuthenticateResponse')
def authenticate_response_handle(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    register_no = str(message['RegisterNo'])
    sim = str(message['SIM'])
    is_passed = int(message['IsPassed'])
    vehicle_id = message['VehicleId']
    send_message(DataAccessProtocol.send_authentication_reply,
                 *(serial_no, is_passed, vehicle_id),
                 phone_num=sim)


@reg_handle('UnRegisterResponse')
def unregister_response_handle(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    register_no = str(message['RegisterNo'])
    sim = int(message['SIM'])
    is_passed = int(message['IsPassed'])
    send_message(DataAccessProtocol.send_logout_reply,
                 *(serial_no, is_passed),
                 authentication_code=uid)


@reg_handle('PolygonsRegion')
def set_polygons_region(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    region_id = int(message['RegionID'])
    region_property_list = message['RegionProperty']
    # 0：根据时间；1：限速；2：进区域报警给驾驶员；3：进区域报警给平台；4：出区域报警给驾驶员；
    # 5：出区域报警给平台；6：北纬；7：南纬；8：东经；9：西经；
    region_property = 0
    for i in region_property_list:
        region_property += REGION_PROPERTY_MAP[i]
    start_time = None
    end_time = None
    if 0 in region_property_list:
        start_time = time_str_to_time(message['StartTime'])
        end_time = time_str_to_time(message['EndTime'])
    max_speed = None
    over_speed_duration = None
    if 1 in region_property_list:
        max_speed = int(message['MaxSpeed'])
        over_speed_duration = int(message['OverSpeedDuration'])
    point_count = int(message['PointCount'])
    points_list = []  # message['PointsList']
    for point in message['PointsList']:
        points_list.append({'Longitude': abs(Decimal(str(point['Longitude']))),
                            'Latitude': abs(Decimal(str(point['Latitude'])))})
    send_message(DataAccessProtocol.send_set_polygons_region,
                 *(serial_no, region_id, region_property, points_list,
                   start_time, end_time, max_speed, over_speed_duration),
                 authentication_code=uid)


@reg_handle('DelPolygonsRegion')
def del_polygons_region(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    region_count = int(message['RegionCount'])
    region_list = []
    if region_count != 0:
        region_list = message['RegionList']
    send_message(DataAccessProtocol.send_del_polygons_region,
                 *(serial_no, region_list),
                 authentication_code=uid)


@reg_handle('RouteInfo')
def set_route(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    route_id = int(message['RouteId'])
    route_property_list = message['RouteAttribute']
    route_property = 0
    for i in route_property_list:
        route_property += ROUTE_PROPERTY_MAP[i]
    start_time = None
    end_time = None
    if 0 in route_property_list:
        start_time = time_str_to_time(message['StartTime'])
        end_time = time_str_to_time(message['EndTime'])
    point_count = int(message['PointCount'])
    points_list = []
    for point in message['PointsList']:
        p = {}
        p['InflexionId'] = int(point['InflexionId'])
        p['RoadId'] = int(point['RoadId'])
        p['Longitude'] = abs(float(point['Longitude']))
        p['Latitude'] = abs(float(point['Latitude']))
        p['RoadWidth'] = int(point['RoadWidth'])
        road_property_list = point['RoadAttribute']
        road_property = 0
        for i in road_property_list:
            road_property += ROAD_PROPERTY_MAP[i]
        p['RoadAttribute'] = road_property
        if 0 in road_property_list:
            p['MaxRoute'] = int(point['MaxRoute'])
            p['MinRoute'] = int(point['MinRoute'])
        if 1 in road_property_list:
            p['MaxSpeed'] = int(point['MaxSpeed'])
            p['OverSpeedDuration'] = int(point['OverSpeedDuration'])
        points_list.append(p)
    send_message(DataAccessProtocol.send_set_route,
                 *(serial_no, route_id, route_property, points_list, start_time, end_time),
                 authentication_code=uid)


@reg_handle('DelRouteRegion')
def del_route(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    route_count = int(message['RouteCount'])
    route_list = []
    if route_count != 0:
        route_list = message['RouteList']
    send_message(DataAccessProtocol.send_del_route,
                 *(serial_no, route_list),
                 authentication_code=uid)


@reg_handle('QueryAllParam')
def del_route(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    send_message(DataAccessProtocol.send_query_all_param,
                 serial_no,
                 authentication_code=uid)


@reg_handle('QueryPartParam')
def del_route(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    param_count = int(message['ParamCount'])
    param_list = []
    if param_count != 0:
        param_list = message['ParamList']
    send_message(DataAccessProtocol.send_query_part_param,
                 *(serial_no, param_list),
                 authentication_code=uid)

@reg_handle('SetTermParam')
def del_route(message):
    uid = str(message['UID'])
    serial_no = int(message['SerialNo'])
    param_count = int(message['ParamCount'])
    param_list = []
    if param_count != 0:
        for param in message['ParamList']:
            p = {}
            p['ParaId'] = int(param['ParaId'])
            p['ParaLen'] = int(param['ParaLen'])
            if p['ParaLen'] == 3:
                p['ParaValue'] = str(param['ParaValue'])
            else:
                p['ParaValue'] = int(param['ParaValue'])
            param_list.append(p)
        send_message(DataAccessProtocol.send_set_param,
                     *(serial_no, param_list),
                     authentication_code=uid)


@reg_handle('Test808')
def test_808(message):
    message_id = int_to_word(int(message['MessageID']))
    sim = str(message['SIM']).rjust(12, '0')
    message_body = binascii.a2b_hex(message['MessageBody'])
    send_message(DataAccessProtocol.send_test808,
                 *(message_id, message_body),
                 phone_num=sim)


def on_message(channel, merhod_frame, header_frame, body):
    logging.info('receive from mq: routing_key: %s, body: %s' %
                 (merhod_frame.routing_key, body.decode()))
    try:
        message = json.loads(body.decode())
    except ValueError:
        logging.warning('message is not json type')
    else:
        routing_key = merhod_frame.routing_key.split('.')[1]
        handle = json_message_handle.get(routing_key,
                                         lambda mess: logging.warning('routing key: %s is not support' % routing_key))

        try:
            handle(message)
        except KeyError as e:
            logging.warning('json message not have key: ' + e.args[0])
        except Exception as e:
            logging.warning('json message not format well')
            logging.error(repr(e))


if __name__ == '__main__':
    print(json_message_handle)
