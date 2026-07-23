"""
Unit tests for device point data_type handling.

Guards the invariant that the `DataType` Literal accepted by the API and the decode
branches in `_decode_modbus_point_value` cannot drift apart. Drift is silent in
production: an unsupported data_type decodes to BAD_DATA_TYPE, stores a null reading
every poll, and the endpoint hides it via response_model_exclude_none.
"""

import pytest
from pydantic import ValidationError

from helpers.device_points.device_standardized_points import _STANDARDIZED_POINTS
from helpers.modbus.modbus_data_mapping import _decode_modbus_point_value
from helpers.reads.calculate_reads import translate_reading
from schemas.api_models.requests import DeviceCreateRequest, DevicePointCreateRequest
from schemas.api_models.types import (
    register_size,
    SUPPORTED_DATA_TYPES,
    SUPPORTED_DEVICE_TYPES,
    SUPPORTED_NUMERIC_DATA_TYPES,
)

# Register count each type needs: 16-bit -> 1, 32-bit -> 2, 64-bit -> 4.
REGISTERS_FOR_TYPE = {
    "bool": 1,
    "uint16": 1,
    "int16": 1,
    "raw": 1,
    "enum16": 1,
    "bitfield16": 1,
    "status_word16": 1,
    "uint32": 2,
    "int32": 2,
    "float32": 2,
    "enum32": 2,
    "bitfield32": 2,
    "status_word32": 2,
    "uint64": 4,
    "int64": 4,
    "float64": 4,
}


class TestLiteralComposition:
    """
    Guards the nested-Literal flattening in types.py. If PEP 586 flattening ever stops
    applying, get_args() returns Literal objects instead of strings and these sets go
    silently wrong — taking every other check in this file with them.
    """

    def test_set_sizes(self):
        assert len(SUPPORTED_NUMERIC_DATA_TYPES) == 10
        assert len(SUPPORTED_DATA_TYPES) == 16
        assert len(SUPPORTED_DEVICE_TYPES) == 10

    def test_all_members_are_strings(self):
        for value in SUPPORTED_DATA_TYPES | SUPPORTED_DEVICE_TYPES:
            assert isinstance(value, str)

    def test_numeric_is_a_subset_of_full(self):
        assert SUPPORTED_NUMERIC_DATA_TYPES < SUPPORTED_DATA_TYPES
        assert SUPPORTED_DATA_TYPES - SUPPORTED_NUMERIC_DATA_TYPES == {
            "enum16",
            "enum32",
            "bitfield16",
            "bitfield32",
            "status_word16",
            "status_word32",
        }


class TestRegisterSize:
    """register_size is the single source of width truth; it must cover the vocabulary."""

    def test_covers_every_supported_type(self):
        assert {t: register_size(t) for t in SUPPORTED_DATA_TYPES}.keys() == SUPPORTED_DATA_TYPES

    def test_matches_test_fixture(self):
        for data_type in SUPPORTED_DATA_TYPES:
            assert register_size(data_type) == REGISTERS_FOR_TYPE[data_type]

    def test_width_suffix_drives_size(self):
        assert register_size("enum16") == 1
        assert register_size("enum32") == 2
        assert register_size("bitfield16") == 1
        assert register_size("bitfield32") == 2
        assert register_size("status_word16") == 1
        assert register_size("status_word32") == 2


class TestDataTypeDecoding:
    def test_every_supported_type_has_a_register_width(self):
        """REGISTERS_FOR_TYPE must cover the Literal, or the test below silently skips."""
        assert set(REGISTERS_FOR_TYPE) == set(SUPPORTED_DATA_TYPES)

    @pytest.mark.parametrize("data_type", sorted(SUPPORTED_DATA_TYPES))
    def test_supported_type_decodes(self, data_type: str):
        """Every type the API accepts must decode, or points using it store nulls forever."""
        result = _decode_modbus_point_value(
            register_values=[1] * REGISTERS_FOR_TYPE[data_type],
            data_type=data_type,
        )
        assert result.success is True, f"{data_type}: {result.quality} — {result.reason}"
        assert result.value is not None

    @pytest.mark.parametrize("data_type", ["enum", "bitfield", "status_word", "int24", ""])
    def test_unsupported_type_is_rejected_by_decoder(self, data_type: str):
        """Bare enum/bitfield/status_word were replaced by width-suffixed variants."""
        result = _decode_modbus_point_value(register_values=[1], data_type=data_type)
        assert result.success is False
        assert result.quality == "BAD_DATA_TYPE"


class TestDataTypeValidation:
    def _payload(self, data_type: str, size: int) -> dict:
        return {
            "name": "test_point",
            "poll_kind": "holding",
            "address": 1400,
            "size": size,
            "data_type": data_type,
        }

    @pytest.mark.parametrize("data_type", sorted(SUPPORTED_DATA_TYPES))
    def test_supported_type_accepted(self, data_type: str):
        payload = self._payload(data_type, register_size(data_type))
        assert DevicePointCreateRequest(**payload).data_type == data_type

    @pytest.mark.parametrize("data_type", ["enum", "bitfield", "status_word", "INT32", "bogus"])
    def test_unsupported_type_rejected(self, data_type: str):
        """Bare enum/bitfield/status_word no longer exist; wrong casing is also rejected."""
        with pytest.raises(ValidationError):
            DevicePointCreateRequest(**self._payload(data_type, 1))

    def test_size_must_match_type_width(self):
        """enum32 needs 2 registers; supplying size=1 is rejected."""
        with pytest.raises(ValidationError):
            DevicePointCreateRequest(**self._payload("enum32", 1))
        with pytest.raises(ValidationError):
            DevicePointCreateRequest(**self._payload("int32", 1))

    def test_size_matching_type_width_accepted(self):
        assert DevicePointCreateRequest(**self._payload("enum32", 2)).size == 2
        assert DevicePointCreateRequest(**self._payload("bitfield16", 1)).size == 1


class TestDeviceType:
    """
    Guards the device-type vocabulary against the registry it feeds. The original bug:
    'meter'/'RTAC' were accepted but matched no registry key (0 standardized points,
    silently), while ES/PV/GENERATOR/LOADBANK/IED had templates the API rejected outright.
    """

    # Valid device types that intentionally have no standardized-point templates yet.
    NO_TEMPLATE_YET = {"METER", "RTAC"}

    def test_every_device_type_has_templates_or_is_explicitly_exempt(self):
        for device_type in SUPPORTED_DEVICE_TYPES:
            assert device_type in _STANDARDIZED_POINTS or device_type in self.NO_TEMPLATE_YET, (
                f"{device_type} is accepted but generates no standardized points. "
                f"Add templates, or add it to NO_TEMPLATE_YET deliberately."
            )

    def test_every_template_is_reachable(self):
        """A template whose key the API rejects can never be used."""
        for registry_key in _STANDARDIZED_POINTS:
            assert registry_key in SUPPORTED_DEVICE_TYPES, (
                f"{registry_key} has standardized points but is not an accepted device type."
            )

    def test_exempt_types_really_have_no_templates(self):
        """Keeps NO_TEMPLATE_YET honest once templates are added."""
        for device_type in self.NO_TEMPLATE_YET:
            assert device_type not in _STANDARDIZED_POINTS

    def _payload(self, device_type: str) -> dict:
        return {"name": "test_device", "type": device_type, "host": "127.0.0.1"}

    @pytest.mark.parametrize("given", ["relay", "RELAY", "Relay", "rElAy"])
    def test_casing_is_normalized(self, given: str):
        assert DeviceCreateRequest(**self._payload(given)).type == "RELAY"

    @pytest.mark.parametrize("device_type", sorted(SUPPORTED_DEVICE_TYPES))
    def test_every_supported_device_type_accepted(self, device_type: str):
        assert DeviceCreateRequest(**self._payload(device_type)).type == device_type

    @pytest.mark.parametrize("device_type", ["bogus", "SOLAR", ""])
    def test_unsupported_device_type_rejected(self, device_type: str):
        with pytest.raises(ValidationError):
            DeviceCreateRequest(**self._payload(device_type))


class TestEnumTranslation:
    ENUM_DETAIL = {"0": "OFF", "1": "ON", "2": "ERROR", "3": "HEALTHY"}

    def test_enum_point_decodes_then_translates(self):
        """The enum bug end to end: with a supported type, the label comes through."""
        decoded = _decode_modbus_point_value(register_values=[3], data_type="enum16")
        assert decoded.success is True
        assert translate_reading(decoded.value, None, self.ENUM_DETAIL) == "HEALTHY"

    def test_null_reading_translates_to_none(self):
        """A failed decode stores None, and no enum_detail can rescue it."""
        assert translate_reading(None, None, self.ENUM_DETAIL) is None
