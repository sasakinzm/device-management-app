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
sql = "select * from node_list"
cur.execute(sql)
rows = cur.fetchall()


####################################
# HTML 作成

print("Content-type: text/html; charset=UTF-8")
print('''
<html>
<head>
<title>test</title>
</head>
<body>

<table border=1 width='100%'>
<tr>
<td>ホスト名</td>
<td>モデル</td>
<td>ベンダー</td>
<td>筐体シリアルNo</td>
<td>OSバージョン</td>
<td>管理用IPアドレス</td>
<td>IF情報</td>
<td>HW情報</td>
</tr>
''')

for row in rows:
    hostname, model, vender, serial, version, mgmt_ip = row
    print('''
    <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td><a href='../cgi-bin/interface_list.cgi'>IF情報へ</a></td>
    <td><a href='hardware_%s.html'>HW情報へ</a></td>
    </tr>
    ''' %(hostname, model, vender, serial, version, mgmt_ip, hostname))

print('''
</table>

</body>
</html>
''')

cur.close()
conn.close()
