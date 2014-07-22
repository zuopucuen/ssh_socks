#!/usr/bin/env python
#-*- coding:utf-8 -*-
#Author:left_left
import socket
import Queue
import socksutils
from optparse import OptionParser

def createchannel(host, port, c, d):
    chan = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    chan.connect((host, port))
    return chan

def parse():
    p = OptionParser()
    p.set_usage("command [options] host port")
    p.add_option('-p', '--port-socks', dest='socks_port', default=1080)
    p.add_option('-b', '--bind_addr', dest='socks_bind', default="127.0.0.1")
    p.add_option('-t', '--threads', dest='thread_num', default=10)
    return p

def run(socks_bind, socks_port, t_num):
    sock_queue = Queue.Queue()
    log_queue = Queue.Queue()
    w = []

    if t_num < 20:
        from socksutils import CreateChannelOne as CreateChannel
        sr = socksutils.SendRecv()
        sr.setDaemon(True)
        sr.start()
    else:
        from socksutils import CreateChannelMore as CreateChannel

    for i in xrange(t_num):
        w.append(CreateChannel(sock_queue, log_queue, createchannel))

    for i in w:
        i.setDaemon(True)
        i.start()

    logout = socksutils.logOut(log_queue)
    logout.setDaemon(True)
    logout.start()

    print"start socks forward  at %s prot %s" % (socks_bind, socks_port)

    g = socksutils.GetConn(socks_port, socks_bind)
    g.get_conn(sock_queue, log_queue)

    for i in xrange(t_num):
        w[i].join()

if __name__ == '__main__':   
    p = parse()
    options, args = p.parse_args()

    socks_bind = options.socks_bind
    socks_port = int(options.socks_port)
    t_num = int(options.thread_num)

    run(socks_bind, socks_port, t_num)
