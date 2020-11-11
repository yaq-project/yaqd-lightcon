import asyncio
import pathlib
from typing import Dict, Any, List

import aiohttp  # type: ignore
from yaqd_core import IsDiscrete, IsDaemon


class LightconTopas4Shutter(IsDiscrete, IsDaemon):
    _kind = "lightcon-topas4-shutter"

    def __init__(self, name: str, config: Dict[str, Any], config_filepath: pathlib.Path):
        super().__init__(name, config, config_filepath)
        self._base_url = f"http://{config['topas4_host']}:{config['topas4_port']}/{config['serial']}/v0/PublicApi"
        self._http_session = aiohttp.ClientSession()

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
        self._loop.create_task(
            self._http_session.put(
                f"{self._base_url}/ShutterInterlock/OpenCloseShutter", json=bool(position)
            )
        )
