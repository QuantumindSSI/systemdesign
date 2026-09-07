"""A consistent hash ring, standard library only.

Reference implementation for the series' consistent-hashing material. It
is deliberately small enough to read start to finish, and every design
decision in it is answering one failure.

THE FAILURE. Pick a server for a key with `hash(key) % n`. This works
until n changes. A modulo has no concept of near or far, so shifting the
divisor by one changes the remainder for almost every key, not for a
proportional slice. A cache that loses one node out of five does not lose
a fifth of its entries under plain mod-n; it loses close to all of them.

THE FIX. Place servers and keys on the same circular hash space. A key
belongs to the first server position at or after it, wrapping around at
the top. Removing a server hands its keys to the next position clockwise
and touches nothing else. Adding one takes a slice from a single
neighbour. The number of keys that move is proportional to the capacity
that changed, which is the entire point.

THE CIRCLE IS NOT A DATA STRUCTURE. There is no circle in this file.
There is a sorted list of integers and one wrap-around when the search
runs off the end. The circle is a description of what the wrap does.

WHY MD5 AND NOT `hash()`. Python randomises the hash of str and bytes per
process by default, as a defence against hash-flooding attacks on dicts.
That is the right default inside one process and fatal for a ring, where
two machines, or one machine after a restart, must independently agree on
which node owns a key without talking to each other. MD5 is stable across
processes and machines. It is used here for spread and stability, not for
security, and nothing in this file resists an adversary who chooses keys.
"""

import hashlib
from bisect import bisect_right, insort
from typing import Dict, Iterable, List, Optional

HASH_SPACE = 2 ** 128


def hash_to_ring(value: str) -> int:
    """Map a string to a position on the ring.

    Returns:
        An integer in [0, 2**128), stable across processes and machines.

    Raises:
        TypeError: if `value` is not a str.
    """
    if not isinstance(value, str):
        raise TypeError(f"hash_to_ring needs a str, got {type(value).__name__}")
    return int(hashlib.md5(value.encode("utf-8")).hexdigest(), 16)


class ConsistentHashRing:
    """Maps keys to servers so that adding or removing one moves few keys.

    Attributes:
        replicas: how many positions each physical server claims. This is
            the virtual node count, and it is the knob that controls load
            balance. One position per server distributes badly, because a
            handful of random points on a circle leave wildly uneven gaps.
    """

    def __init__(self, servers: Optional[Iterable[str]] = None, replicas: int = 100):
        """Build a ring, optionally pre-populated.

        Args:
            servers: server names to add immediately.
            replicas: virtual nodes per server, at least 1.

        Raises:
            ValueError: if replicas is below 1.
        """
        if replicas < 1:
            raise ValueError(f"replicas must be at least 1, got {replicas}")
        self.replicas = replicas
        self._positions: List[int] = []
        self._owner: Dict[int, str] = {}
        for server in servers or ():
            self.add_server(server)

    @property
    def servers(self) -> List[str]:
        """Distinct server names currently on the ring, sorted."""
        return sorted(set(self._owner.values()))

    def _virtual_positions(self, server: str) -> List[int]:
        """Positions claimed by one server. Pure function of the name."""
        return [hash_to_ring(f"{server}-{index}") for index in range(self.replicas)]

    def add_server(self, server: str) -> None:
        """Place a server on the ring at `self.replicas` positions.

        `insort` keeps `_positions` sorted as it grows, so no separate sort
        pass is needed. Collisions between two virtual positions are
        astronomically unlikely in a 128-bit space but are handled rather
        than assumed away: a position already claimed is skipped, which
        costs that server one virtual node and nothing else.

        Raises:
            ValueError: if the server is already on the ring.
        """
        if server in self._owner.values():
            raise ValueError(f"server {server!r} is already on the ring")
        for position in self._virtual_positions(server):
            if position in self._owner:
                continue
            self._owner[position] = server
            insort(self._positions, position)

    def remove_server(self, server: str) -> None:
        """Remove every position a server claimed.

        Raises:
            KeyError: if the server is not on the ring.
        """
        positions = [p for p in self._virtual_positions(server)
                     if self._owner.get(p) == server]
        if not positions:
            raise KeyError(f"server {server!r} is not on the ring")
        for position in positions:
            del self._owner[position]
            index = bisect_right(self._positions, position) - 1
            if index >= 0 and self._positions[index] == position:
                del self._positions[index]

    def get_server(self, key: str) -> str:
        """Return the server that owns `key`.

        Walks clockwise from the key's position to the first server
        position at or after it, wrapping to index 0 when the search runs
        off the end of the sorted list. That wrap is the circle.

        Raises:
            LookupError: if the ring is empty.

        Complexity: O(log n) for the binary search over n virtual nodes.
        """
        if not self._positions:
            raise LookupError("cannot route a key: the ring has no servers")
        position = hash_to_ring(key)
        index = bisect_right(self._positions, position)
        if index == len(self._positions):
            index = 0
        return self._owner[self._positions[index]]

    def distribution(self, keys: Iterable[str]) -> Dict[str, int]:
        """Count how many of `keys` land on each server.

        Returns a count for every server on the ring, including zeros, so
        that an empty server is visible rather than missing.
        """
        counts = {server: 0 for server in self.servers}
        for key in keys:
            counts[self.get_server(key)] += 1
        return counts
