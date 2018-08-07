#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import os
import sys
import mysql.connector
import configparser
sys.path.append("scripts/")
from scripts.get_deviceinfo import *


### フォームデータ読み込み
form = cgi.FieldStorage()


### 変数読み込み
config = configparser.ConfigParser()
config.read("scripts/config.txt")
db_user = config["database"]["username"].replace('"', '')
db_pass = config["database"]["password"].replace('"', '')
db_name = config["database"]["database"].replace('"', '')
db_host = config["database"]["host"].replace('"', '')
username = config["device"]["username"].replace('"', '')
password = config["device"]["password"].replace('"', '')
domain = config["env"]["domain"].replace('"', '')


### OSタイプ判別用ディクショナリ
ostype_dct = {"juniper": "junos",
              "catalyst": "ios",
              "cisco": "ios",
              "asr9k": "iosxr",
              "asr1k": "iosxe",
              "nexus": "nxos",
              "cloudengine": "cloudengine",
              "netengine": "netengine",
              "brocade": "brocade",
              "arista": "arista"
              }


### DB接続、コンフィグ取得
hostname = "none"
if "hostname" in form:
    hostname = form["hostname"].value
    conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
    cur = conn.cursor()
    cur.execute("select name, type from node_list where name='{0}'".format(hostname))
    data = cur.fetchall()
    name, type = data[0]
    device = session_create(hostname, domain, username, password, ostype_dct[type])
    configuration = device.get_hardware()
    configuration = configuration.split("\r\n")
    conn.close()
    device.close()


### HTML作成
print("Content-type:text/html; charset=UTF-8")
print("")
print("<html>")
print("<head>")
print("<meta charset='UTF-8'>")
print("<title> Device Configuration </title>")
print("</head>")
print("<body>")

print("<h1> Hardware Information of {0} </h1>".format(hostname))
print("<hr>")

try:
    print("<pre>")
    for line in configuration:
        print(line)
    print("</pre>")
except:
    print("<p> Error! </p>")

print("</body>")
print("</html>")
