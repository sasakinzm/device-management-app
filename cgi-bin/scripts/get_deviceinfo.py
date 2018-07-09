#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from get_deviceinfo_junos import *
from get_deviceinfo_arista import *
from get_deviceinfo_cloudengine import *
from get_deviceinfo_netengine import *
from get_deviceinfo_ios import *
from get_deviceinfo_iosxr import *
from get_deviceinfo_brocade import *

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
        if ostype == "iosxr" :
            self.sess = session_create_iosxr(host, domain, user, password)
        if ostype == "brocade" :
            self.sess = session_create_brocade(host, domain, user, password)

    def run(self, command):
        return self.sess.run(command)

    def get_sysinfo(self):    
        self.sess.get_sysinfo()
        self.model = self.sess.model
        self.os_version = self.sess.os_version
        self.serial = self.sess.serial

    def get_interface(self):
        return self.sess.get_interface()

    def close(self):
        return self.sess.close()
