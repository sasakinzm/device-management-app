#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
from interfaceinfo import interfaceinfo

class session_create_ios(interfaceinfo):
    """
    ostype が ios の時にデバイス情報を取得するクラス
    """

    def __init__(self, host, domain, user, password):
        """
        Telnetログイン～ターミナル長制限解除までを実施
        ◆引数
        host: ログイン先ホスト名のホスト部
        domain: ログイン先ホストのドメイン
        user: ログインするユーザ名
        password: ログインユーザのパスワード
        """
        self.host = host
        self.user = user
        fqdn = host + "." + domain
        self.conn = telnetlib.Telnet(fqdn)
        self.conn.read_until("Username:".encode("utf-8"))
        self.conn.write("{0}\n".format(user).encode("utf-8"))
        self.conn.read_until("Password:".encode("utf-8"))
        self.conn.write("{0}\n".format(password).encode("utf-8"))
        self.conn.read_until("\n{0}>".format(host).encode("utf-8"))
        self.conn.write("terminal length 0 \n".encode("utf-8"))
        self.conn.read_until("\n{0}>".format(host).encode("utf-8"))


    def run(self, command):
        """
        任意のコマンドを実行する関数
        ◆引数
        command: 実行するCLIコマンド
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
        stdout = self.run("show inventory")
        stdout = stdout.split("\n")[4]  # コマンドの4行目に "PID: XXXX, VID: V02,SN: XXXXXX" が出力される前提
        stdout_list = stdout.replace(",", "").split()
        self.model = stdout_list[1]

        ### 筐体シリアルナンバーを取得
        self.serial = stdout_list[-1]

        ### OSバージョンを取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if "Cisco IOS Software," in row: version_row = row   # バージョンを含む行のみを抽出
        for row in version_row.split(","):
            if "Version " in row: version = row       # バージョン番号のみを抽出
        self.os_version = version.strip()


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        ifname = self.run("show interface | include line protocol")
        ifname_list = ifname.split("\n")[1:-2]
        ifname_list = [i.split()[0] for i in ifname_list]
        interfaces = []

        ### 物理インターフェースに対するPort-channel グループを決定するために、
        ### 物理インターフェースを key, Port-channel グループをvalue とするディクショナリ(lag_group_dict)を作る(後で使う)
        lag_group_dict = {}
        for i in ifname_list:
            if "Port-channel" in i:
                output = self.run("show interface {0}".format(i))
                output_list = output.split("\n")
                for j in output_list:
                    if "Members in this channel:" in j:
                        lag_member = [k.strip() for k in j.replace("Members in this channel:", "").split()]
                for j in lag_member:
                    lag_group_dict[j] = i

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        for i in ifname_list:
            interface_dict = {}
            interface_dict["name"] = i

            output1 = self.run("show interface {0}".format(interface_dict["name"]))
            output1_list = output1.split("\n")

            ### 各インターフェースに対して、Adminステートとリンク状態と帯域幅とディスクリプションを取得する
            for j in output1_list:
                if "line protocol " in j:
                    if "administratively down" in j:
                        admin_state = "down"
                    else: admin_state = "up"
                    interface_dict["admin_state"] = admin_state
                    if "line protocol is up" in j: 
                        link_state = "up"
                    elif "line protocol is down" in j:
                        link_state = "down"
                    interface_dict["link_state"] = link_state
                if "BW " in j:
                    for k in j.split(","):
                        if "BW" in k: speed = k.strip().replace("BW ", "").strip()
                    interface_dict["speed"] = speed
                if "Description:" in j:
                    description = j.replace("Description:", "")
                    interface_dict["description"] = description.replace("\r", "")

            ### lag_group_dict から物理インターフェースが所属するPort-channelポートを取得する
            if i in lag_group_dict.keys():
                interface_dict["lag_group"] = lag_group_dict[i]

            ### Port-channel インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "Port-channel" in interface_dict["name"]:
                lag_member = []
                for j in lag_group_dict:
                    if lag_group_dict[j] == interface_dict["name"]:
                        lag_member.append(j)
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

