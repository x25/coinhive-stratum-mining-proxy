#!/usr/bin/env python
# The MIT License (MIT)
#
# Copyright (c) 2017
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import autobahn.twisted.websocket
import autobahn.twisted.resource
import json
import os
import socket
import sys
import time
import twisted.internet.defer
import twisted.internet.protocol
import twisted.internet.reactor
import twisted.protocols.basic
import twisted.web.resource
import twisted.web.server
import twisted.web.static

from twisted.internet import ssl
from twisted.python import log

def toJson(obj):
    return json.dumps(obj).encode("utf-8")

class Container:

    def __init__(self):
      self.rpcId = 0
      self.workerId = None
      self.hashes = 0
      self.to_client = twisted.internet.defer.DeferredQueue()
      self.to_server = twisted.internet.defer.DeferredQueue()

    def getNextRpcId(self):
        self.rpcId += 1
        return self.rpcId

    def incAndGetHashes(self):
        self.hashes += 1
        return self.hashes

class Root(twisted.web.static.File):

    def render(self, request):
        request.setHeader('Access-Control-Allow-Origin','*')
        return super(Root, self).render(request)

    def directoryListing(self):
        return twisted.web.resource.ForbiddenResource()

class ProxyClient(twisted.protocols.basic.LineOnlyReceiver):

    delimiter = b'\n'

    def connectionMade(self):
        log.msg('Server connected')
        self.factory.di.to_server.get().addCallback(self.dataEnqueued)
        try:
            self.transport.getHandle().setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.transport.getHandle().setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 30)
            self.transport.getHandle().setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 1)
            self.transport.getHandle().setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 5)
        except:
            pass

    def dataEnqueued(self, data):
        if data is None:
            log.msg('Client disconnecting from server')
            self.transport.loseConnection()
        else:
            log.msg('Queue -> Server: %s' % str(data))
            self.transport.write(data)
            if not data.endswith(self.delimiter):
                self.transport.write(self.delimiter)
            self.factory.di.to_server.get().addCallback(self.dataEnqueued)

    def lineReceived(self, line):
        log.msg('Server -> Queue: %s' % line)
        data = json.loads(line)
        if data.get("id") == 1:
          self.factory.di.workerId = data.get("result").get("id")
          self.factory.di.to_client.put(b'{"type":"authed","params":{"token":"","hashes":0}}')
          if data.get('result', {}).get('job'):
            self.factory.di.to_client.put(toJson({'type':'job','params':data['result']['job']}))
        elif data.get('method') == 'job':
          self.factory.di.to_client.put(toJson({'type':'job','params':data['params']}))
        elif data.get('result', {}).get('status') == 'OK':
          hashes = self.factory.di.incAndGetHashes()
          self.factory.di.to_client.put(toJson({'type':'hash_accepted','params':{'hashes':hashes}}))

    def connectionLost(self, why):
        log.msg('Server disconnected (%s)' % str(why))
        self.factory.di.to_client.put(None)


class ProxyClientFactory(twisted.internet.protocol.ClientFactory):
    protocol = ProxyClient

    def __init__(self, container):
        self.di = container

    def clientConnectionFailed(self, connector, why):
        log.msg('Server connection failed (%s)' % str(why))
        self.di.to_client.put(None)

class ProxyServer(autobahn.twisted.websocket.WebSocketServerProtocol):

    def onConnect(self, request):
        log.msg('Client connected (%s)' % str(request))
        details["clients"] +=1

    def onOpen(self):
        log.msg('WebSocket is open')
        self.di = Container()
        self.di.to_client.get().addCallback(self.onQueue)
        factory = ProxyClientFactory(self.di)
        twisted.internet.reactor.connectTCP(self.targetHost, self.targetPort, factory)

    def onQueue(self, data):
        if data is None:
            log.msg('Server disconnecting from client')
            self.sendClose()
        else:
            log.msg('Queue -> Client: %s' % str(data))
            self.sendMessage(data, False)
            mData = json.loads(data)
            #{"params": {"hashes": 1}, "type": "hash_accepted"}
            if mData["type"] == "hash_accepted":
              details["total_hashes"] += 1

            self.di.to_client.get().addCallback(self.onQueue)

    def onMessage(self, data, isBinary):
        log.msg('Client -> Queue (%s): %s' % ('binary' if isBinary else 'text', str(data)))
        data = json.loads(data)
        if data.get('type') == 'auth':
            login = data['params']['site_key']
            if data['params'].get('user'):
                login = login + "." + data['params']['user']
            self.di.to_server.put(toJson({'method':'login','params':{'login':login,'pass':self.authPass},'id':self.di.getNextRpcId()}))
        if data.get('type') == 'submit':
            data['params']['id'] = self.di.workerId
            self.di.to_server.put(toJson({'method':'submit','params':data['params'],'id':self.di.getNextRpcId()}))

    def onClose(self, wasClean, code, reason):
        if hasattr(self, 'di'):
            log.msg('Client disconnected (%s, %s, %s)' % (str(wasClean), str(code), str(reason)))
            details["clients"] -= 1
            self.di.to_server.put(None)

class SimpleStats(twisted.web.resource.Resource):

    isLeaf=True

    def __init__(self, details, passwd):
        self.details = details
        self.boot_time = time.time()
        self.passwd = passwd

    def render_GET(self, request):
        passwd = request.args.get("password", None)
        if (passwd and passwd[0] == self.passwd) or not self.passwd:
          self.details["uptime"] = time.time() - self.boot_time  
          return toJson(details)
        request.setResponseCode(403)
        return toJson({"error": "unauthorized"})

if __name__ == "__main__":
    details = {"total_hashes": 0, "clients": 0}

    from argparse import ArgumentParser
    usage = "%prog <stratum tcp host> <stratum tcp port> [options]"
    parser = ArgumentParser(description=usage)

    parser.add_argument("pool_host", metavar="host", help="stratum tcp host")
    parser.add_argument("pool_port", metavar="stratum_port", help="stratum tcp port", type=int, choices=range(1,65535))
    parser.add_argument("--websocket_port", metavar="PORT", help="port to listen for websocket clients", type=int, choices=range(1,65535), default=8892)
    parser.add_argument("--ssl", help="Enables SSL for Websocket clients. (privatekey:certificate)", metavar="CERTIFICATES", dest="ssl")
    parser.add_argument("--pool_pass", help="stratum auth password (Default: x)", default="x")
    parser.add_argument("--password", help="Password for the stats page (Default: No password)", default=None)

    arguments = vars(parser.parse_args())
    log.startLogging(sys.stdout)

    ProxyServer.targetHost = arguments["pool_host"]
    ProxyServer.targetPort = arguments["pool_port"]
    ProxyServer.authPass = arguments["pool_pass"]
    ProxyServer.details = details

    ws = autobahn.twisted.websocket.WebSocketServerFactory()
    ws.protocol = ProxyServer

    root = Root('./static')
    root.putChild(b"proxy", autobahn.twisted.resource.WebSocketResource(ws))
    root.putChild(b"stats", SimpleStats(details, arguments["password"]))

    requestFactory = twisted.web.server.Site(root)

    if arguments["ssl"]:
      import OpenSSL
      try:
        contextFactory = ssl.DefaultOpenSSLContextFactory(arguments["ssl"].split(":")[0], arguments["ssl"].split(":")[1])
        twisted.internet.reactor.listenSSL(arguments["websocket_port"], requestFactory, contextFactory)
      except OpenSSL.SSL.Error:
        print("Invalid privatekey:certificate pair")
        sys.exit(1)
    else:
      twisted.internet.reactor.listenTCP(arguments["websocket_port"], requestFactory)
    twisted.internet.reactor.run()
