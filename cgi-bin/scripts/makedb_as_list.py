#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io
import mysql.connector
import configparser
import urllib.request
import json
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


#############################################
### AS一覧テーブル(as_list)にデータ投入

### DB 接続
conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
cur = conn.cursor()


### AS番号、AS名取得
### as_listテーブルの既存データを削除
cur.execute("DELETE FROM as_list")
conn.commit()


### クエリ作成し、as_list テーブルにデータ格納
sql_select = 'SELECT distinct state, asn FROM bgppeer_list'
cur.execute(sql_select)
data = cur.fetchall()

for i in data:
    try:
        state, asn = i
        url = "https://www.peeringdb.com/api/net?asn={0}".format(asn)
        res = urllib.request.urlopen(url)
        content = json.loads(res.read().decode("utf8"))
        as_name = content["data"][0]["name"]
        sql_insert_as_list = '''
                             INSERT INTO
                               as_list
                             (
                               asn
                             , as_name
                             ) VALUES (
                               "{0}", "{1}"
                             )
                             '''.format(asn, as_name)
        cur.execute(sql_insert_as_list)
        conn.commit()

    except:
        pass


### DB 切断
cur.close()
conn.close()

