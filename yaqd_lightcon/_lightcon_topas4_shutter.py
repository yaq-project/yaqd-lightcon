import asyncio
import pathlib
from typing import Dict, Any, List

import aiohttp  # type: ignore
from yaqd_core import DiscreteHardware

from .__version__ import __branch__

class LightconTopas4Shutter(DiscreteHardware):
    traits: List[str] = []
    _kind = "lightcon-topas4-shutter"
    _version = "0.1.0" + f"+{__branch__}" if __branch__ else ""

    def __init__(self, name: str, config: Dict[str, Any], config_filepath: pathlib.Path):
        super().__init__(name, config, config_filepath)
        self._base_url = config["base_url"]
        self._http_session = aiohttp.ClientSession()
        self._position_identifiers = {
            "closed": 0,
            "open": 1,
        }

    async def update_state(self):
        while True:
            async with self._http_session.get(
                f"{self._base_url}/ShutterInterlock/IsShutterOpen"
            ) as resp:
                try:
                    self._position = await resp.json()
                except:
                    self.logger.error(await resp.read())
            self._busy = (bool(self._position) != bool(self._destination))
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
