#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
import re
from subsysteminfo import *

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
        stdout = stdout.replace(" {0} \r\n".format(command), "").replace("\r\n{0}@{1}>".format(self.user, self.host), "")
        return stdout


    def get_config(self):
        config = self.run("show configuration")
        return config


    def get_hardware(self):
        hardware = self.run("show chassis hardware")
        return hardware


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。
        """
        ### モデル名を取得
        stdout = self.run("show version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if "Model: " in row: model_row = row   # モデル名を含む行のみを抽出
        self.model = model_row.split(":")[1].replace("\r", "").strip()       # モデル名のみを抽出

        ### OSバージョンを取得
        self.os_version = re.search("(\[.*\])", stdout).group(0).replace("[", "").replace("]", "")  # 括弧に含まれたバージョン番号を抽出

        ### 筐体シリアルナンバーを取得
        stdout = self.run("show chassis hardware")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if row.startswith("Chassis"): serial_row = row   # シリアルを含む行のみを抽出
        self.serial = serial_row.split()[1].replace("\r", "").strip()       # シリアル番号のみを抽出


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        ifinfo = self.run("show interfaces")
        ifinfo_list = re.split('\r\n\r\n(?=\S)', ifinfo)

        ### 物理インターフェースに対するLAG グループを決定するために、
        ### 物理インターフェースを key, LAG グループをvalue とするディクショナリ(lag_group_dict)を作る(後で使う)
        lag_group_dict = {}
        for interface in ifinfo_list:
            ifname = interface.split(",")[0].replace("Physical interface:", "").strip()
            temp_list = interface.split("\n")
            for row in temp_list:
                if "AE bundle: " in row:
                    lag_group = row.split(",")[1].replace("AE bundle: ", "").strip()
                    lag_group_dict[ifname] = lag_group

        ### 各インターフェースのメディアタイプを格納したディクショナリを作る(後で使う)
        media_dict = {}
        mediainfo = self.run("show chassis hardware")
        fpc_list = mediainfo.split("FPC ")
        for fpc in fpc_list:
            fpc_num = fpc.split()[0]
            pic_list = fpc.split("PIC ")
            for pic in pic_list:
                try:
                    pic_num = pic.split()[0] 
                    port_list = pic.split("\n")
                    for port in port_list:
                        if "Xcvr " in port:
                            port_num = port.split()[1]
                            interface_num = fpc_num + "/" + pic_num + "/" + port_num
                            media = port.split()[-1]
                            media_dict[interface_num] = media
                except:
                    pass

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        interfaces = []
        for interface in ifinfo_list:
            ifname = interface.split(",")[0].replace("Physical interface:", "").strip()
            if ifname.startswith("ge-"):
                pass
            elif ifname.startswith("xe-"):
                pass
            elif ifname.startswith("et-"):
                pass
            elif ifname.startswith("lo"):
                pass
            elif ifname.startswith("ae"):
                pass
            elif ifname.startswith("fxp"):
                pass
            elif ifname.startswith("me"):
                pass
            else:
                continue

            interface_dict = {}
            interface_dict["name"] = ifname
            for row in interface.split("\n"):
                if "Physical interface: {0}".format(interface_dict["name"]) in row:
                    if "Enabled" in row:
                        interface_dict["admin_state"] = "up"
                    elif "Administratively down" in row:
                        interface_dict["admin_state"] = "down"
                    else:
                        pass

                    if " Physical link is Up" in row:
                        interface_dict["link_state"] = "up"
                    elif " Physical link is Down" in row:
                        interface_dict["link_state"] = "down"
                    else:
                        pass

                if "Speed: " in row:
                    temp = row.split(",")
                    for i in temp:
                        if "Speed:" in i:
                            interface_dict["speed"] = i.strip().replace("Speed: ", "")
                if "Description: " in row:
                    interface_dict["description"] = row.replace("Description: ", "").replace("\r", "")
                if "AE bundle: " in row:
                    interface_dict["lag_group"] = row.split(",")[1].replace("AE bundle: ", "").strip()

            ### lag_group_dict から物理インターフェースが所属する ae ポートを取得する
            if interface_dict["name"] in lag_group_dict.keys():
                interface_dict["lag_group"] = lag_group_dict[interface_dict["name"]]

            ### ae インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "ae" in interface_dict["name"]:
                lag_member = []
                for j in lag_group_dict:
                    if lag_group_dict[j].replace(".0", "") == interface_dict["name"]:
                        lag_member.append(j)
                interface_dict["lag_member"] = lag_member

            ### メディアタイプを決める
            try:
                interface_dict["media_type"] = media_dict[interface_dict["name"][3:]]
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


    def get_bgppeer(self):
        bgppeers = []
        peerinfo = self.run("show bgp neighbor")
        peerinfo_list = peerinfo.split("\r\n\r\nPeer:")
        peerinfo_list = [ "Peer:" + i for i in peerinfo_list]

        for peer in peerinfo_list:
            bgppeer_dict = {}
            for line in peer.split("\n"):
                if "Peer ID:" in line:
                    bgppeer_dict["addr"] = line.split("  ")[1].replace("Peer ID: ", "").replace("\r", "").strip()
                if "Peer:" in line:
                    bgppeer_dict["asn"] = line.split()[3].replace("\r", "").strip()
                if "Type:" in line:
                    bgppeer_dict["peer_type"] = line.split("  ")[1].replace("Type: ", "").replace("\r", "").strip()
                    bgppeer_dict["state"] = line.split("  ")[3].replace("State: ", "").replace("\r", "").strip()
                if "Description:" in line:
                    bgppeer_dict["peer_description"] = line.split(":")[1].replace("Description:", "").replace("\r", "").strip()
                if "Received prefixes:" in line:
                    bgppeer_dict["rcvroutes"] = line.split()[2]
                if "Advertised prefixes:" in line:
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
            # IPv6のみの情報は捨てる
            if "NLRI advertised by peer: inet6-unicast" in peer:
                continue

            bgppeers.append(bgpinfo(bgppeer_dict["addr"], bgppeer_dict["peer_type"], bgppeer_dict["state"], bgppeer_dict["asn"], bgppeer_dict["rcvroutes"], bgppeer_dict["advroutes"], bgppeer_dict["peer_description"]))

        return bgppeers


    def close(self):
        self.conn.close()

