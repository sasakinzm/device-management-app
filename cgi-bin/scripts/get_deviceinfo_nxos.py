#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
from subsysteminfo import *

class session_create_nxos(interfaceinfo):
    """
    ostype が nxos の時にデバイス情報を取得するクラス
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
        self.conn.read_until("{0}# ".format(host).encode("utf-8"))
        self.conn.write("terminal length 0 \n".encode("utf-8"))
        self.conn.read_until("{0}# ".format(host).encode("utf-8"))


    def run(self, command):
        """
        任意のコマンドを実行する関数
        command: 実行するCLIコマンド
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("{0}# ".format(self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        stdout = stdout.replace("{0}\r\r\n".format(command), "").replace("\r\n\r\n\r{0}#".format(self.host), "")
        return stdout


    def get_config(self):
        config = self.run("show running-config")
        return config


    def get_hardware(self):
        hardware = self.run("show inventory")
        return hardware


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。
        """
        ### モデル名を取得
        stdout = self.run("show inventory chassis")
        stdout_list = [section for row in stdout.split("\n") for section in row.split(",")]
        for row in stdout_list:
            if "DESCR:" in row:
                self.model = row.replace("DESCR: ", "").replace("\r", "").replace("\n", "").replace('"', '').strip()

        ### 筐体シリアルナンバーを取得
            if "SN:" in row:
                self.serial = row.replace("SN: ", "").replace("\r", "").replace('"', '').strip()

        ### OSバージョンを取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if "system: " in row:
                self.os_version = row.split(":")[1].replace("\r", "").strip()


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """

        ### 各インターフェースのメディアタイプを格納したディクショナリを作る(後で使う)
        media_dict = {}
        mediainfo = self.run("show interface transceiver")
        mediainfo_list = mediainfo.split("\r\nE")
        mediainfo_list = ["E" + i for i in mediainfo_list]
        for i in mediainfo_list:
            interface_name = i.split()[0]
            for line in i.split("\n"):
                if "type is" in line:
                    media = line.replace("type is ", "").replace("\r", "").strip()
                    media_dict[interface_name] = media

        ifinfo = self.run("show interface")
        ifinfo_list = ifinfo.split("\r\n\r\n")
        interfaces = []

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        for interface in ifinfo_list:
            if interface.split()[0].startswith("Vlan") or interface.split()[0].startswith("loopback"):
                continue

            interface_dict = {}
            interface_dict["name"] = interface.split()[0] 
            interface_dict["link_state"] = interface.split("\n")[0].replace("{0} is ".format(interface_dict["name"]), "").replace("(SFP not inserted)", "").strip()

            ### 各インターフェースに対して、Adminステートと帯域幅とディスクリプションとLAGメンバーとLAGグループを取得する
            for row in interface.split("\n"):
                if "admin state is" in row:
                    interface_dict["admin_state"] = row.split(",")[0].replace("admin state is ", "").strip()
                if "BW" in row:
                    for i in row.split(","):
                        if "BW" in i:
                            interface_dict["speed"] = i.replace("BW", "").strip()
                if "Description:" in row:
                    interface_dict["description"] = row.replace("Description:", "").replace("\r", "").strip()
                if "Belongs to" in row:
                    interface_dict["lag_group"] = row.replace("Belongs to", "").strip()
                if "Members in this channel:" in row:
                    lag_member = []
                    for i in row.replace("Members in this channel: ", "").split(","):
                        lag_member.append(i.strip())
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
                    bgppeer_dict["addr"] = line.split(",")[0].replace("BGP neighbor is", "").strip()
                    bgppeer_dict["asn"] = line.split(",")[1].replace("remote AS", "").replace("\r", "").strip()
                    bgppeer_dict["peer_type"] = line.split(",")[2].replace("link", "").replace("\r", "").strip()
                if "BGP state =" in line:
                    bgppeer_dict["state"] = line.split(",")[0].replace("BGP state =", "").replace("\r", "").strip()
                if "Description:" in line:
                    bgppeer_dict["peer_description"] = line.replace("Description:", "").replace('"', '').replace("\r", "").strip()

            ### 経路数を確認するのは面倒そうなのでいったん未実装とする
            bgppeer_dict["rcvroutes"] = "No_Impl"
            bgppeer_dict["advroutes"] = "No_Impl"

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

