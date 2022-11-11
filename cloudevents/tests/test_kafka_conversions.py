#  Copyright 2018-Present The CloudEvents Authors
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64
import datetime
import json

import pytest

from cloudevents import exceptions as cloud_exceptions
from cloudevents.http import CloudEvent
from cloudevents.kafka.conversion import (
    KafkaMessage,
    from_binary,
    from_structured,
    to_binary,
    to_structured,
)
from cloudevents.sdk import types

expected_data = {"name": "test", "amount": 1}


# simple serdes for testing marshallers
def _serialize(data: dict) -> bytes:
    return bytes(json.dumps(data).encode("utf-8"))


def _deserialize(data: bytes) -> dict:
    return json.loads(data.decode())


@pytest.fixture
def source_event() -> CloudEvent:
    return CloudEvent.create(
        attributes={
            "specversion": "1.0",
            "id": "1234-1234-1234",
            "source": "pytest",
            "type": "com.pytest.test",
            "time": datetime.datetime(2000, 1, 1, 6, 42, 33).isoformat(),
            "content-type": "foo",
            "key": "test_key_123",
        },
        data=expected_data,
    )


@pytest.fixture
def source_binary_json_message() -> KafkaMessage:
    return KafkaMessage(
        headers={
            "ce_specversion": "1.0".encode("utf-8"),
            "ce_id": "1234-1234-1234".encode("utf-8"),
            "ce_source": "pytest".encode("utf-8"),
            "ce_type": "com.pytest.test".encode("utf-8"),
            "ce_time": datetime.datetime(2000, 1, 1, 6, 42, 33)
            .isoformat()
            .encode("utf-8"),
            "content-type": "foo".encode("utf-8"),
        },
        value=json.dumps(expected_data).encode("utf-8"),
        key="test_key_123",
    )


@pytest.fixture
def source_binary_bytes_message() -> KafkaMessage:
    return KafkaMessage(
        headers={
            "ce_specversion": "1.0".encode("utf-8"),
            "ce_id": "1234-1234-1234".encode("utf-8"),
            "ce_source": "pytest".encode("utf-8"),
            "ce_type": "com.pytest.test".encode("utf-8"),
            "ce_time": datetime.datetime(2000, 1, 1, 6, 42, 33)
            .isoformat()
            .encode("utf-8"),
            "content-type": "foo".encode("utf-8"),
        },
        value=_serialize(expected_data),
        key="test_key_123",
    )


@pytest.fixture
def source_structured_json_message() -> KafkaMessage:
    return KafkaMessage(
        headers={
            "content-type": "foo".encode("utf-8"),
        },
        value=json.dumps(
            {
                "specversion": "1.0",
                "id": "1234-1234-1234",
                "source": "pytest",
                "type": "com.pytest.test",
                "time": datetime.datetime(2000, 1, 1, 6, 42, 33).isoformat(),
                "data": expected_data,
            }
        ).encode("utf-8"),
        key="test_key_123",
    )


@pytest.fixture
def source_structured_json_bytes_message() -> KafkaMessage:
    return KafkaMessage(
        headers={
            "content-type": "foo".encode("utf-8"),
        },
        value=json.dumps(
            {
                "specversion": "1.0",
                "id": "1234-1234-1234",
                "source": "pytest",
                "type": "com.pytest.test",
                "time": datetime.datetime(2000, 1, 1, 6, 42, 33).isoformat(),
                "data_base64": base64.b64encode(_serialize(expected_data)).decode(
                    "ascii"
                ),
            }
        ).encode("utf-8"),
        key="test_key_123",
    )


@pytest.fixture
def source_structured_bytes_bytes_message() -> KafkaMessage:
    return KafkaMessage(
        headers={
            "content-type": "foo".encode("utf-8"),
        },
        value=_serialize(
            {
                "specversion": "1.0",
                "id": "1234-1234-1234",
                "source": "pytest",
                "type": "com.pytest.test",
                "time": datetime.datetime(2000, 1, 1, 6, 42, 33).isoformat(),
                "data_base64": base64.b64encode(_serialize(expected_data)).decode(
                    "ascii"
                ),
            }
        ),
        key="test_key_123",
    )


@pytest.fixture
def custom_marshaller() -> types.MarshallerType:
    return _serialize


@pytest.fixture
def custom_unmarshaller() -> types.MarshallerType:
    return _deserialize


def _throw():
    raise Exception("fail")


@pytest.fixture
def bad_marshaller() -> types.MarshallerType:
    return _throw


# sanity check for tests that use custom marshalling
def test_custom_marshaller_can_talk_to_itself(custom_marshaller, custom_unmarshaller):
    data = expected_data
    marshalled = custom_marshaller(data)
    unmarshalled = custom_unmarshaller(marshalled)
    for k, v in data.items():
        assert unmarshalled[k] == v


def test_throw_raises():
    with pytest.raises(Exception):
        _throw()


def test_to_binary_sets_value_default_marshaller(source_event):
    result = to_binary(source_event)
    assert result.value == json.dumps(source_event.data).encode("utf-8")


def test_to_binary_sets_value_custom_marshaller(source_event, custom_marshaller):
    result = to_binary(source_event, data_marshaller=custom_marshaller)
    assert result.value == custom_marshaller(source_event.data)


def test_to_binary_sets_key(source_event):
    result = to_binary(source_event)
    assert result.key == source_event["key"]


def test_to_binary_none_key(source_event):
    source_event["key"] = None
    result = to_binary(source_event)
    assert result.key is None


def test_to_binary_no_key(source_event):
    del source_event["key"]
    result = to_binary(source_event)
    assert result.key is None


def test_to_binary_sets_headers(source_event):
    result = to_binary(source_event)
    assert result.headers["ce_id"] == source_event["id"].encode("utf-8")
    assert result.headers["ce_specversion"] == source_event["specversion"].encode(
        "utf-8"
    )
    assert result.headers["ce_source"] == source_event["source"].encode("utf-8")
    assert result.headers["ce_type"] == source_event["type"].encode("utf-8")
    assert result.headers["ce_time"] == source_event["time"].encode("utf-8")
    assert result.headers["content-type"] == source_event["content-type"].encode(
        "utf-8"
    )
    assert "data" not in result.headers
    assert "key" not in result.headers


def test_to_binary_raise_marshaller_exception(source_event, bad_marshaller):
    with pytest.raises(cloud_exceptions.DataMarshallerError):
        to_binary(source_event, data_marshaller=bad_marshaller)


def test_from_binary_default_marshaller(source_binary_json_message):
    result = from_binary(source_binary_json_message)
    assert result.data == json.loads(source_binary_json_message.value.decode())


def test_from_binary_custom_marshaller(
    source_binary_bytes_message, custom_unmarshaller
):
    result = from_binary(
        source_binary_bytes_message, data_unmarshaller=custom_unmarshaller
    )
    assert result.data == custom_unmarshaller(source_binary_bytes_message.value)


def test_from_binary_sets_key(source_binary_json_message):
    result = from_binary(source_binary_json_message)
    assert result["key"] == source_binary_json_message.key


def test_from_binary_no_key(source_binary_json_message):
    keyless_message = KafkaMessage(
        headers=source_binary_json_message.headers,
        key=None,
        value=source_binary_json_message.value,
    )
    result = from_binary(keyless_message)
    assert "key" not in result.get_attributes()


def test_from_binary_sets_attrs_from_headers(source_binary_json_message):
    result = from_binary(source_binary_json_message)
    assert result["id"] == source_binary_json_message.headers["ce_id"].decode()
    assert (
        result["specversion"]
        == source_binary_json_message.headers["ce_specversion"].decode()
    )
    assert result["source"] == source_binary_json_message.headers["ce_source"].decode()
    assert result["type"] == source_binary_json_message.headers["ce_type"].decode()
    assert result["time"] == source_binary_json_message.headers["ce_time"].decode()
    assert (
        result["content-type"]
        == source_binary_json_message.headers["content-type"].decode()
    )


def test_from_binary_unmarshaller_exception(source_binary_json_message, bad_marshaller):
    with pytest.raises(cloud_exceptions.DataUnmarshallerError):
        from_binary(source_binary_json_message, data_unmarshaller=bad_marshaller)


def test_binary_can_talk_to_itself(source_event):
    message = to_binary(source_event)
    event = from_binary(message)
    for key, val in source_event.get_attributes().items():
        assert event[key] == val
    for key, val in source_event.data.items():
        assert event.data[key] == val


def test_binary_can_talk_to_itself_custom_marshaller(
    source_event, custom_marshaller, custom_unmarshaller
):
    message = to_binary(source_event, data_marshaller=custom_marshaller)
    event = from_binary(message, data_unmarshaller=custom_unmarshaller)
    for key, val in source_event.get_attributes().items():
        assert event[key] == val
    for key, val in source_event.data.items():
        assert event.data[key] == val


def test_to_structured_sets_value_default_marshallers(source_event):
    result = to_structured(source_event)
    assert result.value == json.dumps(
        {
            "specversion": source_event["specversion"],
            "id": source_event["id"],
            "source": source_event["source"],
            "type": source_event["type"],
            "time": source_event["time"],
            "data": expected_data,
        }
    ).encode("utf-8")


def test_to_structured_sets_value_custom_data_marshaller_default_envelope(
    source_event, custom_marshaller
):
    result = to_structured(source_event, data_marshaller=custom_marshaller)
    assert result.value == json.dumps(
        {
            "specversion": source_event["specversion"],
            "id": source_event["id"],
            "source": source_event["source"],
            "type": source_event["type"],
            "time": source_event["time"],
            "data_base64": base64.b64encode(custom_marshaller(expected_data)).decode(
                "ascii"
            ),
        }
    ).encode("utf-8")


def test_to_structured_sets_value_custom_envelope_marshaller(
    source_event, custom_marshaller
):
    result = to_structured(source_event, envelope_marshaller=custom_marshaller)
    assert result.value == custom_marshaller(
        {
            "specversion": source_event["specversion"],
            "id": source_event["id"],
            "source": source_event["source"],
            "type": source_event["type"],
            "time": source_event["time"],
            "data": expected_data,
        }
    )


def test_to_structured_sets_value_custom_marshallers(source_event, custom_marshaller):
    result = to_structured(
        source_event,
        data_marshaller=custom_marshaller,
        envelope_marshaller=custom_marshaller,
    )
    assert result.value == custom_marshaller(
        {
            "specversion": source_event["specversion"],
            "id": source_event["id"],
            "source": source_event["source"],
            "type": source_event["type"],
            "time": source_event["time"],
            "data_base64": base64.b64encode(custom_marshaller(expected_data)).decode(
                "ascii"
            ),
        }
    )


def test_to_structured_sets_key(source_event):
    result = to_structured(source_event)
    assert result.key == source_event["key"]


def test_to_structured_none_key(source_event):
    source_event["key"] = None
    result = to_structured(source_event)
    assert result.key is None


def test_to_structured_no_key(source_event):
    del source_event["key"]
    result = to_structured(source_event)
    assert result.key is None


def test_to_structured_sets_headers(source_event):
    result = to_structured(source_event)
    assert len(result.headers) == 1
    assert result.headers["content-type"] == source_event["content-type"].encode(
        "utf-8"
    )


def test_to_structured_datamarshaller_exception(source_event, bad_marshaller):
    with pytest.raises(cloud_exceptions.DataMarshallerError):
        to_structured(source_event, data_marshaller=bad_marshaller)


def test_to_structured_envelope_datamarshaller_exception(source_event, bad_marshaller):
    with pytest.raises(cloud_exceptions.DataMarshallerError):
        to_structured(source_event, envelope_marshaller=bad_marshaller)


def test_structured_can_talk_to_itself(source_event):
    message = to_structured(source_event)
    event = from_structured(message)
    for key, val in source_event.get_attributes().items():
        assert event[key] == val
    for key, val in source_event.data.items():
        assert event.data[key] == val


def test_from_structured_sets_data_default_data_unmarshaller(
    source_structured_json_message,
):
    result = from_structured(source_structured_json_message)
    assert result.data == expected_data


def test_from_structured_sets_data_custom_data_unmarshaller(
    source_structured_json_bytes_message, custom_unmarshaller
):
    result = from_structured(
        source_structured_json_bytes_message, data_unmarshaller=custom_unmarshaller
    )
    assert result.data == expected_data


def test_from_structured_sets_data_custom_unmarshallers(
    source_structured_bytes_bytes_message, custom_unmarshaller
):
    result = from_structured(
        source_structured_bytes_bytes_message,
        data_unmarshaller=custom_unmarshaller,
        envelope_unmarshaller=custom_unmarshaller,
    )
    assert result.data == expected_data


def test_from_structured_sets_attrs_default_enveloper_unmarshaller(
    source_structured_json_message,
):
    result = from_structured(source_structured_json_message)
    for key, value in json.loads(source_structured_json_message.value.decode()).items():
        if key != "data":
            assert result[key] == value


def test_from_structured_sets_attrs_custom_enveloper_unmarshaller(
    source_structured_bytes_bytes_message,
    custom_unmarshaller,
):
    result = from_structured(
        source_structured_bytes_bytes_message,
        data_unmarshaller=custom_unmarshaller,
        envelope_unmarshaller=custom_unmarshaller,
    )
    for key, value in custom_unmarshaller(
        source_structured_bytes_bytes_message.value
    ).items():
        if key not in ["data_base64"]:
            assert result[key] == value


def test_from_structured_sets_content_type_default_envelope_unmarshaller(
    source_structured_json_message,
):
    result = from_structured(source_structured_json_message)
    assert (
        result["content-type"]
        == source_structured_json_message.headers["content-type"].decode()
    )


def test_from_structured_sets_content_type_custom_envelope_unmarshaller(
    source_structured_bytes_bytes_message, custom_unmarshaller
):
    result = from_structured(
        source_structured_bytes_bytes_message,
        data_unmarshaller=custom_unmarshaller,
        envelope_unmarshaller=custom_unmarshaller,
    )
    assert (
        result["content-type"]
        == source_structured_bytes_bytes_message.headers["content-type"].decode()
    )


def test_from_structured_data_unmarshaller_exception(
    source_structured_bytes_bytes_message, custom_unmarshaller, bad_marshaller
):
    with pytest.raises(cloud_exceptions.DataUnmarshallerError):
        from_structured(
            source_structured_bytes_bytes_message,
            data_unmarshaller=bad_marshaller,
            envelope_unmarshaller=custom_unmarshaller,
        )


def test_from_structured_envelope_unmarshaller_exception(
    source_structured_bytes_bytes_message, bad_marshaller
):
    with pytest.raises(cloud_exceptions.DataUnmarshallerError):
        from_structured(
            source_structured_bytes_bytes_message,
            envelope_unmarshaller=bad_marshaller,
        )
