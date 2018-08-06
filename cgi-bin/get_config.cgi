#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cgi
import os
import sys
import mysql.connector
import configparser
sys.path.append("scripts/")
from scripts.get_deviceinfo import *

form = cgi.FieldStorage()
config = configparser.ConfigParser()
config.read("scripts/config.txt")
db_user = config["database"]["username"].replace('"', '')
db_pass = config["database"]["password"].replace('"', '')
db_name = config["database"]["database"].replace('"', '')
db_host = config["database"]["host"].replace('"', '')
username = config["device"]["username"].replace('"', '')
password = config["device"]["password"].replace('"', '')
domain = config["env"]["domain"].replace('"', '')

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

hostname = "none"
if "hostname" in form:
    hostname = form["hostname"].value
    conn = mysql.connector.connect(user=db_user, password=db_pass, database=db_name, host=db_host)
    cur = conn.cursor()
    cur.execute("select name, type from node_list where name='{0}'".format(hostname))
    data = cur.fetchall()
    name, type = data[0]
    device = session_create(hostname, domain, username, password, ostype_dct[type])
    configuration = device.get_config()
    configuration = configuration.split("\r\n")
    conn.close()
    device.close()

print("Content-type:text/html; charset=UTF-8")
print("")
print("<html>")
print("<head>")
print("<meta charset='UTF-8'>")
print("<title> Device Configuration </title>")
print("</head>")
print("<body>")

print("<h1> Device Configuration of {0} </h1>".format(hostname))
print("<hr>")

try:
    for line in configuration:
        print("<pre>" + line + "</pre>")
except:
    print("<p> Error! </p>")

print("</body>")
print("</html>")
