#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
import re
from subsysteminfo import *

class session_create_ios2600(interfaceinfo, bgpinfo):
    """
    ostype が ios2600 の時にデバイス情報を取得するクラス
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
        command: 実行するCLIコマンド
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("\n{0}>".format(self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        stdout = stdout.replace("{0}\r\n".format(command), "").replace("\r\n{0}>".format(self.host), "")
        return stdout


    def get_config(self):
        config = self.run("show running-config")
        return config


    def get_hardware(self):
        hardware = self.run("show hardware")
        return hardware


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。
        """
        ### モデル名を取得
        self.model = "C2600"

        ### 筐体シリアルナンバーを取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\r\n")
        for row in stdout_list:
            if "Processor board ID" in row:
                self.serial = row.replace("Processor board ID", "").strip()

        ### OSバージョンを取得
            if "IOS (tm) C2600 Software" in row:   # バージョンを含む行のみを抽出
                for sec in row.split(","):
                    if "Version " in sec:
                        self.os_version = sec.strip()       # バージョン番号のみを抽出


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        ifinfo = self.run("show interface")
        ifinfo_list = re.split('\r\n(?=\S)', ifinfo)

        ### 物理インターフェースに対するPort-channel グループを決定するために、
        ### 物理インターフェースを key, Port-channel グループをvalue とするディクショナリ(lag_group_dict)を作る(後で使う)
        lag_group_dict = {}
        for interface in ifinfo_list:
            ifname = interface.split()[0]
            if "Port-channel" in ifname:
                temp_list = interface.split("\n")
                for j in temp_list:
                    if "Members in this channel:" in j:
                        lag_member = [k.strip() for k in j.replace("Members in this channel:", "").split()]
                for j in lag_member:
                    lag_group_dict[j] = ifname

        ### 各インターフェースのメディアタイプを格納したディクショナリを作る(後で使う)
        media_dict = {}
        mediainfo = self.run("show interface status")
        mediainfo_list = mediainfo.split("\r\n")
        for line in mediainfo_list:
            try:
                interface_name = line.split()[0].replace("Gi", "GigabitEthernet").replace("Te", "TenGigabitEthernet")
                media = line.split()[-1]
                media_dict[interface_name] = media
            except:
                pass

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        interfaces = []
        for interface in ifinfo_list:
            if interface.split()[0].startswith("Vlan") or interface.split()[0].startswith("Loopback"):
                continue

            interface_dict = {}
            interface_dict["name"] = interface.split()[0]
            for row in interface.split("\n"):
                if "line protocol " in row:
                    if "administratively down" in row:
                        interface_dict["admin_state"] = "down"
                    else:
                        interface_dict["admin_state"] = "up"
                    if "line protocol is up" in row: 
                        interface_dict["link_state"] = "up"
                    elif "line protocol is down" in row:
                        interface_dict["link_state"] = "down"
                if "BW " in row:
                    for i in row.split(","):
                        if "BW" in i:
                            interface_dict["speed"] = i.replace("BW ", "").strip()
                if "Description:" in row:
                    interface_dict["description"] = row.replace("Description:", "").replace("\r", "")
                if "media type is" in row:
                    for i in row.split(","):
                        if "media type is" in i:
                            interface_dict["media_type"] = i.replace("media type is", "").replace("\r", "").strip()

            ### lag_group_dict から物理インターフェースが所属するPort-channelポートを取得する
            short_ifname = interface_dict["name"].replace("Port-channel", "Po").replace("FortyGigabitEthernet","Fo").replace("TenGigabitEthernet", "Te").replace("GigabitEthernet", "Gi")

            if short_ifname in lag_group_dict.keys():
                interface_dict["lag_group"] = lag_group_dict[short_ifname]

            ### Port-channel インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "Port-channel" in interface_dict["name"]:
                lag_member = []
                for j in lag_group_dict:
                    if lag_group_dict[j] == interface_dict["name"]:
                        lag_member.append(j)
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


    def get_interface_detail(self, interface):
        interface_detail = self.run("show interface {0}".format(interface))
        return interface_detail


    def get_bgppeer(self):
        bgppeers = []
        peerinfo = self.run("show bgp ipv4 unicast neighbors")
        peerinfo_list = peerinfo.split("\r\n\r\nBGP neighbor is")
        peerinfo_list = [ "BGP neighbor is" + i for i in peerinfo_list]

        for peer in peerinfo_list:
            bgppeer_dict = {}
            for line in peer.split("\n"):
                if "BGP neighbor is " in line:
                    bgppeer_dict["addr"] = line.split(",")[0].replace("BGP neighbor is ", "").replace("\r", "").strip()
                    bgppeer_dict["asn"] = line.split(",")[1].replace("remote AS", "").replace("\r", "").strip()
                    bgppeer_dict["peer_type"] = line.split(",")[2].replace("link", "").replace("\r", "").strip()
                if "BGP state =" in line:
                    bgppeer_dict["state"] = line.split(",")[0].replace("BGP state =", "").replace("\r", "").strip()
                if "Description:" in line:
                    bgppeer_dict["peer_description"] = line.split(":")[1].replace("Description:", "").replace("\r", "").strip()
                if "Prefixes Current:" in line:
                    bgppeer_dict["rcvroutes"] = line.split()[3]
                    bgppeer_dict["advroutes"] = line.split()[2]

            ### これまでの処理で、必要な key に値が入らなかった部分を "-" で埋める
            keys = ["addr", "asn", "peer_type", "state", "rcvroutes", "advroutes", "peer_description"]
            key_diff = list(set(keys) - set(bgppeer_dict.keys()))
            for key in key_diff:
                bgppeer_dict[key] = "-"

            ### 意図しない値を修正・除去する
            # addr, asn, peer_type のどれかに値がないものは捨てる
            if bgppeer_dict["addr"] == "-" or bgppeer_dict["asn"] == "-" or bgppeer_dict["peer_type"] == "-":
                continue

            bgppeers.append(bgpinfo(bgppeer_dict["addr"], bgppeer_dict["peer_type"], bgppeer_dict["state"], bgppeer_dict["asn"], bgppeer_dict["rcvroutes"], bgppeer_dict["advroutes"], bgppeer_dict["peer_description"]))

        return bgppeers


    def get_peer_detail(self, peer):
        peer_detail = self.run("show bgp ipv4 unicast neighbors {0}".format(peer))
        return peer_detail


    def close(self):
        self.conn.close()

