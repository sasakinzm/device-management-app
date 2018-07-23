#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class interfaceinfo:
    def __init__(self, name, admin_state, link_state, speed, description, lag_group, lag_member, media_type):
        self.name = name
        self.admin_state = admin_state
        self.link_state = link_state
        self.speed = speed
        self.description = description
        self.lag_group = lag_group
        self.lag_member = lag_member
        self.media_type = media_type

class bgpinfo:
    def __init__(self, addr, peer_type, state, asn, rcvroutes, advroutes, peer_description):
        self.addr = addr
        self.peer_type = peer_type
        self.state = state
        self.asn = asn
        self.rcvroutes = rcvroutes
        self.advroutes = advroutes
        self.peer_description = peer_description
