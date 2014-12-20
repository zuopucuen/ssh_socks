#!/usr/bin/env python
#-*- coding:utf-8 -*-
#Author:left_left
import socks_ssh
server = '127.0.0.1'
port = 10000
user = 'root'
password = 'password'
bind_addr = '0.0.0.0'
bind_port = 1080
t_num = 10
socks_ssh.run(server, port, user, password, bind_addr, bind_port, t_num)
