"""Query the servers for information."""

import socket
from datetime import datetime
from math import log
from .utils import unicodecmp


class ServerError(Exception):
    pass


class Syncable:
    last_sync = None

    def sync(self):
        try:
            self._sync()
        except (OSError, socket.timeout):
            return False
        self.last_sync = datetime.utcnow()
        return True


class ServerBrowser(Syncable):

    def __init__(self, cup):
        self.cup = cup
        self.servers = cup.db.setdefault("servers", dict)

    def _sync(self):
        to_delete = set(self.servers)
        for x in range(1, 17):
            addr = f"master{x}.teeworlds.com", 8300
            print(addr)
            try:
                self._sync_server_browser(addr, to_delete)
            except (OSError, socket.timeout):
                continue
        for server_id in to_delete:
            self.servers.pop(server_id, None)
        if not self.servers:
            raise OSError("no servers found")
        self.cup.db.sync()

    def _sync_server_browser(self, addr, to_delete):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(5)
        s.sendto(b" \x00\x00\x00\x00H\xff\xff\xff\xffreqt", addr)
        data = s.recvfrom(1024)[0][14:]
        s.close()
        for n in range(0, len(data) // 6):
            addr = ".".join(map(str, map(ord, data[n * 6 : n * 6 + 4]))), ord(
                data[n * 6 + 5]
            ) * 256 + ord(data[n * 6 + 4])
            server_id = f"{addr[0]}:{addr[1]}"
            if server_id in self.servers:
                if not self.servers[server_id].sync():
                    continue
            else:
                try:
                    self.servers[server_id] = Server(addr, server_id)
                except ServerError:
                    pass
            to_delete.discard(server_id)


class Server(Syncable):

    def __init__(self, addr, server_id):
        self.addr = addr
        self.id = server_id
        self.players = []
        if not self.sync():
            raise ServerError("server not responding in time")

    def _sync(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.sendto(b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xffgief", self.addr)
        bits = s.recvfrom(1024)[0][14:].split(b"\x00")
        s.close()
        self.version, server_name, map_name = bits[:3]
        self.name = server_name.decode("latin1")
        self.map = map_name.decode("latin1")
        self.gametype = bits[3]
        self.flags, self.progression, player_count, self.max_players = map(
            int, bits[4:8]
        )
        players = {p.name: p for p in self.players}
        for i in range(player_count):
            name = bits[8 + i * 2].decode("latin1")
            score = int(bits[9 + i * 2])
            if name in players:
                player = players.pop(name)
                player.score = score
            else:
                self.players.append(Player(self, name, score))
        for player in players.values():
            try:
                self.players.remove(player)
            except Exception:
                pass
        self.players.sort(key=lambda x: -x.score)
        self.player_count = len(self.players)

    def __cmp__(self, other):
        return unicodecmp(self.name, other.name)


class Player:

    def __init__(self, server, name, score):
        self.server = server
        self.name = name
        self.score = score
        self.size = round(100 + log(max(score, 1)) * 25, 2)
