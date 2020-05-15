import asyncio
import pathlib
from typing import Dict, Any, List

import aiohttp  # type: ignore
from yaqd_core import Base, logging

from .__version__ import __branch__


class Topas4(Base):
    traits: List[str] = []
    _kind = "topas4"
    _version = "0.1.0" + f"+{__branch__}" if __branch__ else ""

    def __init__(self, name: str, config: Dict[str, Any], config_filepath: pathlib.Path):
        super().__init__(name, config, config_filepath)
        self._base_url = config["base_url"]
        self._http_session = aiohttp.ClientSession()
        self._motors: Dict[str, Dict[str, Any]] = {}
        self._shutter_status = False
        self._shutter_target = False
        self._loop.create_task(self._populate_motors_dict())

    async def _populate_motors_dict(self):
        async with self._http_session.get(f"{self._base_url}/Motors/AllProperties") as resp:
            json = await resp.json()
            self._motors = {
                m["Title"]: {"index": m["Index"], "target": m["TargetPositionInUnits"]}
                for m in json["Motors"]
            }

    async def update_state(self):
        while True:
            for info in self._motors.values():
                async with self._http_session.get(
                    f"{self._base_url}/Motors?id={info['index']}"
                ) as resp:
                    json = await resp.json()
                    info["position"] = json["ActualPositionInUnits"]
                    info["range"] = (
                        json["MinimalPositionInUnits"],
                        json["MaximalPositionInUnits"],
                    )

                    info["busy"] = (
                        json["ActualPosition"] != json["TargetPosition"]
                        or abs(json["TargetPositionInUnits"] - info.get("target", 0)) > 0.01
                        or json["IsHoming"]
                    )
            async with self._http_session.get(
                f"{self._base_url}/ShutterInterlock/IsShutterOpen"
            ) as resp:
                self._shutter_status = await resp.json()
            self._busy = (
                any(i.get("busy", True) for i in self._motors.values())
                or self._shutter_status != self._shutter_target
            )
            if not self._busy:
                await self._busy_sig.wait()
            else:
                await asyncio.sleep(0.01)

    def get_state(self):
        return {"motors": self._motors, "shutter": self._shutter_status}

    def is_motor_busy(self, motor):
        return self._motors[motor]["busy"]

    def get_motor_range(self, motor):
        return self._motors[motor]["range"]

    def get_motor_position(self, motor):
        return self._motors[motor]["position"]

    def set_motor_position(self, motor, position):
        self._busy = True
        self._motors[motor]["target"] = position
        self._motors[motor]["busy"] = True
        self._loop.create_task(
            self._http_session.put(
                f"{self._base_url}/Motors/TargetPositionInUnits?id={self._motors[motor]['index']}",
                json=position,
            )
        )

    def home_motor(self, motor):
        self._busy = True
        self._loop.create_task(self._home_motor(motor))

    async def _home_motor(self, motor):
        await self._http_session.post(
            f"{self._base_url}/Motors/Home?id={self._motors[motor]['index']}"
        )
        self._motors[motor]["busy"] = True
        while self.is_motor_busy(motor):
            self.logger.debug(f"Waiting because {motor} is busy")
            await asyncio.sleep(0.001)
        self.logger.debug(f"resetting {motor} shutter to {self._shutter_target}")
        self.set_shutter(self._shutter_target)

    def get_shutter(self):
        return self._shutter_status

    def set_shutter(self, state):
        self._busy = True
        self._shutter_target = state
        self._loop.create_task(
            self._http_session.put(
                f"{self._base_url}/ShutterInterlock/OpenCloseShutter", json=bool(state)
            )
        )
