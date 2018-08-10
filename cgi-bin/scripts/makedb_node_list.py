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
db_user = config["database"]["username"].replace('"', '')
db_pass = config["database"]["password"].replace('"', '')
db_name = config["database"]["database"].replace('"', '')
db_host = config["database"]["host"].replace('"', '')

username = config["device"]["username"].replace('"', '')
password = config["device"]["password"].replace('"', '')
domain = config["env"]["domain"].replace('"', '')


#############################################
### ノード一覧テーブル(node_list)にデータ投入

### DB 接続
conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
cur = conn.cursor()

### ノード名、ベンダー名取得
sql_select1 = 'SELECT name, location, ostype, mgmt_ip FROM node_master_list'
cur.execute(sql_select1)
data = cur.fetchall()

node_list = []
for i in data:
    param_dct = {}
    param_dct["name"], param_dct["location"], param_dct["ostype"], param_dct["mgmt_ip"] = i
    node_list.append(param_dct)

### node_listテーブルを削除 & 作成
cur.execute("DROP TABLE node_list")
conn.commit()
sql_create_table = '''CREATE TABLE node_list (
                        name varchar(30)
                      , location varchar(50)
                      , model varchar(30)
                      , vender varchar(30)
                      , ostype varchar(15)
                      , serial varchar(100)
                      , version varchar(100)
                      , mgmt_ip varchar(15)
                      )'''
cur.execute(sql_create_table)


### モデル名、シリアルNo、バージョンを取得して、
### [ホスト名, モデル名, ベンダー名, シリアルNo, バージョン] の順にDBに格納

vender_dct = {"junos": "Juniper",
              "ios": "Cisco",
              "ios2600": "Cisco",
              "iosxr": "Cisco",
              "iosxe": "Cisco",
              "nxos": "Cisco",
              "cloudengine": "Huawei",
              "netengine": "Huawei",
              "brocade": "Brocade",
              "arista": "Arista"
              }

for dct in node_list:
    host = dct["name"]
    location = dct["location"]
    ostype = dct["ostype"]
    mgmt_ip = dct["mgmt_ip"]

    try: 
        session = session_create(host, domain, username, password, ostype)
        session.get_sysinfo()
        model = session.model
        version = session.os_version
        serial = session.serial
        vender = vender_dct[ostype]

        sql_insert_node_list = '''
                               INSERT INTO
                                 node_list
                               (
                                 name
                               , location
                               , model
                               , vender
                               , ostype
                               , serial
                               , version
                               , mgmt_ip
                               ) VALUES (
                                 "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}", "{7}"
                               )
                               '''.format(host, location, model, vender, ostype, serial, version, mgmt_ip)

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
                               , vender
                               , ostype
                               , serial
                               , version
                               , mgmt_ip
                               ) VALUES (
                                 "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}", "{7}"
                               )
                               '''.format(host, location, "ERROR", "ERROR", type, "ERROR", "ERROR", mgmt_ip)

        cur.execute(sql_insert_node_list)
        conn.commit()
        session.close()


### DB 切断
cur.close()
conn.close()
