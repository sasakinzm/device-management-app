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
cur.execute("select * from interface_list")
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
print("<td>aaa</td>")
print("<td>bbb</td>")
print("<td>ccc</td>")
print("<td>ddd</td>")
print("<td>eee</td>")
print("</tr>")
print("<tr>")
print("<td>aaaaa</td>")
print("<td>bbbbb</td>")
print("<td>ccccc</td>")
print("<td>ddddd</td>")
print("<td>eeeee</td>")
print("</tr>")
print("</table>")

print("<br>")

print("<table border=1 width='100%'>")
print("<tr>")
print("<td>ホスト名</td>")
print("<td>物理IF</td>")
print("<td>帯域幅</td>")
print("<td>リンク状態</td>")
print("<td>Description</td>")
print("</tr>")
for row in rows:
    hostname, physical_interface, bandwidth, link_state, description = row
    print("<tr>")
    print("<td>%s</td>" %(hostname))
    print("<td>%s</td>" %(physical_interface))
    print("<td>%s</td>" %(bandwidth))
    print("<td>%s</td>" %(link_state))
    print("<td>%s</td>" %(description))
    print("</tr>")
print("</table>")

print("</body>")
print("</html>")

cur.close()
conn.close()
