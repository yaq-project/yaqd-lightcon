import asyncio
import pathlib
from typing import Dict, Any, List

from yaqd_core import IsDiscrete, IsDaemon
from ._aiohttp import Client
from ._taskset import TaskSet


class LightconTopas4Shutter(IsDiscrete, IsDaemon):
    _kind = "lightcon-topas4-shutter"
    client = Client

    def __init__(self, name: str, config: Dict[str, Any], config_filepath: pathlib.Path):
        super().__init__(name, config, config_filepath)
        self._base_url = f"http://{config['topas4_host']}:{config['topas4_port']}/{config['serial']}/v0/PublicApi"
        self.client.open(config["port"])
        self._http_session = self.client.session
        self.tasks = TaskSet()

    async def update_state(self):
        while True:
            async with self._http_session.get(
                f"{self._base_url}/ShutterInterlock/IsShutterOpen"
            ) as resp:
                try:
                    self._state["position"] = await resp.json()
                    self._state["position_identifier"] = (
                        "open" if self._state["position"] else "closed"
                    )
                except:
                    self.logger.error(await resp.read())
            self._busy = bool(self._state["position"]) != bool(self._state["destination"])
            if not self._busy:
                await self._busy_sig.wait()
            else:
                await asyncio.sleep(0.01)

    def _set_position(self, position):
        self._busy = True
        self.tasks.add(
            self._loop.create_task(
                self._http_session.put(
                    f"{self._base_url}/ShutterInterlock/OpenCloseShutter", json=bool(position)
                )
            )
        )

    def close(self):
        self.client.close(self._config["port"])
