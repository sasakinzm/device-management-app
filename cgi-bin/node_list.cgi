#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import io
import mysql.connector
import configparser
import cgi
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
# 変数読み込み

form = cgi.FieldStorage()
keyword_host = form["keyword_host"]
keyword_location = form["keyword_location"]
keyword_model = form["keyword_model"]
keyword_type = form["keyword_type"]
keyword_os_version = form["keyword_os_version"]
keyword_mgmt_ip = form["keyword_mgmt_ip"]
match_condition = "exact"


####################################
# DB 接続

conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
cur = conn.cursor()
sql = '''
       SELECT
           *
       FROM
           node_list
       WHERE
           name LIKE '%{0}%'
       AND location LIKE '%{1}%'
       AND model LIKE '%{2}%'
       AND type LIKE '%{3}%'
       AND version LIKE '%{4}%'
       AND mgmt_ip LIKE '%{5}%'
       ORDER BY name
      '''.format(keyword_host, keyword_location, keyword_model, keyword_type, keyword_os_version, keyword_mgmt_ip)
cur.execute(sql)
rows = cur.fetchall()


####################################
# HTML 作成

print("Content-type: text/html; charset=UTF-8")
print('''
<html>
<head>
<title> Device List </title>
</head>
<body>

<table border=1 width='100%' style='font-size: 10pt; line-height: 110%;'>
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
          <td> {0} </td>
          <td> {1} </td>
          <td> {2} </td>
          <td> {3} </td>
          <td> {4} </td>
          <td> {5} </td>
          <td> <a href='interface_list.html?keyword_hostname={0}&{6}=exact' targt='contents'>IF一覧</a>
          <td> <a href='bgppeer_list.html?keyword_hostname={0}&{6}=exact' targt='contents'>BGPピア一覧</a>
          </tr>
          '''.format(hostname, model, vender, serial, version, mgmt_ip, match_condition))

print('''
</table>

</body>
</html>
''')

cur.close()
conn.close()
