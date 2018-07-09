#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os 
import sys
import io
import mysql.connector
import configparser
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

#############################################
### コンフィグ読み込み

path = os.path.dirname(os.path.abspath(__file__))
config = configparser.ConfigParser()
config.read( path + "/scripts/config.txt")
db_user = config["database"]["username"]
db_pass = config["database"]["password"]
db_name = config["database"]["database"]
db_host = config["database"]["host"]


####################################
# DB 接続

conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
cur = conn.cursor()
sql = "select * from node_master_list"
cur.execute(sql)
rows = cur.fetchall()


####################################
# HTML 作成

print("Content-type: text/html; charset=UTF-8")
print("")
print("<html>")
print("<head>")
print("<title>test</title>")
print("</head>")
print("<body>")

print("<table border=1 width='100%'>")
print("<tr>")
print("<td>ノード名</td>")
print("<td>タイプ</td>")
print("<td>管理用IPアドレス</td>")
print("</tr>")
for row in rows:
    value1, value2, value3 = row
    print("<tr>")
    print("<td>%s</td>" %(value1))
    print("<td>%s</td>" %(value2))
    print("<td>%s</td>" %(value3))
    print("</tr>")
print("</table>")

print("</body>")
print("</html>")

cur.close()
conn.close()
