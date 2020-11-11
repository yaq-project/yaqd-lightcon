import asyncio
import pathlib
from typing import Dict, Any, List

import aiohttp  # type: ignore
from yaqd_core import IsHomeable, HasLimits, HasPosition, IsDaemon


class LightconTopas4Motor(IsHomeable, HasLimits, HasPosition, IsDaemon):
    _kind = "lightcon-topas4-motor"

    def __init__(self, name: str, config: Dict[str, Any], config_filepath: pathlib.Path):
        super().__init__(name, config, config_filepath)
        self._base_url = f"http://{config['topas4_host']}:{config['topas4_port']}/{config['serial']}/v0/PublicApi"
        self._motor_index = config["motor_index"]
        self._http_session = aiohttp.ClientSession()

    async def update_state(self):
        while True:
            async with self._http_session.get(
                f"{self._base_url}/Motors?id={self._motor_index}"
            ) as resp:
                json = await resp.json()
                self._state["position"] = json["ActualPositionInUnits"]
                self._state["hw_limits"] = (
                    json["MinimalPositionInUnits"],
                    json["MaximalPositionInUnits"],
                )

                self._units = json["UnitName"]

                self._busy = (
                    json["ActualPosition"] != json["TargetPosition"]
                    or abs(json["TargetPositionInUnits"] - self._state["destination"]) > 0.01
                    or json["IsHoming"]
                )
            if not self._busy:
                await self._busy_sig.wait()
            else:
                await asyncio.sleep(0.01)

    def _set_position(self, position):
        self._busy = True
        self._loop.create_task(
            self._http_session.put(
                f"{self._base_url}/Motors/TargetPositionInUnits?id={self._motor_index}",
                json=position,
            )
        )

    def home(self):
        self._busy = True
        self._loop.create_task(
            self._http_session.post(f"{self._base_url}/Motors/Home?id={self._motor_index}")
        )
