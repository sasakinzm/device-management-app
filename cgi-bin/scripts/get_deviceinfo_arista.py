#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
import re
from subsysteminfo import *

class session_create_arista(interfaceinfo):
    """
    ostype が arista の時にデバイス情報を取得するクラス
    """

    def __init__(self, host, domain, user, password):
        """
        ログイン～ターミナル長制限解除までを実施
        """
        self.host = host
        self.user = user
        fqdn = host + "." + domain
        self.conn = telnetlib.Telnet(fqdn)
        self.conn.read_until("Username: ".encode("utf-8"))
        self.conn.write("{0}\n".format(user).encode("utf-8"))
        self.conn.read_until("Password: ".encode("utf-8"))
        self.conn.write("{0}\n".format(password).encode("utf-8"))
        self.conn.read_until("\n{0}>".format(host).encode("utf-8"))
        self.conn.write("terminal length 0 \n".encode("utf-8"))
        self.conn.read_until("\n{0}>".format(host).encode("utf-8"))

    def run(self, command):
        """
        任意のコマンドを実行する関数
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("\n{0}>".format(self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        stdout = stdout.replace("{0}\r\n".format(command), "").replace("\r\n{0}>".format(self.host), "")
        return stdout


    def get_config(self):
        config = self.run("show running-config")
        return config


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。
        """
        ### モデル名を取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if row.startswith("Arista ") : model_row = row   # モデル名を含む行のみを抽出
        self.model = model_row.split()[1].replace("\r", "").strip()      # モデル名のみを抽出

        ### OSバージョンを取得
        for row in stdout_list:
            if "Software image version:" in row: version_row = row   # バージョンを含む行のみを抽出
        self.os_version = version_row.split(":")[1].replace("\r", "") .strip()      # バージョン番号のみを抽出

        ### 筐体シリアルナンバーを取得
        for row in stdout_list:
            if row.startswith("Serial number:") : serial_row = row   # シリアルを含む行のみを抽出
        self.serial = serial_row.split(":")[1].replace("\r", "").strip()       # シリアル番号のみを抽出
        

    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """

        ### 各インターフェースのメディアタイプを格納したディクショナリを作る(後で使う)
        media_dict = {}
        mediainfo = self.run("show interfaces status")
        mediainfo_list = mediainfo.split("\r\n")
        for line in mediainfo_list:
            try:
                interface_name = line.split()[0].replace("Et", "Ethernet")
                media = line.split()[-1]
                media_dict[interface_name] = media
            except:
                pass

        ifinfo = self.run("show interface")
        ifinfo_list = re.split('\r\n(?=\S)', ifinfo)        
        interfaces = []

        ### 各インターフェースに対して、Adminステート、リンク状態、帯域幅、ディスクリプション、LAGグループ、LAGメンバーを取得する
        for interface in ifinfo_list:

            if interface.split()[0].startswith("Vlan") or interface.split()[0].startswith("loopback"):
                continue

            interface_dict = {}
            interface_dict["name"] = interface.split()[0]
            for row in interface.split("\n"):
                if "line protocol is" in row:
                    temp_list = row.split(",")
                    interface_dict["admin_state"] = temp_list[0].split()[2]
                    if interface_dict["admin_state"] == "administratively":
                        interface_dict["admin_state"] = "down"
                    interface_dict["link_state"] = temp_list[1].split()[3]
                    if interface_dict["link_state"] == "notpresent":
                        interface_dict["link_state"] = "down"
                if "BW" in row:
                    for i in row.split(","):
                        if "BW" in i:
                            interface_dict["speed"] = i.replace("BW ", "").strip()
                if "Description: " in row:
                    interface_dict["description"] = row.replace("Description: ", "").replace("\r", "").strip()
                if "Member of Port-Channel" in row:
                    for i in row.split():
                        if "Port-Channel" in i:
                            interface_dict["lag_group"] = i.strip()
            if "Port-Channel" in interface_dict["name"]:
                lag_member = []
                for row in interface.split("\n"):
                    if " ... " in row:
                        for i in row.split():
                            if "Ethernet" in i: member = i.strip()
                        lag_member.append(member)
                interface_dict["lag_member"] = lag_member

            ### メディアタイプを決める
            try:
                interface_dict["media_type"] = media_dict[interface_dict["name"]]
            except:
                pass

            ### これまでの処理で、必要な key に値が入らなかった部分を "-" で埋める
            keys = ["name", "admin_state", "link_state", "speed", "description", "lag_group", "lag_member", "media_type"]
            key_diff = list(set(keys) - set(interface_dict.keys()))
            for key in key_diff:
                interface_dict[key] = "-" 

            ### 意図しない値を修正・除去する
            # admin_state と link_state が共に値がないものは捨てる
            if interface_dict["admin_state"] == "-" and interface_dict["link_state"] == "-":
                continue
            #メディアタイプが変な値だったら "-" に変更する
            if interface_dict["media_type"] in ["Present", "Connector", "Transceiver", "unknown media type"]:
                interface_dict["media_type"] = "-"

            interfaces.append(interfaceinfo(interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"], interface_dict["speed"], interface_dict["description"], interface_dict["lag_group"], interface_dict["lag_member"], interface_dict["media_type"]))

        return interfaces


    def close(self):
        self.conn.close()

