"""
Unit tests for SchoolConfig and SchoolConfigManager.
Tests specific examples and edge cases for per-school configuration management.
"""
import json
from pathlib import Path

import pytest

from backend.school_config import SchoolConfig, SchoolConfigManager


@pytest.fixture
def manager(tmp_path):
    """Create a SchoolConfigManager with a temp base path."""
    return SchoolConfigManager(base_path=str(tmp_path))


@pytest.fixture
def populated_manager(tmp_path):
    """Create a manager with a pre-existing school config on disk."""
    mgr = SchoolConfigManager(base_path=str(tmp_path))
    config = SchoolConfig(
        class_name="Test Klas",
        logo_path="static/test_logo.png",
        max_projects_per_profile=5,
        anthropic_api_key="sk-ant-test1234",
        suno_api_key="suno-key-5678",
        google_api_key="AIzaSyTestKey9012",
    )
    mgr.save_config("testschool", config)
    return mgr


class TestSchoolConfigDefaults:
    def test_default_values(self):
        config = SchoolConfig()
        assert config.class_name == ""
        assert config.logo_path == ""
        assert config.max_projects_per_profile == 10
        assert config.anthropic_api_key is None
        assert config.suno_api_key is None
        assert config.google_api_key is None


class TestGetConfig:
    def test_returns_defaults_when_no_file(self, manager, monkeypatch):
        monkeypatch.setenv("CLASS_NAME", "Groep 5 en 6")
        monkeypatch.setenv("LOGO_PATH", "static/logo.png")
        monkeypatch.setenv("MAX_PROJECTS_PER_PROFILE", "10")
        config = manager.get_config("nonexistent")
        assert config.class_name == "Groep 5 en 6"
        assert config.logo_path == "static/logo.png"
        assert config.max_projects_per_profile == 10
        assert config.anthropic_api_key is None

    def test_loads_existing_config(self, populated_manager):
        config = populated_manager.get_config("testschool")
        assert config.class_name == "Test Klas"
        assert config.logo_path == "static/test_logo.png"
        assert config.max_projects_per_profile == 5
        assert config.anthropic_api_key == "sk-ant-test1234"
        assert config.suno_api_key == "suno-key-5678"
        assert config.google_api_key == "AIzaSyTestKey9012"

    def test_returns_defaults_on_corrupted_json(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLASS_NAME", "Fallback")
        monkeypatch.setenv("LOGO_PATH", "static/fallback.png")
        config_dir = tmp_path / "badschool"
        config_dir.mkdir()
        (config_dir / "config.json").write_text("{broken json!!!", encoding="utf-8")
        mgr = SchoolConfigManager(base_path=str(tmp_path))
        config = mgr.get_config("badschool")
        assert config.class_name == "Fallback"

    def test_normalizes_empty_api_keys_to_none(self, tmp_path):
        config_dir = tmp_path / "emptykeys"
        config_dir.mkdir()
        data = {
            "class_name": "Klas",
            "logo_path": "logo.png",
            "max_projects_per_profile": 10,
            "anthropic_api_key": "",
            "suno_api_key": "",
            "google_api_key": "",
        }
        (config_dir / "config.json").write_text(json.dumps(data), encoding="utf-8")
        mgr = SchoolConfigManager(base_path=str(tmp_path))
        config = mgr.get_config("emptykeys")
        assert config.anthropic_api_key is None
        assert config.suno_api_key is None
        assert config.google_api_key is None


class TestSaveConfig:
    def test_save_creates_directory_and_file(self, manager):
        config = SchoolConfig(class_name="New School", logo_path="logo.png")
        manager.save_config("newschool", config)
        path = Path(manager.base_path) / "newschool" / "config.json"
        assert path.exists()
        with open(path, "r") as f:
            data = json.load(f)
        assert data["class_name"] == "New School"

    def test_save_normalizes_empty_keys_to_null(self, manager):
        config = SchoolConfig(
            class_name="X",
            logo_path="y",
            anthropic_api_key="",
            suno_api_key="",
            google_api_key="",
        )
        manager.save_config("school", config)
        path = Path(manager.base_path) / "school" / "config.json"
        with open(path, "r") as f:
            data = json.load(f)
        assert data["anthropic_api_key"] is None
        assert data["suno_api_key"] is None
        assert data["google_api_key"] is None


class TestCreateDefaultConfig:
    def test_creates_config_with_env_defaults(self, manager, monkeypatch):
        monkeypatch.setenv("CLASS_NAME", "Groep 5 en 6")
        monkeypatch.setenv("LOGO_PATH", "static/logo.png")
        monkeypatch.setenv("MAX_PROJECTS_PER_PROFILE", "10")
        config = manager.create_default_config("fresh")
        assert config.class_name == "Groep 5 en 6"
        assert config.logo_path == "static/logo.png"
        assert config.max_projects_per_profile == 10
        assert config.anthropic_api_key is None
        # Verify persisted to disk
        loaded = manager.get_config("fresh")
        assert loaded.class_name == "Groep 5 en 6"

    def test_uses_hardcoded_defaults_when_no_env(self, manager, monkeypatch):
        monkeypatch.delenv("CLASS_NAME", raising=False)
        monkeypatch.delenv("LOGO_PATH", raising=False)
        monkeypatch.delenv("MAX_PROJECTS_PER_PROFILE", raising=False)
        config = manager.create_default_config("noenv")
        assert config.class_name == "Groep 5 en 6"
        assert config.logo_path == "static/logo.png"
        assert config.max_projects_per_profile == 10


class TestSetApiKey:
    def test_set_anthropic_key(self, manager):
        manager.create_default_config("school1")
        manager.set_api_key("school1", "anthropic", "sk-ant-newkey1234")
        config = manager.get_config("school1")
        assert config.anthropic_api_key == "sk-ant-newkey1234"

    def test_set_suno_key(self, manager):
        manager.create_default_config("school1")
        manager.set_api_key("school1", "suno", "suno-abc123")
        config = manager.get_config("school1")
        assert config.suno_api_key == "suno-abc123"

    def test_set_google_key(self, manager):
        manager.create_default_config("school1")
        manager.set_api_key("school1", "google", "AIzaSyXYZ")
        config = manager.get_config("school1")
        assert config.google_api_key == "AIzaSyXYZ"

    def test_set_empty_key_clears(self, populated_manager):
        populated_manager.set_api_key("testschool", "anthropic", "")
        config = populated_manager.get_config("testschool")
        assert config.anthropic_api_key is None

    def test_invalid_service_raises(self, manager):
        manager.create_default_config("school1")
        with pytest.raises(ValueError, match="Invalid service"):
            manager.set_api_key("school1", "openai", "key123")


class TestClearApiKey:
    def test_clear_existing_key(self, populated_manager):
        populated_manager.clear_api_key("testschool", "anthropic")
        config = populated_manager.get_config("testschool")
        assert config.anthropic_api_key is None

    def test_clear_already_none_key(self, manager):
        manager.create_default_config("school1")
        manager.clear_api_key("school1", "suno")
        config = manager.get_config("school1")
        assert config.suno_api_key is None

    def test_invalid_service_raises(self, manager):
        with pytest.raises(ValueError, match="Invalid service"):
            manager.clear_api_key("school1", "invalid")


class TestGetApiKeyStatus:
    def test_all_keys_set(self, populated_manager):
        status = populated_manager.get_api_key_status("testschool")
        assert status == {
            "anthropic": "Set",
            "suno": "Set",
            "google": "Set",
        }

    def test_no_keys_set(self, manager, monkeypatch):
        monkeypatch.delenv("CLASS_NAME", raising=False)
        manager.create_default_config("empty")
        status = manager.get_api_key_status("empty")
        assert status == {
            "anthropic": "Not set",
            "suno": "Not set",
            "google": "Not set",
        }

    def test_partial_keys(self, manager):
        config = SchoolConfig(
            class_name="X",
            logo_path="y",
            anthropic_api_key="sk-key",
        )
        manager.save_config("partial", config)
        status = manager.get_api_key_status("partial")
        assert status["anthropic"] == "Set"
        assert status["suno"] == "Not set"
        assert status["google"] == "Not set"


class TestGetApiKeyHint:
    def test_hint_for_long_key(self, populated_manager):
        hint = populated_manager.get_api_key_hint("testschool", "anthropic")
        assert hint == "1234"  # last 4 of "sk-ant-test1234"

    def test_hint_for_short_key(self, tmp_path):
        mgr = SchoolConfigManager(base_path=str(tmp_path))
        config = SchoolConfig(class_name="X", logo_path="y", suno_api_key="ab")
        mgr.save_config("short", config)
        hint = mgr.get_api_key_hint("short", "suno")
        assert hint == "ab"

    def test_hint_for_no_key(self, manager):
        manager.create_default_config("nokeys")
        hint = manager.get_api_key_hint("nokeys", "google")
        assert hint is None

    def test_hint_exactly_4_chars(self, tmp_path):
        mgr = SchoolConfigManager(base_path=str(tmp_path))
        config = SchoolConfig(class_name="X", logo_path="y", google_api_key="ABCD")
        mgr.save_config("exact4", config)
        hint = mgr.get_api_key_hint("exact4", "google")
        assert hint == "ABCD"

    def test_invalid_service_raises(self, manager):
        with pytest.raises(ValueError, match="Invalid service"):
            manager.get_api_key_hint("school", "invalid")
