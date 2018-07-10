#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import mysql.connector
from get_deviceinfo import *
import configparser
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


###############################################################################
###  HTMLで表示するデータの元ネタ情報を収集し、それらをテーブルに格納していくスクリプト


#############################################
### コンフィグ読み込み

config = configparser.ConfigParser()
config.read("config.txt")
db_user = config["database"]["username"]
db_pass = config["database"]["password"]
db_name = config["database"]["database"]
db_host = config["database"]["host"]

username = config["device"]["username"]
password = config["device"]["password"]
domain = config["env"]["domain"]

### DB 接続
conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
cur = conn.cursor()

### ノード名、ベンダー名取得
sql_select1 = 'SELECT name, location, type, mgmt_ip FROM node_master_list'
cur.execute(sql_select1)
data = cur.fetchall()

node_list = []
for i in data:
    param_dct = {}
    param_dct["name"], param_dct["location"], param_dct["type"], param_dct["mgmt_ip"] = i
    node_list.append(param_dct)

### モデル名、シリアルNo、バージョンを取得して、
### [ホスト名, モデル名, ベンダー名, シリアルNo, バージョン] の順にDBに格納

ostype_dct = {"juniper": "junos", 
              "catalyst": "ios", 
              "cisco": "ios", 
              "asr": "iosxr", 
              "cloudengine": "cloudengine", 
              "netengine": "netengine", 
              "brocade": "brocade", 
              "arista": "arista"
             }


#############################################
### BGPピア一覧テーブル(bgppeer_list)作成

### bgppeer_listテーブルのデータを削除
cur.execute("DELETE FROM bgppeer_list")
conn.commit()

### モデル名取得し、それをもとにBGPピアの情報を取得
### [ホスト名、ピアアドレス、タイプ、ピア状態、AS番号、受信経路数、広報経路数] の順にDBに格納

for dct in node_list:
    try:
        host = dct["name"]
        ostype = ostype_dct[dct["type"]]

        session = session_create(host, domain, username, password, ostype)
        bgppeers = session.get_bgppeer()
        for peer in bgppeers:
            peer_address = peer.addr
            peer_type = peer.peer_type
            state = peer.state
            asn = peer.asn
            received_route_num = peer.rcvroutes
            advertise_route_num = peer.advroutes
            peer_description = peer.peer_description

            sql_insert_bgppeer_list = '''
                                        INSERT
                                        INTO
                                          bgppeer_list
                                        (
                                          hostname
                                        , peer_address
                                        , peer_type
                                        , state
                                        , asn
                                        , received_route_num
                                        , advertise_route_num
                                        , peer_description
                                        ) VALUES (
                                          "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}", "{7}"
                                        )
                                       '''.format(host, peer_address, peer_type, state, asn, received_route_num, advertise_route_num, peer_description)

            cur.execute(sql_insert_bgppeer_list)
            conn.commit()
        session.close()
    except:
        pass


### DB 切断
cur.close()
conn.close()
