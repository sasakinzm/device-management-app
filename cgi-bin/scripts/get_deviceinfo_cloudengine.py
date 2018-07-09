#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import telnetlib
from interfaceinfo import interfaceinfo

class session_create_cloudengine(interfaceinfo):
    """
    ostype が cloudengine の時にデバイス情報を取得するクラス
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
        self.conn.read_until("\n<{0}>".format(host).encode("utf-8"))
        self.conn.write("screen-length 0 temporary \n".encode("utf-8"))
        self.conn.read_until("\n<{0}>".format(host).encode("utf-8"))


    def run(self, command):
        """
        任意のコマンドを実行する関数
        ◆引数
        command: 実行するCLIコマンド
        """
        self.conn.write("{0}\n".format(command).encode("utf-8"))
        stdout = self.conn.read_until("\n<{0}>".format(self.host).encode("utf-8"))
        stdout = stdout.decode("utf-8")
        return stdout


    def get_sysinfo(self):
        """
        装置のモデル名、OSバージョン、筐体シリアルナンバーを取得する関数
        それぞれ、name, os_version, serial というメソッドに格納する。返り値はそれらのディクショナリ。
        """
        ### モデル名を取得
        stdout = self.run("display version")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if row.startswith("HUAWEI "): model_row = row   # モデル名を含む行のみを抽出
        model = model_row.split()[1]       # モデル名のみを抽出
        self.model = model.replace("\r", "").strip()

        ### OSバージョンを取得
        for row in stdout_list:
            if "VRP (R) software," in row: version_row = row   # バージョンを含む行のみを抽出
        for row in version_row.split(","):
            if "Version " in row: version = row       # バージョン番号のみを抽出
        self.os_version = version.replace("\r", "").strip()

        ### 筐体シリアルナンバーを取得
        stdout = self.run("display sn")
        stdout_list = stdout.split("\n")
        for row in stdout_list:
            if row.startswith("Equipment SN"): serial_row = row   # シリアルを含む行のみを抽出
        serial = serial_row.split(":")[1]       # シリアル番号のみを抽出
        self.serial = serial.replace("\r", "").strip()


    def get_interface(self):
        """
        機器のインターフェースの情報を取得する
        インターフェース名、Adminステート、リンク状態、帯域幅、ディスクリプション、
        LAGに含まれる場合は所属するLAGグループ、LAGポートなら含まれるLAGメンバーを取得する
        """
        ifname = self.run("display interface | include current state : | exclude Line protocol")
        ifname_list = [l.split()[0] for l in ifname.split("\n")[2:-1]]     ### インターフェース名を格納した配列に整形

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

        ### インターフェース1つ毎に、name, admin_state, link_state, speed, description, lag_group, lag_member を key とするディクショナリを作る
        ### それらを interfaces 配列に格納していく
        interfaces = []
        for i in ifname_list:
            interface_dict = {}
            interface_dict["name"] = i

            output1 = self.run("display interface {0}".format(interface_dict["name"]))
            output1_list = output1.split("\n")

            ### 各インターフェースに対して、Adminステートとリンク状態と帯域幅とディスクリプションを取得する
            for j in output1_list:
                if "{0} current state :".format(interface_dict["name"]) in j:
                    if "Administratively DOWN" in j: admin_state = "DOWN"
                    else: admin_state = "UP"
                    interface_dict["admin_state"] = admin_state
                if "Line protocol current state :" in j:
                    link_state = j.split(":")[1].strip()
                    interface_dict["link_state"] = link_state
                if "Current BW :" in j:
                    for k in j.split(","):
                        if "Current BW :" in k: speed = k.replace("Current BW : ", "").strip()
                    interface_dict["speed"] = speed
                if "Description: " in j:
                    description = j.replace("Description: ", "")
                    interface_dict["description"] = description.replace("\r", "")

            ### lag_group_dict から物理インターフェースが所属するEthTrunkポートを取得する
            if i in lag_group_dict.keys():
                interface_dict["lag_group"] = lag_group_dict[i]


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

            ### これまでの処理で、必要な key に値が入らなかった部分を "-" で埋める
            keys = ["name", "admin_state", "link_state", "speed", "description", "lag_group", "lag_member"]
            key_diff = list(set(keys) - set(interface_dict.keys()))
            for key in key_diff:
                interface_dict[key] = "-" 

            interfaces.append(interfaceinfo(interface_dict["name"], interface_dict["admin_state"], interface_dict["link_state"], interface_dict["speed"], interface_dict["description"], interface_dict["lag_group"], interface_dict["lag_member"]))

        return interfaces


    def close(self):
        self.conn.close()

