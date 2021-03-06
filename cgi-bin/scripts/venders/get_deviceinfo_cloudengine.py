#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
import re
from subsysteminfo import *

class session_create_cloudengine(interfaceinfo, bgpinfo):
    """
    ostype が cloudengine の時にデバイス情報を取得するクラス
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
        self.conn.read_until("\n<{0}>".format(host).encode("utf-8"))
        self.conn.write("screen-length 0 temporary \n".encode("utf-8"))
        self.conn.read_until("\n<{0}>".format(host).encode("utf-8"))


    def run(self, command):
        """
        任意のコマンドを実行する関数
        command: 実行するCLIコマンド
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("\n<{0}>".format(self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        stdout = stdout.replace("{0}\r\n".format(command), "").replace("\r\n<{0}>".format(self.host), "")
        return stdout


    def get_config(self):
        config = self.run("display current-configuration")
        return config


    def get_hardware(self):
        hardware = self.run("display device elabel")
        return hardware


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。
        """
        ### OSバージョンを取得
        stdout = self.run("display version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if "VRP (R) software," in row: version_row = row   # バージョンを含む行のみを抽出
        for row in version_row.split(","):
            if "Version " in row: version = row       # バージョン番号のみを抽出
        self.os_version = version.replace("\r", "").strip()

        ### モデル名を取得
        ### 筐体シリアルナンバーを取得
        stdout = self.run("display device elabel")
        stdout_list = stdout.split("\r\n")
        for row in stdout_list:
            if row.startswith("BoardType="):  # モデル名を含む行のみを抽出
                self.model = row.replace("BoardType=", "").strip()   # モデル名のみを抽出
                break
        for row in stdout_list:
            if row.startswith("BarCode="):  # シリアルナンバーを含む行のみを抽出
                self.serial = row.replace("BarCode=", "").strip()   # シリアルナンバーのみを抽出
                break


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        ifinfo = self.run("display interface")
        ifinfo = ifinfo.replace(re.search(".*\n", ifinfo).group(0), "")
        ifinfo_list = re.split('\r\n\r\n(?=\S)', ifinfo)
        ifname_list = [i.split()[0] for i in ifinfo_list]

        ### 物理インターフェースに対するEth-Trunk グループを決定するために、
        ### 物理インターフェースを key, EthTrunk グループをvalue とするディクショナリ(lag_group_dict)を作る(後で使う)
        lag_group_dict = {}
        for i in ifname_list:
            if "Eth-Trunk" in i:
                output = self.run("display interface {0}".format(i))
                output_list = output.split("\n")
                line_indexs = [i for i,x in enumerate(output_list) if x =='----------------------------------------------------------\r']
                member_row_list = output_list[min(line_indexs)+3:max(line_indexs)]
                lag_member = [i.split()[0] for i in member_row_list]
                for j in lag_member:
                    lag_group_dict[j] = i

        ### 各インターフェースのメディアタイプを格納したディクショナリを作る(後で使う)
        media_dict = {}
        mediainfo = self.run("display interface transceiver")
        mediainfo_list = mediainfo.split("\r\n\r\n")

        for i in mediainfo_list:
            interface_name = i.split()[0]
            for line in i.split("\n"):
                if "Transceiver Type" in line:
                    media = line.split(":")[1].replace("\r", "").strip()
                    media_dict[interface_name] = media

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        interfaces = []
        for interface in ifinfo_list:
            if interface.split()[0].startswith("Vlan") or interface.split()[0].startswith("Loopback"):
                continue

            interface_dict = {}
            interface_dict["name"] = interface.split()[0]
            for row in interface.split("\n"):
                if "{0} current state :".format(interface_dict["name"]) in row:
                        if "Administratively DOWN" in row:
                            interface_dict["admin_state"] = "down"
                        else:
                            interface_dict["admin_state"] = "up"
                if "Line protocol current state :" in row:
                    interface_dict["link_state"] = row.split(":")[1].replace("(spoofing)", "").strip().lower()
                if "Current BW :" in row:
                    for i in row.split(","):
                        if "Current BW :" in i:
                            interface_dict["speed"] = i.replace("Current BW : ", "").strip()
                if "Description: " in row:
                    interface_dict["description"] = row.replace("Description: ", "").replace("\r", "").strip()

            ### lag_group_dict から物理インターフェースが所属するEthTrunkポートを取得する
            if interface_dict["name"] in lag_group_dict.keys():
                interface_dict["lag_group"] = lag_group_dict[interface_dict["name"]]


            ### 物理インターフェースの帯域幅はインターフェース名から直接決める
            if "10GE" in interface_dict["name"]: interface_dict["speed"] = "10GE"
            elif "40GE" in interface_dict["name"]: interface_dict["speed"] = "40GE"
            elif "100GE" in interface_dict["name"]: interface_dict["speed"] = "100GE"

            ### Eth-Trunk インターフェースに対して、所属するメンバーポートを並べた配列を作る
            if "Eth-Trunk" in interface_dict["name"]:
                output2 = self.run("display interface {0}".format(interface_dict["name"]))
                output2_list = output2.split("\n")
                line_indexs = [i for i,x in enumerate(output2_list) if x =='----------------------------------------------------------\r']
                member_row_list = output2_list[min(line_indexs)+3:max(line_indexs)]
                lag_member = [i.split()[0] for i in member_row_list]
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
        interface_detail = self.run("display interface {0}".format(interface))
        return interface_detail


    def get_bgppeer(self):
        bgppeers = []
        peerinfo = self.run("display bgp peer verbose")
        peerinfo_list = peerinfo.split("\r\n BGP Peer is ")

        for peer in peerinfo_list:
            bgppeer_dict = {}
            bgppeer_dict["addr"] = peer.split()[0].replace(",", "")
            for line in peer.split("\n"):
                if "Type" in line:
                    peer_type = line.split(":")[1].replace("link", "").replace("\r", "").strip()
                    bgppeer_dict["peer_type"] = peer_type
                if "BGP current state:" in line:
                    state = line.split(",")[0].replace("BGP current state:", "").replace("\r", "").strip()
                    bgppeer_dict["state"] = state
                if "remote AS" in line:
                    asn = line.split(",")[1].replace("remote AS", "").replace("\r", "").strip()
                    bgppeer_dict["asn"] = asn
                if "Peer's description:" in line:
                    peer_description = line.split(":")[1].replace("Peer's description:", "").replace("\r", "").replace('"', "").strip()
                    bgppeer_dict["peer_description"] = peer_description
                if "Received total routes:" in line:
                    bgppeer_dict["rcvroutes"] = line.replace("Received total routes:", "").strip()
                if "Advertised total routes:" in line:
                    bgppeer_dict["advroutes"] = line.replace("Advertised total routes:", "").strip()

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
        peer_detail = self.run("display bgp peer {0} verbose".format(peer))
        return peer_detail


    def close(self):
        self.conn.close()

