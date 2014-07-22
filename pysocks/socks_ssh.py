#!/usr/bin/env python
#-*- coding:utf-8 -*-
#Author:left_left
import sys
import Queue
import paramiko
import socksutils
from optparse import OptionParser

def createchannel(host, port, cs_addr_port, ssh_transport):
    chan = ssh_transport.open_channel('direct-tcpip', (host, port), cs_addr_port)
    return chan

def ssh_client(server='192.168.1.1', port=22, user='root', password='password'):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(server, port, user, password)
    except Exception, e:
        print"con't connect ssh server:", e
        sys.exit(1)
    return client

def parse():
    p = OptionParser()
    p.set_usage("command [options] host port")
    p.add_option('-p', '--port-socks', dest='socks_port', default=1080)
    p.add_option('-b', '--bind_addr', dest='socks_bind', default="127.0.0.1")
    p.add_option('-u', '--user', dest='username', default='root')
    p.add_option('-P', '--password', dest='password', default='password')
    p.add_option('-t', '--threads', dest='thread_num', default=10)
    return p

def run(server, port, user, password, socks_bind, socks_port, t_num):
    sock_queue = Queue.Queue()
    log_queue = Queue.Queue()

    client = ssh_client(user=user, password=password, server=server, port=port)
    ssh_transport = client.get_transport()
    w = []

    if t_num < 20:
        from socksutils import CreateChannelOne as CreateChannel
        sr = socksutils.SendRecv()
        sr.setDaemon(True)
        sr.start()
    else:
        from socksutils import CreateChannelMore as CreateChannel

    for i in xrange(t_num):
        w.append(CreateChannel(sock_queue, log_queue, createchannel, ssh_transport=ssh_transport))

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

    try:
        server = args[0]
        port = int(args[1])
    except Exception:
        print "Please use '-h/--help' for help!"
        sys.exit(1)

    user = options.username
    password = options.password
    socks_bind = options.socks_bind
    socks_port = int(options.socks_port)
    t_num = int(options.thread_num)

    run(server, port, user, password, socks_bind, socks_port, t_num)
