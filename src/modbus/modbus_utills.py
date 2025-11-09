#This class takes a modbus client and will define series of function that base on the functions input do different types of polling and return raw modbus points
from typing import List, Union

from config import settings
from modbus.client import ModbusClient
class ModbusUtils:
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client


    def read_holding_registers(self, address: int, count: int, unit_id: int) -> List[Union[int, bool]]:
        return self.modbus_client.read_registers(kind="holding", address=address, count=count, unit_id=unit_id)

    # TODO: use config instead of hard coded address and count
    def read_device_registers_main_sel_751(self) -> List[Union[int, bool]]:
        return self.modbus_client.read_registers(kind=settings.main_sel_751_poll_kind,
            address=settings.main_sel_751_poll_address,
            count=settings.main_sel_751_poll_count,
            unit_id=settings.main_sel_751_poll_unit_id)
