"""Device polling helper functions."""

from typing import List

from modbus.client import ModbusClient
from modbus.modbus_utills import ModbusUtils
from logger import get_logger
from schemas.api_models import DeviceListItem, ModbusRegisterValues, PollingConfig

logger = get_logger(__name__)

# Initialize services
edge_aggregator_modbus_client = ModbusClient()
edge_aggregator_modbus_utils = ModbusUtils(edge_aggregator_modbus_client)
direct_modbus_utils_by_endpoint: dict[tuple[str, int], ModbusUtils] = {}


def get_direct_modbus_utils(host: str, port: int) -> ModbusUtils:
    endpoint = (host, port)
    modbus_utils = direct_modbus_utils_by_endpoint.get(endpoint)
    if modbus_utils is None:
        modbus_utils = ModbusUtils(ModbusClient())
        direct_modbus_utils_by_endpoint[endpoint] = modbus_utils
    return modbus_utils


async def get_enabled_devices_to_poll(site_devices: List[DeviceListItem]) -> List[DeviceListItem]:
    """
    Get list of devices to poll from database, filtered by poll_enabled.

    Returns:
        List of devices that have polling enabled
    """
    devices_to_poll = []
    for device in site_devices:
        if device.poll_enabled:
            devices_to_poll.append(device)
            logger.debug(f"Device '{device.name}' (ID: {device.device_id}) has polling enabled")
        else:
            logger.debug(
                f"Device '{device.name}' (ID: {device.device_id}) has polling disabled "
                f"(poll_enabled={device.poll_enabled}), skipping"
            )

    logger.info(
        f"Found {len(devices_to_poll)} device(s) to poll out of {len(site_devices)} total device(s) "
    )
    return devices_to_poll


async def read_device_registers(
    device: DeviceListItem,
    polling_config: PollingConfig
) -> ModbusRegisterValues:
    """
    Read Modbus registers for a device using polling configuration.

    Args:
        device: Device to read from
        polling_config: Polling configuration (address, count, kind, device_id)

    Returns:
        List of raw register values from Modbus

    Raises:
        Exception: If Modbus read fails
    """
    address = polling_config.poll_address
    count = polling_config.poll_count
    kind = polling_config.poll_kind
    server_id = device.server_address
    host = device.host
    port = device.port

    logger.debug(
        f"Reading Modbus registers for device '{device.name}': "
        f"kind={kind}, address={address}, count={count}, server_address={server_id}"
    )

    if device.read_from_aggregator:
        modbus_utils = edge_aggregator_modbus_utils
        host = None
        port = None
    else:
        modbus_utils = get_direct_modbus_utils(host, port)

    if kind not in {"holding", "input", "coils", "discretes"}:
        raise ValueError(f"Invalid register kind: {kind}. Must be 'holding', 'input', 'coils', or 'discretes'")

    if kind == "holding":
        modbus_data = modbus_utils.read_holding_registers(
            address,
            count,
            server_id,
            host,
            port
        )
    elif kind == "input":
        modbus_data = modbus_utils.read_input_registers(
            address,
            count,
            server_id,
            host,
            port
        )
    elif kind == "coils":
        modbus_data = modbus_utils.read_coils(
            address,
            count,
            server_id,
            host,
            port
        )
    else:
        modbus_data = modbus_utils.read_discrete_inputs(
            address,
            count,
            server_id,
            host,
            port
        )

    logger.info(f"Successfully read {len(modbus_data)} registers from device '{device.name}'")
    return modbus_data
