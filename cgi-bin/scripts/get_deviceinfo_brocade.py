#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
from subsysteminfo import *

class session_create_brocade(interfaceinfo):
    """
    ostype が brocade の時にデバイス情報を取得するクラス
    """

    def __init__(self, host, domain, user, password):
        """
        Telnetログイン～ターミナル長制限解除までを実施
        host: ログイン先ホスト名のホスト部
        domain: ログイン先ホストのドメイン
        user: ログインするユーザ名
        password: ログインユーザのパスワード
        """
        self.host = host
        self.user = user
        fqdn = host + "." + domain
        self.conn = telnetlib.Telnet(fqdn)
        self.conn.read_until("login:".encode("utf-8"))
        self.conn.write("{0}\n".format(user).encode("utf-8"))
        self.conn.read_until("Password:".encode("utf-8"))
        self.conn.write("{0}\n".format(password).encode("utf-8"))
        self.conn.read_until("\n{0}#".format(host).encode("utf-8"))
        self.conn.write("terminal length 0 \n".encode("utf-8"))
        self.conn.read_until("\n{0}#".format(host).encode("utf-8"))


    def run(self, command):
        """
        任意のコマンドを実行する関数
        command: 実行するCLIコマンド
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("\n{0}#".format(self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        stdout = stdout.replace(" {0}\r\n".format(command), "").replace("\r\n{0}#".format(self.host), "")
        return stdout


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。
        """
        ### モデル名を取得
        stdout = self.run("show inventory")
        stdout_list = stdout.split("\r\n\r\n")
        for row in stdout_list:
            if "NAME: Chassis" in row : model_block = row   # モデル名を含むブロックを抽出
        model_block = model_block.split("\r\n")
        model_list = []
        for i in model_block:
            k = i.split("\t")
            for j in range(len(k)):
                model_list.append(k[j])
        for i in model_list:
            if "SID:" in i : model = i.split(":")[1]
        self.model = model.replace("\r", "").strip()

        ### 筐体シリアルナンバーを取得
        for i in model_list:
            if "SN:" in i : serial = i.split(":")[1]
        self.serial = serial.replace("\r", "").strip()

        ### OSバージョンを取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if "Network Operating System Version:" in row: version_row = row   # バージョンを含む行のみを抽出
        self.os_version =  version_row.split(":")[1].replace("\r", "").strip()    # バージョン番号のみを抽出


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """

        ifinfo = self.run("show interface")
        ifinfo_list = ifinfo.split("\r\n\r\n")
        ifname_list = [i.split()[0] + " " +  i.split()[1] for i in ifinfo_list]
        interfaces = []

        ### 物理インターフェースに対するPort-channel グループを決定するために、
        ### 物理インターフェースを key, Port-channel グループをvalue とするディクショナリ(lag_group_dict)を作る(後で使う)
        lag_group_dict = {}
        output = self.run("show port-channel")
        output_list = output.split("\r\n\r\n")
        output_list = [i.split("\r\n") for i in output_list]
        for i in output_list:
            for j in i[3:]:
                lag_group_dict[j.replace("*", "").strip()] = i[0].split(":")[1].strip()

        ### 各インターフェースのメディアタイプを格納したディクショナリを作る(後で使う)
        media_dict = {}
        mediainfo = self.run("show interface status")
        mediainfo_list = mediainfo.split("\r\n")
        for line in mediainfo_list:
            try:
                interface_num = line.split()[1]
                media = line.split()[5]
                media_dict[interface_num] = media
            except:
                pass

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        for interface in ifinfo_list:
            if interface.split()[0].startswith("Vlan") or interface.split()[0].startswith("loopback"):
                continue

            interface_dict = {}
            interface_dict["name"] = interface.split()[0] + " " +  interface.split()[1]
            for row in interface.split("\n"):
                if "line protocol" in row:
                    if "admin down" in row:
                        interface_dict["admin_state"] = "down"
                    else: interface_dict["admin_state"] = "up"
                    if "line protocol is up" in row:
                        interface_dict["link_state"] = "up"
                    elif "line protocol is down" in row:
                        interface_dict["link_state"] = "down"
                if "LineSpeed Actual" in row:
                    interface_dict["speed"] = row.split(":")[1].replace("\r", "").strip()
                if "Description:" in row:
                    interface_dict["description"] = row.split(":")[1].replace("\r", "").strip()

            ### lag_group_dict から物理インターフェースが所属するPort-channelポートを取得する
            short_ifname = interface_dict["name"].replace("Port-channel", "Po").replace("FortyGigabitEthernet","Fo").replace("TenGigabitEthernet", "Te")
            if short_ifname in lag_group_dict.keys():
                interface_dict["lag_group"] = lag_group_dict[short_ifname]

            ### Port-channel インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "Port-channel" in interface_dict["name"]:
                lag_member = []
                for j in lag_group_dict:
                    if lag_group_dict[j] == short_ifname:
                        lag_member.append(j)
                interface_dict["lag_member"] = lag_member

            ### メディアタイプを決める
            try:
                interface_dict["media_type"] = media_dict[interface.split()[1]]
            except:
                pass

            ### これまでの処理で、必要な key に値が入らなかった部分を "-" で埋める
            keys = ["name", "admin_state", "link_state", "speed", "description", "lag_group", "lag_member", "media_type"]
            key_diff = list(set(keys) - set(interface_dict.keys()))
            for key in key_diff:
                interface_dict[key] = "-" 

            interfaces.append(interfaceinfo(interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"], interface_dict["speed"], interface_dict["description"], interface_dict["lag_group"], interface_dict["lag_member"], interface_dict["media_type"]))

        return interfaces


    def close(self):
        self.conn.close()

