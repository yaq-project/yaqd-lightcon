import aiohttp  # type: ignore
import asyncio


class TaskSet(set):
    """container class for tasks to keep strong references"""
    def add(self, task:asyncio.Task):
        super().add(task)
        task.add_done_callback(self.discard)


class Client:
    """a single client session for all daemons"""
    daemons = set()  # keep track of connected daemons
    session = None  # to be initialized
    tasks = TaskSet()

    def open(cls, daemon_id):
        cls.daemons.add(daemon_id)
        if cls.session is None:
            cls.session = aiohttp.ClientSession()

    def close(cls, daemon_id):
        """close session only if there are no daemons still running off of it"""
        cls.daemons.discard(daemon_id)
        if not cls.daemons:
            cls.tasks.add(asyncio.get_running_loop().create_task(cls.close()))

    async def close(cls) -> None:
        if (cls.session is not None) and (not cls.session.closed):
            await cls.session.close()
            cls.session = None


