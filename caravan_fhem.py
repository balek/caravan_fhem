#!/usr/bin/env python

import json

from twisted.internet.defer import Deferred, inlineCallbacks, returnValue, CancelledError
from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet import reactor, protocol

from autobahn.twisted.util import sleep

from caravan.base import VanSession, VanModule, VanDevice, deviceCommand
from caravan.types import Str, List



PROMPT = 'fhem> '


class FhemCommandProtocol(protocol.Protocol):
    answer = None

    @inlineCallbacks
    def connectionMade(self):
        yield self.command('')
        result = yield self.command('jsonlist2')
        result = json.loads(result)
        for device in result['Results']:
            FhemDevice(self.factory.module, device)

    def dataReceived(self, data):
        if not self.answer:
            return
        self.buffer += data
        if self.buffer.endswith(PROMPT):
            result = self.buffer[:-len(PROMPT)]
            self.answer, answer = None, self.answer
            answer.callback(result)

    @inlineCallbacks
    def command(self, command):
        while self.answer:
            yield self.answer
        self.transport.write(str(command) + '\n')
        self.buffer = ''
        self.answer = Deferred()
        result = yield self.answer
        returnValue(result)


class FhemCommandFactory(protocol.ClientFactory):
    protocol = FhemCommandProtocol

    def __init__(self, module):
        self.module = module

    def buildProtocol(self, address):
        self.protocol = protocol.ClientFactory.buildProtocol(self, address)
        return self.protocol


class FhemEventProtocol(LineOnlyReceiver):
    delimiter = '\n'

    def connectionMade(self):
        self.sendLine('inform on')

    def lineReceived(self, line):
        print line
        words = line.split()
        device = self.factory.module.children.get(words[1])
        if device is None:
            return
        device.emitEvent(*words[2:])


class FhemEventFactory(protocol.ClientFactory):
    protocol = FhemEventProtocol

    def __init__(self, module):
        self.module = module


class FhemDevice(VanDevice):
    list = None

    def __init__(self, parent, desc):
        super(FhemDevice, self).__init__(parent, desc['Name'])

    @deviceCommand(List('set', 'get', 'attr'), Str())
    def call(self, command, args):
        return self.parent.commandFactory.protocol.command('%s %s %s' % (command, self.name, args))


class Fhem(VanModule):
    def __init__(self, server, port, parent, name):
        super(Fhem, self).__init__(parent, name)
        self.commandFactory = FhemCommandFactory(self)
        reactor.connectTCP(server, port, self.commandFactory)  # @UndefinedVariable
        reactor.connectTCP(server, port, FhemEventFactory(self))  # @UndefinedVariable


class AppSession(VanSession):
    def start(self):
        Fhem('localhost', 7072, self, 'fhem')



if __name__ == '__main__':
    from autobahn.twisted.wamp import ApplicationRunner
    runner = ApplicationRunner("ws://127.0.0.1/ws", "realm1")
    runner.run(AppSession)
