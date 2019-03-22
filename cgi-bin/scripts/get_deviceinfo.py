#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
from venders.get_deviceinfo_junos import *
from venders.get_deviceinfo_arista import *
from venders.get_deviceinfo_cloudengine import *
from venders.get_deviceinfo_netengine import *
from venders.get_deviceinfo_ios import *
from venders.get_deviceinfo_ios2600 import *
from venders.get_deviceinfo_iosxr import *
from venders.get_deviceinfo_iosxe import *
from venders.get_deviceinfo_brocade import *
from venders.get_deviceinfo_nxos import *

class session_create:
    def __init__(self,host,domain,user,password,ostype):
        self.ostype = ostype
        if ostype == "junos" :
            self.sess = session_create_junos(host, domain, user, password)
        if ostype == "arista" :
            self.sess = session_create_arista(host, domain, user, password)
        if ostype == "cloudengine" :
            self.sess = session_create_cloudengine(host, domain, user, password)
        if ostype == "netengine" :
            self.sess = session_create_netengine(host, domain, user, password)
        if ostype == "ios" :
            self.sess = session_create_ios(host, domain, user, password)
        if ostype == "ios2600" :
            self.sess = session_create_ios2600(host, domain, user, password)
        if ostype == "iosxr" :
            self.sess = session_create_iosxr(host, domain, user, password)
        if ostype == "iosxe" :
            self.sess = session_create_iosxe(host, domain, user, password)
        if ostype == "brocade" :
            self.sess = session_create_brocade(host, domain, user, password)
        if ostype == "nxos" :
            self.sess = session_create_nxos(host, domain, user, password)

    def run(self, command):
        return self.sess.run(command)

    def get_config(self):
        return self.sess.get_config()

    def get_hardware(self):
        return self.sess.get_hardware()

    def get_sysinfo(self):    
        self.sess.get_sysinfo()
        self.model = self.sess.model
        self.os_version = self.sess.os_version
        self.serial = self.sess.serial

    def get_interface(self):
        return self.sess.get_interface()

    def get_interface_detail(self, interface):
        return self.sess.get_interface_detail(interface)

    def get_bgppeer(self):
        return self.sess.get_bgppeer()

    def get_peer_detail(self, peer):
        return self.sess.get_peer_detail(peer)

    def close(self):
        return self.sess.close()


if __name__ == "__main__":
    host = sys.argv[1]
    domain = sys.argv[2]
    user  = sys.argv[3]
    password = sys.argv[4]
    ostype = sys.argv[5]
    conn = session_create(host, domain, user, password, ostype)
    conn.get_sysinfo()
    print("\n1. SYS INFO\n#######################################################\n")
    print(conn.model, conn.serial, conn.os_version)
    print("\n2. HARDWARE INFO\n#######################################################\n")
    print(conn.get_hardware())
    print("\n4. CONFIG\n#######################################################\n")
    print(conn.get_config())
    print("\n5. INTERFACE INFO\n#######################################################\n")
    interfaces = conn.get_interface()
    for i in interfaces:
        print(i.name, i.admin_state, i.link_state, i.speed, i.description, i.lag_group, i.lag_member, i.media_type)
    print("\n6. BGP Peer INFO\n#######################################################\n")
    bgpinfo = conn.get_bgppeer()
    for j in bgpinfo:
        print(j.addr, j.peer_type, j.state, j.asn, j.rcvroutes, j.advroutes, j.peer_description)
    conn.close()