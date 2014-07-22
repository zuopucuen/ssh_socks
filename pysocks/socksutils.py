#!/usr/bin/env python
#-*- coding:utf-8 -*-
#Author:left_left
import socket
import struct
import select
import os
import sys
import time
import threading

sock_list = {}

if os.name == 'nt':
    s = socket.socket()
    sock_list[0] = {s}
else:
    sock_list[0] = set()

sock_dict = {}

class GetConn(object):
    def __init__(self,socks_port, socks_bind):
        self.socks_port = socks_port
        self.socks_bind = socks_bind

    def get_conn(self, sock_queue, log_queue):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, e:
            print "create a socket failed:", e
            sys.exit(1)

        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except socket.error, e:
            print "setsocketopt error:", e
            sys.exit(1)

        try:
            s.bind((self.socks_bind, self.socks_port))
        except socket.error, e:
            print "bind ip error:", e
            sys.exit(1)

        try:
            s.listen(10)
        except socket.error, e:
            print "listen error:", e
            sys.exit(1)

        s_list = set([s])
        f_list = set()
    
        while 1:
            r, w, x = select.select(s_list, [], [])
            for sock in r:
                if sock is s:
                    sock, addr = sock.accept()
                    s_list |= {sock}
                else:
                    try:
                        data = sock.recv(1024)
                    except socket.error, e:
                        log_queue.put("recv data error:%s" % str(e))
                        continue

                    try:
                        d = data[0]
                    except IndexError, e:
                        log_queue.put("error client:%s" % str(e))
                        s_list -= {sock}
                        sock.close()
                        continue

                    if ord(d) == 4:
                        s_list -= {sock}
                        try:
                            remote_port = ord(data[3])
                            remote_host = socket.inet_ntoa(data[4:8])
                            sock_queue.put([remote_port, remote_host, sock, 0])
                        except IndexError, e:
                            log_queue.put("error client:%s" % str(e))
                            sock.close()
                    elif sock in f_list:
                        s_list -= {sock}
                        f_list -= {sock}
                        try:
                            remote_port = ord(data[9])
                            remote_host = socket.inet_ntoa(data[4:8])
                            sock_queue.put([remote_port, remote_host, sock, 1])
                        except IndexError, e:
                            log_queue.put("error client:%s" % str(e))
                            sock.close()
                    else:
                        try:
                            sock.send(b"\x05\x00")
                            f_list |={sock}
                        except socket.error, e:
                            log_queue.put("error client:%s" % str(e))
                            s_list -= {sock}
                            sock.close()

class Worker(threading.Thread):
    def __init__(self, sock_queue, log_queue, createchannel, ssh_transport=None):
        threading.Thread.__init__(self)
        self.sock_queue = sock_queue
        self.log_queue = log_queue
        self.createchannel = createchannel
        self.ssh_transport = ssh_transport

    def response(self, cs, reply):
        try:
            c = cs.getsockname()
            cs.send("".join( [reply, socket.inet_aton(c[0]),
            struct.pack(">H", c[1])]))
        except socket.error, e:
            self.log_queue.put("send response error:%s" % str(e))
            return True
        return False

    def sendrecv(self, chan, cs):
        pass

    def run(self):
        reply_e5 = b"\x05\x05\x00\x01"
        reply_e4 = b"\x00\x0c"
        reply_5 = b"\x05\x00\x00\x01"
        reply_4 = b"\x00\x5a"

        while 1:
            port, host, cs, v = self.sock_queue.get()

            try:
                cs_addr_port = cs.getpeername()
            except socket.error, e:
                self.log_queue.put("client socket error:%s" % str(e))
                cs.close()
                continue

            try:
                chan = self.createchannel(host, port, cs_addr_port, self.ssh_transport)
            except Exception, e:
                self.log_queue.put("channel connect error:%s" % str(e))
                if v:
                    self.response(cs, reply_e5)
                    cs.close()
                    continue
                else:
                    self.response(cs, reply_e4)
                    cs.close()
                    continue

            if v:
                r = self.response(cs, reply_5)
            else:
                r = self.response(cs, reply_4)

            if r:
                cs.close()
                continue
            else:
                self.log_queue.put("      open channel from %s:%s to %s:%s"
                            % (cs_addr_port[0], cs_addr_port[1], host, port))
                self.sendrecv(chan, cs)
 
class logOut(threading.Thread):
    def __init__(self, log_queue):
        threading.Thread.__init__(self)
        self.queue = log_queue

    def run(self):
        while 1:
            print "%s      %s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), self.queue.get())

class CreateChannelMore(Worker):
    def sendrecv(self, chan, cs):
        try:
            while 1:
                r, w, x = select.select([chan, cs], [], [])
                if chan in r:
                    data = chan.recv(4096)
                    if len(data) > 0:
                        cs.send(data)
                    else:
                        cs.close()
                        chan.close()
                        break

                if cs in r:
                    data = cs.recv(4096)
                    if len(data) > 0:
                        chan.send(data)
                    else:
                        cs.close()
                        chan.close()
                        break
        except socket.error, e:
            self.log_queue.put("transport error:%s" % str(e))
            cs.close()
            chan.close()

class CreateChannelOne(Worker):
    def sendrecv(self, chan, cs):
        sock_list[0] |= {chan, cs}
        sock_dict[chan] = cs
        sock_dict[cs] = chan

class SendRecv(threading.Thread):
    def run(self):
        print "start server ......"
        while 1:
            r, w, x = select.select(sock_list[0], [], [], 0.1)
            for s in r:
                try:
                    c = sock_dict[s]
                except KeyError:
                    continue

                try:
                    data = s.recv(8192)

                    if len(data) > 0:
                        c.send(data)
                    else:
                        s.close()
                        c.close()
                        sock_list[0] -= {c, s}
                        del sock_dict[c], sock_dict[s]
                except socket.error, e:
                    s.close()
                    c.close()
                    sock_list[0] -= {c, s}
                    del sock_dict[c], sock_dict[s]
