#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import mysql.connector
import get_sysinfo
import configparser
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


###############################################################################
###  HTMLで表示するデータの元ネタ情報を収集し、テーブルに格納していくスクリプト


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


#############################################
### ノード一覧テーブル(node_list)にデータ投入

### DB 接続
conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
cur = conn.cursor()

### ノード名、ベンダー名取得
cur.execute("select name,type,mgmt_ip from node_master_list")
temp = cur.fetchall()
node_list = []
for i in temp:
    d = {}
    d["name"], d["type"], d["mgmt_ip"] = i
    node_list.append(d)

### node_listテーブルの既存データを削除
cur.execute("delete from node_list")

### モデル名、シリアルNo、バージョンを取得して、
### [ホスト名, モデル名, ベンダー名, シリアルNo, バージョン] の順にDBに格納

sysinfo = get_sysinfo.session()
function_dict = {
                 "junos": sysinfo.junos, 
                 "catalyst": sysinfo.ios, 
                 "cisco": sysinfo.ios, 
                 "asr": sysinfo.iosxr, 
                 "cloudengine": sysinfo.cloudengine, 
                 "netengine": sysinfo.netengine, 
                 "brocade": sysinfo.nos, 
                 "arista": sysinfo.arista
                }

for d in node_list:
    host, type, mgmt_ip = d["name"], d["type"], d["mgmt_ip"]
    try:
        function_dict[d["type"]](host, username,password)
        model, version, serial = sysinfo.model, sysinfo.os_version, sysinfo.serial
        sql_insert = 'insert into node_list(name, model, type, serial, version, mgmt_ip) values("%s", "%s", "%s", "%s", "%s", "%s")' % (host, model, type, serial, version, mgmt_ip)
        cur.execute(sql_insert)
        conn.commit()
    except:
        pass


#############################################
### インターフェース一覧テーブル(node_list)作成

### ノード名、ベンダー名取得
cur.execute("select name,type from node_master_list")
nodes = cur.fetchall()

### interface_listテーブルのデータを削除
cur.execute("delete from interface_list")

### モデル名取得し、それをもとにインターフェースの情報を取得
### [ホスト名, 物理インターフェース名, 帯域幅, リンク状態, Description] の順にDBに格納
for i in range(len(nodes)):
    hostname = nodes[i][0]
    type = nodes[i][1]
    if type == "juniper":
        if_list = get_interface_juniper(hostname)
        for interface in if_list:
            bandwidth, link_state, description = get_interface_info_juniper(hostname, interface)
            sql_insert = 'insert into interface_list(hostname, physical_interface, bandwidth, link_state, description) values("%s", "%s", "%s", "%s", "%s")' % (hostname, interface, bandwidth, link_state, description)
            cur.execute(sql_insert)
            conn.commit()
    elif type == "cisco":
        pass
    elif type == "huawei":
        pass
    elif type == "brocade":
        pass
    elif type == "arista":
        pass


### DB 切断
cur.close()
conn.close()
