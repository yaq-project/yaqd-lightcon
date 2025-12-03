from __future__ import annotations

import asyncio
import pathlib
import os
from typing import Any

from yaqd_core import IsHomeable, IsDiscrete, HasLimits, HasPosition, IsDaemon
from ._aiohttp import Client
from ._taskset import TaskSet


class LightconTopas4Motor(IsHomeable, IsDiscrete, HasLimits, HasPosition, IsDaemon):
    _kind = "lightcon-topas4-motor"
    client = Client

    def __init__(self, name: str, config: dict[str, Any], config_filepath: pathlib.Path):
        super().__init__(name, config, config_filepath)
        self.logger.info(f"PID: {os.getpid()}")
        self._base_url = f"http://{config['topas4_host']}:{config['topas4_port']}/{config['serial']}/v0/PublicApi"
        self._motor_index = config["motor_index"]
        self.client.open(config["port"])
        self._http_session = self.client.session
        self._position_identifiers: dict[str, float] = {}
        self.tasks = TaskSet()

    async def update_state(self):
        while True:
            async with self._http_session.get(
                f"{self._base_url}/Motors?id={self._motor_index}"
            ) as resp:
                try:
                    json = await resp.json()
                except:
                    self.logger.error(await resp.read())

                self._state["position"] = json["ActualPositionInUnits"]
                self._state["hw_limits"] = (
                    json["MinimalPositionInUnits"],
                    json["MaximalPositionInUnits"],
                )

                self._units = json["UnitName"]

                offset = json["Affix"]
                scale = json["Factor"]

                self._position_identifiers: dict[str, float] = {
                    i["Name"]: i["Position"] / 8 / scale + offset for i in json["NamedPositions"]
                }

                self._busy = (
                    json["ActualPosition"] != json["TargetPosition"]
                    or abs(json["TargetPositionInUnits"] - self._state["destination"]) > 0.01
                    or json["IsHoming"]
                )

                for i, val in self._position_identifiers.items():
                    if abs(self._state["position"] - val) < 0.01:
                        self._state["position_identifier"] = i
                        break
                else:
                    self._state["position_identifier"] = None

            if not self._busy:
                await self._busy_sig.wait()
            else:
                await asyncio.sleep(0.01)

    def _set_position(self, position):
        self._busy = True
        self.tasks.add(
            self._loop.create_task(
                self._http_session.put(
                    f"{self._base_url}/Motors/TargetPositionInUnits?id={self._motor_index}",
                    json=position,
                )
            )
        )

    def home(self):
        self._busy = True
        self.tasks.add(
            self._loop.create_task(
                self._http_session.post(f"{self._base_url}/Motors/Home?id={self._motor_index}")
            )
        )

    def close(self):
        self.client.close(self._config["port"])
