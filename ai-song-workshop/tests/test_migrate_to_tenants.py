"""
Tests for the migration script migrate_to_tenants.py.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add parent directory to path so we can import the migration script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from migrate_to_tenants import (
    check_migration_complete,
    migrate,
    move_child_dirs,
    move_json_files,
    update_project_paths,
    write_marker,
)


@pytest.fixture
def temp_env(tmp_path, monkeypatch):
    """Create a temporary environment mimicking the project structure."""
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "profiles").mkdir()
    (storage / "projects").mkdir()

    # Create a script_dir with static dirs
    script_dir = tmp_path / "script"
    script_dir.mkdir()
    (script_dir / "static" / "audio").mkdir(parents=True)
    (script_dir / "static" / "images").mkdir(parents=True)
    (script_dir / "static" / "photos").mkdir(parents=True)
    (script_dir / "data").mkdir(parents=True)

    return {
        "tmp_path": tmp_path,
        "storage": storage,
        "script_dir": script_dir,
    }


def _create_profile(profiles_dir: Path, profile_id: str, name: str):
    data = {
        "id": profile_id,
        "name": name,
        "created_at": "2025-01-01T00:00:00",
        "project_ids": [],
    }
    (profiles_dir / f"{profile_id}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2)
    )


def _create_project(projects_dir: Path, project_id: str, profile_id: str,
                     song_path: str = "", image_path: str = ""):
    data = {
        "id": project_id,
        "profile_id": profile_id,
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
        "description": "test",
        "genre": "pop",
        "lyrics": "la la la",
        "song_file_path": song_path,
        "image_file_path": image_path,
        "lyrics_generated": True,
        "song_generated": bool(song_path),
        "image_generated": bool(image_path),
    }
    (projects_dir / f"{project_id}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2)
    )


class TestMoveJsonFiles:
    def test_moves_json_files(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"

        (src / "a.json").write_text('{"id": "a"}')
        (src / "b.json").write_text('{"id": "b"}')

        count = move_json_files(src, dest, dry_run=False)
        assert count == 2
        assert (dest / "a.json").exists()
        assert (dest / "b.json").exists()
        assert not (src / "a.json").exists()
        assert not (src / "b.json").exists()

    def test_skips_existing_at_destination(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"
        dest.mkdir()

        (src / "a.json").write_text('{"id": "a_src"}')
        (dest / "a.json").write_text('{"id": "a_dest"}')

        count = move_json_files(src, dest, dry_run=False)
        assert count == 0
        # Original at dest is preserved
        data = json.loads((dest / "a.json").read_text())
        assert data["id"] == "a_dest"

    def test_nonexistent_source_returns_zero(self, tmp_path):
        src = tmp_path / "nonexistent"
        dest = tmp_path / "dest"
        count = move_json_files(src, dest, dry_run=False)
        assert count == 0

    def test_dry_run_does_not_move(self, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        dest = tmp_path / "dest"

        (src / "a.json").write_text('{"id": "a"}')
        count = move_json_files(src, dest, dry_run=True)
        assert count == 1  # counted but not moved
        assert (src / "a.json").exists()
        assert not dest.exists()


class TestMoveChildDirs:
    def test_moves_child_directories(self, tmp_path):
        src = tmp_path / "audio"
        src.mkdir()
        child = src / "child_hash_abc"
        child.mkdir()
        (child / "song.mp3").write_text("audio data")

        dest = src / "suno4kids"
        count = move_child_dirs(src, dest, "suno4kids", dry_run=False)
        assert count == 1
        assert (dest / "child_hash_abc" / "song.mp3").exists()
        assert not (src / "child_hash_abc").exists()

    def test_skips_tenant_directory(self, tmp_path):
        src = tmp_path / "audio"
        src.mkdir()
        tenant_dir = src / "suno4kids"
        tenant_dir.mkdir()
        (tenant_dir / "existing.mp3").write_text("data")

        other = src / "other_dir"
        other.mkdir()

        dest = src / "suno4kids"
        count = move_child_dirs(src, dest, "suno4kids", dry_run=False)
        assert count == 1
        assert (dest / "other_dir").exists()

    def test_skips_hidden_files(self, tmp_path):
        src = tmp_path / "images"
        src.mkdir()
        (src / ".gitkeep").write_text("")
        child = src / "child_dir"
        child.mkdir()

        dest = src / "suno4kids"
        count = move_child_dirs(src, dest, "suno4kids", dry_run=False)
        assert count == 1
        assert (src / ".gitkeep").exists()  # not moved

    def test_moves_loose_files(self, tmp_path):
        """Loose non-hidden files should also be moved."""
        src = tmp_path / "images"
        src.mkdir()
        (src / "song_image_0_1358.png").write_text("image data")

        dest = src / "suno4kids"
        count = move_child_dirs(src, dest, "suno4kids", dry_run=False)
        assert count == 1
        assert (dest / "song_image_0_1358.png").exists()


class TestUpdateProjectPaths:
    def test_updates_paths(self, tmp_path):
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        _create_project(
            projects_dir, "p1", "prof1",
            song_path="audio/child_hash/song.mp3",
            image_path="images/child_hash/img.png",
        )

        count = update_project_paths(projects_dir, "suno4kids", dry_run=False)
        assert count == 1

        data = json.loads((projects_dir / "p1.json").read_text())
        assert data["song_file_path"] == "audio/suno4kids/child_hash/song.mp3"
        assert data["image_file_path"] == "images/suno4kids/child_hash/img.png"

    def test_skips_already_prefixed(self, tmp_path):
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        _create_project(
            projects_dir, "p1", "prof1",
            song_path="audio/suno4kids/child_hash/song.mp3",
            image_path="images/suno4kids/child_hash/img.png",
        )

        count = update_project_paths(projects_dir, "suno4kids", dry_run=False)
        assert count == 0

    def test_skips_empty_paths(self, tmp_path):
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        _create_project(projects_dir, "p1", "prof1", song_path="", image_path="")

        count = update_project_paths(projects_dir, "suno4kids", dry_run=False)
        assert count == 0

    def test_handles_corrupt_json(self, tmp_path):
        projects_dir = tmp_path / "projects"
        projects_dir.mkdir()
        (projects_dir / "bad.json").write_text("not valid json{{{")

        count = update_project_paths(projects_dir, "suno4kids", dry_run=False)
        assert count == 0  # skipped, no crash


class TestCheckMigrationComplete:
    def test_returns_false_when_no_marker(self, tmp_path):
        assert check_migration_complete(tmp_path) is False

    def test_returns_true_when_marker_exists(self, tmp_path):
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / ".migration_complete").write_text("")
        assert check_migration_complete(tmp_path) is True


class TestWriteMarker:
    def test_writes_marker_file(self, tmp_path):
        write_marker(tmp_path, dry_run=False)
        assert (tmp_path / "data" / ".migration_complete").exists()

    def test_dry_run_does_not_write(self, tmp_path):
        write_marker(tmp_path, dry_run=True)
        assert not (tmp_path / "data" / ".migration_complete").exists()
