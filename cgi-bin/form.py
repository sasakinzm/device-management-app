#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import cgi
import mysql.connector
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

form = cgi.FieldStorage()
form_check = 0
node = form.getvalue("name")

####################################
# DB 接続

conn = mysql.connector.connect(user="root", password="password", database="device_management", host="localhost")
cur = conn.cursor()
sql = "select * from node_list where name = '%s'" %(node)
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
