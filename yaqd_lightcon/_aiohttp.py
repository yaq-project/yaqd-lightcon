import aiohttp  # type: ignore
import asyncio

from ._taskset import TaskSet


class Client:
    """a single client for all daemons sessions"""

    daemons: set[int] = set()  # keep track of connected daemons
    session = None  # to be initialized
    tasks = TaskSet()

    @classmethod
    def open(cls, daemon_id):
        """initializes a new client if one isn't open"""
        cls.daemons.add(daemon_id)
        if cls.session is None or (cls.session.closed):
            cls.session = aiohttp.ClientSession()

    @classmethod
    def close(cls, daemon_id):
        """close session if there are no daemons still connected"""
        cls.daemons.discard(daemon_id)
        if not cls.daemons:
            cls.tasks.add_coro(cls._close())

    @classmethod
    async def _close(cls) -> None:
        if (cls.session is not None) and (not cls.session.closed):
            await cls.session.__aexit__()
