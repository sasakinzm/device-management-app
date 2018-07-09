#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
from interfaceinfo import interfaceinfo

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
        return stdout

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
        self.model = model_row.split()[1].replace("\r", "")      # モデル名のみを抽出

        ### OSバージョンを取得
        for row in stdout_list:
            if "Software image version:" in row: version_row = row   # バージョンを含む行のみを抽出
        self.version = version_row.split(":")[1].replace("\r", "")       # バージョン番号のみを抽出

        ### 筐体シリアルナンバーを取得
        for row in stdout_list:
            if row.startswith("Serial number:") : serial_row = row   # シリアルを含む行のみを抽出
        self.serial = serial_row.split(":")[1].replace("\r", "")       # シリアル番号のみを抽出
        

    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        stdout = self.run("show interface | include line protocol")
        stdout_list = stdout.split("\n")[1:-2]
        stdout_list = [i.replace("is", "").replace("line protocol", "").replace("administratively ", "").replace("admintratively", "") for i in stdout_list]
        stdout_list = [i.split() for i in stdout_list]
        interfaces = []

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく

        for i in stdout_list:
            interface_dict = {}
            interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"] = i[0], i[1], i[2]

            output1 = self.run("show interfaces {0}".format(interface_dict["name"]))
            output1_list = output1.split("\n")

            ### 各インターフェースに対して、帯域幅とディスクリプションとLAGグループを取得する
            for j in output1_list:
                if "BW " in j:
                    for k in j.split(","):
                        if "BW" in k: speed = k.strip().replace("BW ", "")
                    interface_dict["speed"] = speed
                if "Description: " in j:
                    description = j.replace("Description: ", "")
                    interface_dict["description"] = description
                if "Member of Port-Channel" in j:
                    for k in j.split():
                        if "Port-Channel" in k: lag_group = k.strip()
                    interface_dict["lag_group"] = lag_group

            ### Po インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "Port-Channel" in i[0]:
                output2 = self.run("show interfaces {0}".format(i[0]))
                output2_list = output2.split("\n")
                lag_member = []
                for j in output2_list:
                    if " ... " in j:
                        for k in j.split():
                            if "Ethernet" in k: member = k.strip()
                        lag_member.append(member)
                interface_dict["lag_member"] = lag_member

            ### これまでの処理で、必要な key に値が入らなかった部分を "-" で埋める
            keys = ["name", "admin_state", "link_state", "speed", "description", "lag_group", "lag_member"]
            key_diff = list(set(keys) - set(interface_dict.keys()))
            for key in key_diff:
                interface_dict[key] = "-" 
            print(interface_dict)

            interfaces.append(interfaceinfo(interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"], interface_dict["speed"], interface_dict["description"], interface_dict["lag_group"], interface_dict["lag_member"]))

        return interfaces


    def close(self):
        self.conn.close()

