#!/usr/bin/env python
#-*- coding:utf-8 -*-
#Author:left_left
import socks
bind_addr = '0.0.0.0'
bind_port = 1080
t_num = 10
socks.run(bind_addr, bind_port, t_num)
