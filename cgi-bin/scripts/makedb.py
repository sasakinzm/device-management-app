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
sql_select1 = '''
             SELECT
               name
             , type
             , mgmt_ip
             FROM
               node_master_list
             '''
cur.execute(sql_select1)
data = cur.fetchall()

node_list = []
for i in data:
    param_dict = {}
    param_dict["name"], param_dict["type"], param_dict["mgmt_ip"] = i
    node_list.append(param_dict)

### node_listテーブルの既存データを削除
cur.execute("DELETE FROM node_list")

### モデル名、シリアルNo、バージョンを取得して、
### [ホスト名, モデル名, ベンダー名, シリアルNo, バージョン] の順にDBに格納

ostype_dict = {"juniper": "junos", 
                 "catalyst": "ios", 
                 "cisco": "ios", 
                 "asr": "iosxr", 
                 "cloudengine": "cloudengine", 
                 "netengine": "netengine", 
                 "brocade": "brocade", 
                 "arista": "arista"
                }

for dict in node_list:
    try:
        host = dict["name"]
        type = dict["type"]
        ostype = ostype_dict[dict["type"]]
        mgmt_ip = dict["mgmt_ip"]

        session = session_create(host, domain, username, password, ostype)
        session.get_sysinfo()
        model = session.model
        version = session.os_version
        serial = session.serial

        sql_insert = '''
                     INSERT INTO
                       node_list
                     (
                       name
                     , model
                     , type
                     , serial
                     , version, mgmt_ip
                     ) VALUES (
                       "{0}", "{1}", "{2}", "{3}", "{4}", "{5}"
                     )
                     '''.format(host, model, type, serial, version, mgmt_ip)

        cur.execute(sql_insert)
        conn.commit()
        session.close()
    except:
        pass



#############################################
### インターフェース一覧テーブル(node_list)作成

### ノード名、ベンダー名取得
sql_select2 = '''
              SELECT
                name
              , type
              FROM
               node_master_list
              '''
cur.execute(sql_select2)
nodes = cur.fetchall()

### interface_listテーブルのデータを削除
cur.execute("DELETE FROM interface_list")

### モデル名取得し、それをもとにインターフェースの情報を取得
### [ホスト名, インターフェース名, Adminステート, リンク状態, 帯域幅, LAGグループ, LAGメンバー, Description] の順にDBに格納

for dict in node_list:
    try:
        host = dict["name"]
        ostype = ostype_dict[dict["type"]]

        session = session_create(host, domain, username, password, ostype)
        interfaces = session.get_interfaceinfo()
        for i in interfaces:
            ifname = i.name
            admin_state = i.admin_state
            link_state = i.link_state
            speed = i.speed
            lag_group = i.lag_group
            lag_member = i.lag_member
            description = i.description

            sql_insert = '''
                         INSERT
                         INTO
                           interface_list
                         (
                           hostname
                         , interface_name
                         , admin_state
                         , link_state
                         , bandwidth
                         , lag_group
                         , lag_member
                         , description
                         ) VALUES (
                           "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}", "{7}"
                         )
                         '''.format(host, ifname, admin_state, link_state, speed, lag_group, lag_member, description)

            cur.execute(sql_insert)
            conn.commit()
    except:
        pass


### DB 切断
cur.close()
conn.close()
