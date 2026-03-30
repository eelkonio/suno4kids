"""
Unit tests for SchoolRegistry.
Tests specific examples and edge cases for credential management and persistence.
"""
import json
import os
import tempfile
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from backend.school_registry import SchoolRegistry


@pytest.fixture
def tmp_registry(tmp_path):
    """Create a SchoolRegistry with a temp file path."""
    path = tmp_path / "schools.json"
    return SchoolRegistry(registry_path=str(path))


@pytest.fixture
def populated_registry(tmp_path):
    """Create a registry pre-populated with test data."""
    path = tmp_path / "schools.json"
    data = {
        "admin_username": "eelko",
        "global_settings": {"default_max_projects_per_profile": 10},
        "schools": {
            "suno4kids": {
                "password_hash": generate_password_hash("nutsschool"),
                "created_at": "2025-01-15T10:30:00",
            },
            "eelko": {
                "password_hash": generate_password_hash("superhacker"),
                "created_at": "2025-01-15T10:30:00",
            },
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return SchoolRegistry(registry_path=str(path))


class TestLoad:
    def test_load_returns_empty_when_no_file(self, tmp_registry):
        data = tmp_registry.load()
        assert data["schools"] == {}
        assert "admin_username" in data

    def test_load_reads_existing_file(self, populated_registry):
        data = populated_registry.load()
        assert "suno4kids" in data["schools"]
        assert "eelko" in data["schools"]
        assert data["admin_username"] == "eelko"

    def test_load_falls_back_on_corrupted_json(self, tmp_path, monkeypatch):
        path = tmp_path / "schools.json"
        path.write_text("{invalid json!!!", encoding="utf-8")
        monkeypatch.setenv("AUTH_USERS", "testuser:testpass")
        monkeypatch.setenv("ADMIN_USERNAME", "testadmin")
        registry = SchoolRegistry(registry_path=str(path))
        data = registry.load()
        assert "testuser" in data["schools"]
        assert data["admin_username"] == "testadmin"

    def test_load_falls_back_on_invalid_structure(self, tmp_path, monkeypatch):
        path = tmp_path / "schools.json"
        path.write_text(json.dumps({"no_schools_key": True}), encoding="utf-8")
        monkeypatch.setenv("AUTH_USERS", "fallback:pass123")
        monkeypatch.setenv("ADMIN_USERNAME", "admin")
        registry = SchoolRegistry(registry_path=str(path))
        data = registry.load()
        assert "fallback" in data["schools"]


class TestSave:
    def test_save_persists_to_disk(self, tmp_registry):
        tmp_registry._data = {
            "admin_username": "admin",
            "global_settings": {"default_max_projects_per_profile": 5},
            "schools": {},
        }
        tmp_registry.save()
        assert tmp_registry.registry_path.exists()
        with open(tmp_registry.registry_path, "r") as f:
            loaded = json.load(f)
        assert loaded["admin_username"] == "admin"

    def test_save_with_explicit_data(self, tmp_registry):
        data = {
            "admin_username": "test",
            "global_settings": {},
            "schools": {"school1": {"password_hash": "x", "created_at": "now"}},
        }
        tmp_registry.save(data)
        with open(tmp_registry.registry_path, "r") as f:
            loaded = json.load(f)
        assert "school1" in loaded["schools"]


class TestInitializeFromEnv:
    def test_creates_registry_from_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AUTH_USERS", "school1:pass1,school2:pass2")
        monkeypatch.setenv("ADMIN_USERNAME", "myadmin")
        monkeypatch.setenv("MAX_PROJECTS_PER_PROFILE", "15")
        path = tmp_path / "schools.json"
        registry = SchoolRegistry(registry_path=str(path))
        registry.initialize_from_env()
        data = registry.load()
        assert data["admin_username"] == "myadmin"
        assert "school1" in data["schools"]
        assert "school2" in data["schools"]
        assert data["global_settings"]["default_max_projects_per_profile"] == 15

    def test_skips_if_file_exists(self, populated_registry):
        # Should not overwrite existing file
        populated_registry.initialize_from_env()
        data = populated_registry.load()
        assert "suno4kids" in data["schools"]


class TestValidateCredentials:
    def test_valid_credentials(self, populated_registry):
        assert populated_registry.validate_credentials("suno4kids", "nutsschool") is True

    def test_invalid_password(self, populated_registry):
        assert populated_registry.validate_credentials("suno4kids", "wrongpass") is False

    def test_unknown_user(self, populated_registry):
        assert populated_registry.validate_credentials("nonexistent", "pass") is False


class TestAddSchool:
    def test_add_new_school(self, populated_registry):
        populated_registry.add_school("newschool", "newpass123")
        assert populated_registry.validate_credentials("newschool", "newpass123") is True

    def test_add_duplicate_raises(self, populated_registry):
        with pytest.raises(ValueError, match="already exists"):
            populated_registry.add_school("suno4kids", "anypass")

    def test_add_school_persists(self, populated_registry):
        populated_registry.add_school("persistent", "pass")
        # Reload from disk
        fresh = SchoolRegistry(registry_path=str(populated_registry.registry_path))
        data = fresh.load()
        assert "persistent" in data["schools"]


class TestUpdatePassword:
    def test_update_password(self, populated_registry):
        populated_registry.update_password("suno4kids", "newpassword")
        assert populated_registry.validate_credentials("suno4kids", "newpassword") is True
        assert populated_registry.validate_credentials("suno4kids", "nutsschool") is False

    def test_update_nonexistent_raises(self, populated_registry):
        with pytest.raises(ValueError, match="not found"):
            populated_registry.update_password("ghost", "pass")


class TestDeleteSchool:
    def test_delete_school(self, populated_registry):
        populated_registry.delete_school("suno4kids")
        schools = populated_registry.list_schools()
        usernames = [s["username"] for s in schools]
        assert "suno4kids" not in usernames

    def test_delete_admin_raises(self, populated_registry):
        with pytest.raises(ValueError, match="Cannot delete the admin"):
            populated_registry.delete_school("eelko")

    def test_delete_nonexistent_raises(self, populated_registry):
        with pytest.raises(ValueError, match="not found"):
            populated_registry.delete_school("ghost")


class TestListSchools:
    def test_list_schools(self, populated_registry):
        schools = populated_registry.list_schools()
        usernames = [s["username"] for s in schools]
        assert "suno4kids" in usernames
        assert "eelko" in usernames
        for school in schools:
            assert "created_at" in school


class TestAdminAndSettings:
    def test_get_admin_username(self, populated_registry):
        assert populated_registry.get_admin_username() == "eelko"

    def test_get_global_settings(self, populated_registry):
        settings = populated_registry.get_global_settings()
        assert settings["default_max_projects_per_profile"] == 10

    def test_update_global_settings(self, populated_registry):
        populated_registry.update_global_settings(
            {"default_max_projects_per_profile": 20}
        )
        settings = populated_registry.get_global_settings()
        assert settings["default_max_projects_per_profile"] == 20


class TestDirectoryCreation:
    def test_creates_data_dir(self, tmp_path):
        nested = tmp_path / "deep" / "nested" / "schools.json"
        registry = SchoolRegistry(registry_path=str(nested))
        assert nested.parent.exists()
