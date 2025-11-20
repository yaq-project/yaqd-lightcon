import aiohttp  # type: ignore
import asyncio


class TaskSet(set):
    """container class for tasks to keep strong references"""
    def add(self, task:asyncio.Task):
        super().add(task)
        task.add_done_callback(self.discard)

    def add_coro(self, coro:asyncio._CoroutineLike):
        """create task and add to running loop"""
        task = asyncio.get_running_loop().create_task(coro)
        self.add(task)


class Client:
    """a single client for all daemons sessions"""
    daemons = set()  # keep track of connected daemons
    session = None  # to be initialized
    tasks = TaskSet()

    def open(cls, daemon_id):
        """initializes a new client if one isn't open"""
        cls.daemons.add(daemon_id)
        if cls.session is None or (cls.session.closed):
            cls.session = aiohttp.ClientSession()

    def close(cls, daemon_id):
        """close session if there are no daemons still connected"""
        cls.daemons.discard(daemon_id)
        if not cls.daemons:
            cls.tasks.add_coro(cls.close())

    async def close(cls) -> None:
        if (cls.session is not None) and (not cls.session.closed):
            await cls.session.__aexit__()


