#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import re
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


#############################################
### インターフェース一覧テーブル(interface_list)作成

### interface_listテーブルを削除 & 作成
cur.execute("DROP TABLE interface_list")
conn.commit()
sql_create_table = '''CREATE TABLE interface_list (
                        hostname varchar(30)
                      , interface_name varchar(50)
                      , admin_state varchar(10)
                      , link_state varchar(10)
                      , bandwidth varchar(20)
                      , lag_group varchar(50)
                      , lag_member varchar(500)
                      , description varchar(250)
                      , media_type varchar(50)
                      )'''
cur.execute(sql_create_table) 


### モデル名取得し、それをもとにインターフェースの情報を取得
### [ホスト名, インターフェース名, Adminステート, リンク状態, 帯域幅, LAGグループ, LAGメンバー, Description] の順にDBに格納

for dct in node_list:
    try:
        host = dct["name"]
        ostype = dct["ostype"]
        session = session_create(host, domain, username, password, ostype)
        interfaces = session.get_interface()
        for i in interfaces:
            interface_name = i.name
            admin_state = i.admin_state
            link_state = i.link_state
            speed = i.speed
            lag_group = i.lag_group
            lag_member = i.lag_member
            description = i.description
            media_type = i.media_type

            # 表記揺れの吸収
            if ("kbit" in speed) or ("Kbit" in speed) or ("kbps" in speed):
                speed = re.sub("kbit.*", "", speed).strip()
                speed = re.sub("Kbit.*", "", speed).strip()
                speed = re.sub("kbps.*", "", speed).strip()
                speed = re.sub("000000$","Gbps", speed)
            if ("mbit" in speed) or ("Mbit" in speed) or ("mbps" in speed):
                speed = re.sub("mbit.*", "", speed).strip()
                speed = re.sub("Mbit.*", "", speed).strip()
                speed = re.sub("mbps.*", "", speed).strip()
                speed = re.sub("000$","Gbps", speed)
            if "G" in speed:
                speed = re.sub(r'\D', '', speed) + "Gbps"
            if "Po" in interface_name:
                if ("Port-Channel" in interface_name) or ("Port-channel" in interface_name):
                    pass
                else:
                    interface_name = interface_name.replace("Po", "Port-Channel")
            if "Po" in lag_group:
                if ("Port-Channel" in lag_group) or ("Port-channel" in lag_group):
                    pass
                else:
                    lag_group = lag_group.replace("Po", "Port-Channel")
            if ("SX" in media_type) or (media_type == "SFP-GE-S"):
                media_type = "1000BASE-SX"
            if "LX" in media_type:
                media_type = "1000BASE-LX"
            if "LH" in media_type:
                media_type = "1000BASE-LH"
            if ("10G" in media_type) and ("SR" in media_type):
                media_type = "10GBASE-SR"
            if ("10G" in media_type) and ("LR" in media_type):
                media_type = "10GBASE-LR"
            if ("40G" in media_type) and ("SR4" in media_type):
                media_type = "40GBASE-SR4"
            if ("40G" in media_type) and ("LR4" in media_type):
                media_type = "40GBASE-LR4"
            if ("100G" in media_type) and ("SR4" in media_type):
                media_type = "100GBASE-SR4"
            if ("100G" in media_type) and ("SR10" in media_type):
                media_type = "100GBASE-SR10"
            if ("100G" in media_type) and ("LR4" in media_type):
                media_type = "100GBASE-LR4"

            sql_insert_interface_list = '''
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
                                        , media_type
                                        ) VALUES (
                                          "{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}", "{7}", "{8}"
                                        )
                                       '''.format(host, interface_name, admin_state, link_state, speed, lag_group, lag_member, description, media_type)

            cur.execute(sql_insert_interface_list)
            conn.commit()
        session.close()
    except:
        pass


### DB 切断
cur.close()
conn.close()
