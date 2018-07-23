#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
import re
from subsysteminfo import *

class session_create_iosxr(interfaceinfo):
    """
    ostype が iosxr の時にデバイス情報を取得するクラス
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
        self.conn.read_until("RP/0/RSP0/CPU0:{0}#".format(host).encode("utf-8"))
        self.conn.write("terminal length 0 \n".encode("utf-8"))
        self.conn.read_until("RP/0/RSP0/CPU0:{0}#".format(host).encode("utf-8"))


    def run(self, command):
        """
        任意のコマンドを実行する関数
        command: 実行するCLIコマンド
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("RP/0/RSP0/CPU0:{0}#".format(self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        stdout = stdout.replace("{0}\r\n".format(command), "").replace("\r\nRP/0/RSP0/CPU0:{0}#".format(self.host), "")
        return stdout


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。
        """
        ### モデル名を取得
        stdout = self.run("show inventory rack")
        line_num = 3
        stdout = stdout.split("\n")[line_num]     # ほしい情報がコマンドの3行目に "0, モデル名  シリアル番号" と出力される前提
        stdout_list = stdout.split()
        model_index = 1
        self.model = stdout_list[model_index].replace("\r", "").strip()

        ### 筐体シリアルナンバーを取得
        serial_index = 2
        self.serial = stdout_list[serial_index].replace("\r", "").strip()

        ### OSバージョンを取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if "Cisco IOS XR Software," in row: version_row = row   # バージョンを含む行のみを抽出
        for row in version_row.split(","):
            if "Version " in row: version = row       # バージョン番号のみを抽出
        self.os_version = version.replace("\r", "").strip()


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        ifinfo = self.run("show interface")
        ifinfo = ifinfo.replace(re.search(".*\n", ifinfo).group(0), "")
        ifinfo_list = re.split('\r\n\r\n(?=\S)', ifinfo)

        ### 物理インターフェースに対するBundle-Ether グループを決定するために、
        ### 物理インターフェースを key, Bundle-Ether グループをvalue とするディクショナリ(lag_group_dict)を作る(後で使う)
        lag_group_dict = {}
        for interface in ifinfo_list:
            if "Bundle-Ether" in interface.split()[0]:
                temp_list = interface.split("\n")
                for row in temp_list:
                    if "No. of members in this bundle:" in row:
                        member_num = int(row.replace("No. of members in this bundle: ", ""))
                        index = temp_list.index(row)
                        lag_member = [ k.split()[0] for k in temp_list[index + 1:index + member_num + 1]]
                for j in lag_member:
                    lag_group_dict[j] = interface.split()[0]

        ### 各インターフェースのメディアタイプを格納したディクショナリを作る(後で使う)
        media_dict = {}
        mediainfo = self.run("show inventory all")
        mediainfo_list = mediainfo.split("\r\n\r\n")
        for line in mediainfo_list:
            interface_name = line.split(",")[0].replace('NAME: "module mau', "").replace('"', "").replace("CPU", "").strip()
            media = line.split("PID:")[1].split(",")[0].strip()
            media_dict[interface_name] = media

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        interfaces = []
        for interface in ifinfo_list:
            if interface.split()[0].startswith("Vlan") or interface.split()[0].startswith("Loopback"):
                continue

            interface_dict = {}
            interface_dict["name"] = interface.split()[0]

            ### 各インターフェースに対して、Adminステートとリンク状態と帯域幅とディスクリプションを取得する
            for row in interface.split("\n"):
                if "line protocol " in row:
                    if "administratively down" in row:
                        interface_dict["admin_state"] = "down"
                    else:
                        interface_dict["admin_state"] = "up"
                    interface_dict["link_state"] = row.split(",")[1].replace("line protocol is ", "").replace("administratively", "").strip()
                if "BW " in row:
                    for i in row.split(","):
                        if "BW" in i:
                            interface_dict["speed"] = i.replace("BW ", "").strip()
                if "Description:" in row:
                    interface_dict["description"] = row.replace("Description:", "").replace("\r", "")

            ### lag_group_dict から物理インターフェースが所属するBundle-Etherポートを取得する
            if interface_dict["name"] in lag_group_dict.keys():
                interface_dict["lag_group"] = lag_group_dict[interface_dict["name"]]

            ### Bundle-Ether インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "Bundle-Ether" in interface_dict["name"]:
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

            interfaces.append(interfaceinfo(interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"], interface_dict["speed"], interface_dict["description"], interface_dict["lag_group"], interface_dict["lag_member"], interface_dict["media_type"]))

        return interfaces


    def get_bgppeer(self):
        bgppeers = []
        peerinfo = self.run("show bgp ipv4 unicast neighbors")
        peerinfo_list = peerinfo.split("\r\n\r\nBGP neighbor is")
        peerinfo_list = [ "BGP neighbor is" + i for i in peerinfo_list]

        for peer in peerinfo_list:
            bgppeer_dict = {}
            for line in peer.split("\n"):
                if "BGP neighbor is " in line:
                    bgppeer_dict["addr"] = line.replace("BGP neighbor is", "").strip()
                if "Remote AS" in line:
                    bgppeer_dict["asn"] = line.split(",")[0].replace("Remote AS", "").replace("\r", "").strip()
                    bgppeer_dict["peer_type"] = line.split(",")[2].replace("link", "").replace("\r", "").strip()
                if "BGP state =" in line:
                    bgppeer_dict["state"] = line.split(",")[0].replace("BGP state =", "").replace("\r", "").strip()
                if "Description:" in line:
                    bgppeer_dict["peer_description"] = line.split(":")[1].replace("Description:", "").replace("\r", "").strip()
                if "accepted prefixes," in line:
                    bgppeer_dict["rcvroutes"] = line.split()[0]

            try:
                advroutes = self.run("show bgp ipv4 unicast neighbor {0} advertised-count".format(bgppeer_dict["addr"]))
                for i in advroutes.split("\n"):
                    if "No of prefixes Advertised:" in i:
                        bgppeer_dict["advroutes"] = i.replace("No of prefixes Advertised:", "").replace("\r", "").strip()
            except:
                pass

            ### これまでの処理で、必要な key に値が入らなかった部分を "-" で埋める
            keys = ["addr", "asn", "peer_type", "state", "rcvroutes", "advroutes", "peer_description"]
            key_diff = list(set(keys) - set(bgppeer_dict.keys()))
            for key in key_diff:
                bgppeer_dict[key] = "-"

            bgppeers.append(bgpinfo(bgppeer_dict["addr"], bgppeer_dict["peer_type"], bgppeer_dict["state"], bgppeer_dict["asn"], bgppeer_dict["rcvroutes"], bgppeer_dict["advroutes"], bgppeer_dict["peer_description"]))

        return bgppeers


    def close(self):
        self.conn.close()

