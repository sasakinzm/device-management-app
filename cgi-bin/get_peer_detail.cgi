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


### DB接続、コンフィグ取得
hostname = "none"
peer = "none"

if "hostname" in form and "peer" in form:
    hostname = form["hostname"].value
    peer = form["peer"].value
    conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
    cur = conn.cursor()
    cur.execute("select name, ostype from node_master_list where name='{0}'".format(hostname))
    data = cur.fetchall()
    name, ostype = data[0]
    device = session_create(hostname, domain, username, password, ostype)
    peer_detail = device.get_peer_detail(peer)
    peer_detail = peer_detail.split("\r\n")
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

print("<h1> Peer Detail of {0} {1} </h1>".format(hostname, peer))
print("<hr>")

try:
    print("<pre>")
    for line in peer_detail:
        print(line.replace("<", "&lt;").replace(">", "&gt;"))
    print("</pre>")
except:
    print("<p> Error! </p>")

print("</body>")
print("</html>")
