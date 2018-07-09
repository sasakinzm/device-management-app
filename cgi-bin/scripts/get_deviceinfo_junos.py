#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
from interfaceinfo import interfaceinfo

class session_create_junos(interfaceinfo):
    """
    ostype が junos の時にデバイス情報を取得するクラス
    """

    def __init__(self, host, domain, user, password):
        """
        ログイン～ターミナル長制限解除までを実施
        """
        self.host = host
        self.user = user
        fqdn = host + "." + domain
        self.conn = telnetlib.Telnet(fqdn)
        self.conn.read_until("login: ".encode("utf-8"))
        self.conn.write("{0}\n".format(user).encode("utf-8"))
        self.conn.read_until("Password: ".encode("utf-8"))
        self.conn.write("{0}\n".format(password).encode("utf-8"))
        self.conn.read_until("\n{0}@{1}>".format(user, host).encode("utf-8"))
        self.conn.write("set cli screen-length 0 \n".encode("utf-8"))
        self.conn.read_until("\n{0}@{1}>".format(user, host).encode("utf-8"))

    def run(self, command):
        """
        任意のコマンドを実行する関数
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("\n{0}@{1}>".format(self.user, self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        return stdout

    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。返り値はそれらのディクショナリ。
        """
        ### モデル名を取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if "Model: " in row: model_row = row   # モデル名を含む行のみを抽出
        self.model = model_row.split(":")[1].replace("\r", "")       # モデル名のみを抽出

        ### OSバージョンを取得
        for row in stdout_list:
            if "Junos: " in row: version_row = row   # バージョンを含む行のみを抽出
        self.version = version_row.split(":")[1].replace("\r", "")       # バージョン番号のみを抽出

        ### 筐体シリアルナンバーを取得
        stdout = self.run("show chassis hardware")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if row.startswith("Chassis"): serial_row = row   # シリアルを含む行のみを抽出
        self.serial = serial_row.split()[1].replace("\r", "")       # シリアル番号のみを抽出
        

    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        stdout = self.run('show interfaces | match "Physical interface" | match "et-|xe-|ge-|ae"')   ### 内部インターフェースを除外する
        stdout_list = stdout.split("\n")[1:-3]
        stdout_list = [i.replace("Physical interface:", "").replace("Physical link is", "").replace("\r", "").replace("Administratively", "") for i in stdout_list]
        stdout_list = [i.split(",") for i in stdout_list]  ### [インターフェース名、Adminステート、リンク状態]を格納した2重配列に整形
        interfaces = []

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく

        for i in stdout_list:
            interface_dict = {}
            interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"] = i[0], i[1], i[2]

            output1 = self.run("show interfaces{0}".format(i[0]))
            output1_list = output1.split("\n")
            output1_list = output1_list[1:-3]

            ### 各インターフェースに対して、帯域幅とディスクリプションとLAGグループを取得する
            for j in output1_list:
                if "Speed: " in j:
                    temp = j.split(",")
                    for k in temp:
                        if "Speed:" in k: speed = k.strip().replace("Speed: ", "")
                    interface_dict["speed"] = speed
                if "Description: " in j:
                    description = j.replace("Description: ", "")
                    interface_dict["description"] = description
                if "AE bundle: " in j:
                    lag_group = j.split(",")[1].replace("AE bundle: ", "").strip()
                    interface_dict["lag_group"] = lag_group

            ### ae インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "ae" in i[0]:
                output2 = self.run("show interfaces terse | match {0}".format(i[0]))
                output2_list = output2.split("\n")
                output2_list = output2_list[1:-3]
                lag_member = []
                for j in output2_list:
                    if "-->" in j:
                        lag_member.append(j.split()[0])
                interface_dict["lag_member"] = lag_member

            ### これまでの処理で、必要な key に値が入らなかった部分を "-" で埋める
            keys = ["name", "admin_state", "link_state", "speed", "description", "lag_group", "lag_member"]
            key_diff = list(set(keys) - set(interface_dict.keys()))
            for key in key_diff:
                interface_dict[key] = "-" 

            interfaces.append(interfaceinfo(interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"], interface_dict["speed"], interface_dict["description"], interface_dict["lag_group"], interface_dict["lag_member"]))

        return interfaces


    def close(self):
        self.conn.close()

