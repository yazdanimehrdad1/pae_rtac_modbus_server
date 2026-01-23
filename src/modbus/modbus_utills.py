#This class takes a modbus client and will define series of function that base on the functions input do different types of polling and return raw modbus points
from typing import List, Union

from config import settings
from modbus.client import ModbusClient
class ModbusUtils:
    def __init__(self, modbus_client: ModbusClient):
        self.modbus_client = modbus_client


    def read_holding_registers(self, address: int, count: int, server_id: int, host: str, port: int) -> List[Union[int, bool]]:
        return self.modbus_client.read_registers(kind="holding", address=address, count=count, server_id=server_id, host=host, port=port)

    def read_input_registers(self, address: int, count: int, server_id: int, host: str, port: int) -> List[Union[int, bool]]:
        return self.modbus_client.read_registers(kind="input", address=address, count=count, server_id=server_id, host=host, port=port)

    def read_coils(self, address: int, count: int, server_id: int, host: str, port: int) -> List[Union[int, bool]]:
        return self.modbus_client.read_registers(kind="coils", address=address, count=count, server_id=server_id, host=host, port=port)

    def read_discrete_inputs(self, address: int, count: int, server_id: int, host: str, port: int) -> List[Union[int, bool]]:
        return self.modbus_client.read_registers(kind="discretes", address=address, count=count, server_id=server_id, host=host, port=port)
    # TODO: use config instead of hard coded address and count
    # TODO: if more than 125 holding register, it should be handled here
    def read_device_registers_main_sel_751(self) -> List[Union[int, bool]]:
        return self.modbus_client.read_registers(kind=settings.main_sel_751_poll_kind,
            address=settings.main_sel_751_poll_address,
            count=settings.main_sel_751_poll_count,
            server_id=settings.main_sel_751_poll_device_id,
            host=settings.modbus_host,
            port=settings.modbus_port)
