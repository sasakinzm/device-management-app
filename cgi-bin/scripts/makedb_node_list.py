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


#############################################
### ノード一覧テーブル(node_list)にデータ投入

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

### node_listテーブルの既存データを削除
cur.execute("DELETE FROM node_list")
conn.commit()

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

for dct in node_list:
    host = dct["name"]
    location = dct["location"]
    type = dct["type"]
    mgmt_ip = dct["mgmt_ip"]

    try: 
        ostype = ostype_dct[dct["type"]]
        session = session_create(host, domain, username, password, ostype)
        session.get_sysinfo()
        model = session.model
        version = session.os_version
        serial = session.serial

        sql_insert_node_list = '''
                               INSERT INTO
                                 node_list
                               (
                                 name
                               , location
                               , model
                               , type
                               , serial
                               , version
                               , mgmt_ip
                               ) VALUES (
                                 "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}"
                               )
                               '''.format(host, location, model, type, serial, version, mgmt_ip)

        cur.execute(sql_insert_node_list)
        conn.commit()
        session.close()
    except:
        sql_insert_node_list = '''
                               INSERT INTO
                                 node_list
                               (
                                 name
                               , location
                               , model
                               , type
                               , serial
                               , version
                               , mgmt_ip
                               ) VALUES (
                                 "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}"
                               )
                               '''.format(host, location, "ERROR", type, "ERROR", "ERROR", mgmt_ip)

        cur.execute(sql_insert_node_list)
        conn.commit()
        session.close()


### DB 切断
cur.close()
conn.close()
