#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class interfaceinfo:
    def __init__(self, name, admin_state, link_state, speed, description, lag_group, lag_member):
        self.name = name
        self.admin_state = admin_state
        self.link_state = link_state
        self.seped = speed
        self.description = description
        self.lag_group = lag_group
        self.lag_member = lag_member
