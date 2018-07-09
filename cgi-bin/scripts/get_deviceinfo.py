#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from get_deviceinfo_junos import *
from get_deviceinfo_arista import *
from get_deviceinfo_cloudengine import *

class session_create:
    def __init__(self,host,domain,user,password,ostype):
        self.ostype = ostype
        if ostype == "junos" :
            self.sess = session_create_junos(host, domain, user, password)
        if ostype == "arista" :
            self.sess = session_create_arista(host, domain, user, password)
        if ostype == "cloudengine" :
            self.sess = session_create_cloudengine(host, domain, user, password)

    def run(self, command):
        return self.sess.run(command)

    def get_sysinfo(self):    
        return self.sess.get_sysinfo()

    def get_interface(self):
        return self.sess.get_interface()
