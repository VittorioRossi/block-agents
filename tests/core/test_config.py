"""Tests for the Config class."""

import os
import tempfile
from unittest import mock

import pytest
import yaml

from block_agents.core.config import Config
from block_agents.core.errors import ConfigurationError


def test_config_defaults():
    """Test that Config loads default values."""
    config = Config({})
    assert config.get("log_level") is None
    assert config.get("non_existent_key") is None
    assert config.get("non_existent_key", "default") == "default"


def test_config_get():
    """Test the get method of Config."""
    config_dict = {
        "log_level": "info",
        "nested": {
            "key1": "value1",
            "key2": {
                "subkey": "subvalue"
            }
        }
    }
    config = Config(config_dict)

    assert config.get("log_level") == "info"
    assert config.get("nested.key1") == "value1"
    assert config.get("nested.key2.subkey") == "subvalue"
    assert config.get("non_existent") is None
    assert config.get("nested.non_existent") is None
    assert config.get("nested.key2.non_existent") is None


def test_config_load_from_dict():
    """Test loading a Config from a dictionary."""
    config_dict = {
        "log_level": "info",
        "max_pipeline_runtime_seconds": 7200,
    }
    config = Config(config_dict)

    assert config.get("log_level") == "info"
    assert config.get("max_pipeline_runtime_seconds") == 7200


def test_config_as_dict():
    """Test the as_dict method of Config."""
    config_dict = {
        "log_level": "info",
        "nested": {"key": "value"}
    }
    config = Config(config_dict)

    result = config.as_dict()
    assert result == config_dict
    assert result is not config_dict  # Should be a copy


def test_config_deep_update():
    """Test the _deep_update method of Config."""
    target = {
        "a": 1,
        "b": {
            "c": 2,
            "d": 3
        }
    }
    source = {
        "b": {
            "c": 4,
            "e": 5
        },
        "f": 6
    }

    Config._deep_update(target, source)
    assert target == {
        "a": 1,
        "b": {
            "c": 4,
            "d": 3,
            "e": 5
        },
        "f": 6
    }


def test_config_resolve_env_vars():
    """Test the resolve_env_vars method of Config."""
    config = Config({})
    
    with mock.patch.dict(os.environ, {"TEST_VAR": "test_value"}):
        result = config.resolve_env_vars("Value: ${TEST_VAR}")
        assert result == "Value: test_value"
        
        # Test with non-string value
        assert config.resolve_env_vars(123) == 123