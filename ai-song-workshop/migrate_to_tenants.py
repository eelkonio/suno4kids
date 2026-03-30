#!/usr/bin/env python3
"""
Migration script to move existing flat-directory data into tenant-scoped directories.

Moves profiles, projects, audio, images, and photos into a tenant subdirectory
(default: suno4kids) and updates file path references in project JSONs.

Usage:
    python migrate_to_tenants.py
    python migrate_to_tenants.py --tenant-name suno4kids --dry-run
    python migrate_to_tenants.py --storage-path /tmp/workshop_sessions
"""
import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

MARKER_FILE = 'data/.migration_complete'

# Path prefixes in project JSONs that need tenant scoping
# These are relative to static/ (e.g. "audio/child_hash/file.mp3")
PATH_PREFIXES_TO_UPDATE = {
    'song_file_path': 'audio/',
    'image_file_path': 'images/',
}


def check_migration_complete(script_dir: Path) -> bool:
    """Check if migration has already been completed."""
    marker = script_dir / MARKER_FILE
    return marker.exists()


def write_marker(script_dir: Path, dry_run: bool) -> None:
    """Write the migration marker file."""
    marker = script_dir / MARKER_FILE
    if dry_run:
        logger.info(f"[DRY RUN] Would write marker file: {marker}")
        return
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text('')
    logger.info(f"Migration marker written: {marker}")


def move_json_files(src_dir: Path, dest_dir: Path, dry_run: bool) -> int:
    """
    Move *.json files from src_dir to dest_dir.

    Returns the number of files moved.
    """
    if not src_dir.exists():
        logger.info(f"Source directory does not exist, skipping: {src_dir}")
        return 0

    count = 0
    for json_file in sorted(src_dir.glob('*.json')):
        dest_file = dest_dir / json_file.name
        if dest_file.exists():
            logger.info(f"Already exists at destination, skipping: {dest_file}")
            continue
        try:
            if dry_run:
                logger.info(f"[DRY RUN] Would move {json_file} -> {dest_file}")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(json_file), str(dest_file))
                logger.info(f"Moved {json_file} -> {dest_file}")
            count += 1
        except Exception as e:
            logger.error(f"Failed to move {json_file}: {e}")
    return count


def move_child_dirs(src_dir: Path, dest_dir: Path, tenant_name: str, dry_run: bool) -> int:
    """
    Move child directories (e.g. user hash dirs) from src_dir into dest_dir.
    Skips the tenant directory itself to avoid moving it into itself.
    Also moves any loose files (like .gitkeep) that aren't directories.

    Returns the number of items moved.
    """
    if not src_dir.exists():
        logger.info(f"Source directory does not exist, skipping: {src_dir}")
        return 0

    count = 0
    for item in sorted(src_dir.iterdir()):
        # Skip the tenant directory itself
        if item.name == tenant_name:
            continue
        # Skip hidden files like .gitkeep
        if item.name.startswith('.'):
            continue

        dest_item = dest_dir / item.name
        if dest_item.exists():
            logger.info(f"Already exists at destination, skipping: {dest_item}")
            continue
        try:
            if dry_run:
                logger.info(f"[DRY RUN] Would move {item} -> {dest_item}")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(dest_item))
                logger.info(f"Moved {item} -> {dest_item}")
            count += 1
        except Exception as e:
            logger.error(f"Failed to move {item}: {e}")
    return count


def update_project_paths(projects_dir: Path, tenant_name: str, dry_run: bool) -> int:
    """
    Update song_file_path and image_file_path in project JSON files
    to include the tenant prefix.

    E.g. "audio/child_hash/file.mp3" -> "audio/suno4kids/child_hash/file.mp3"

    Returns the number of files updated.
    """
    if not projects_dir.exists():
        logger.info(f"Projects directory does not exist, skipping path updates: {projects_dir}")
        return 0

    count = 0
    for json_file in sorted(projects_dir.glob('*.json')):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            changed = False
            for field, prefix in PATH_PREFIXES_TO_UPDATE.items():
                value = data.get(field)
                if not value or not isinstance(value, str):
                    continue
                # Skip if already has tenant prefix
                tenant_prefix = f"{prefix}{tenant_name}/"
                if value.startswith(tenant_prefix):
                    continue
                # Only update if it starts with the expected prefix
                if value.startswith(prefix):
                    # Insert tenant name after the prefix
                    # e.g. "audio/child/file.mp3" -> "audio/suno4kids/child/file.mp3"
                    rest = value[len(prefix):]
                    new_value = f"{prefix}{tenant_name}/{rest}"
                    data[field] = new_value
                    changed = True
                    logger.info(f"  {field}: {value} -> {new_value}")

            if changed:
                if dry_run:
                    logger.info(f"[DRY RUN] Would update paths in {json_file}")
                else:
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Updated paths in {json_file}")
                count += 1

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse {json_file}: {e}")
        except Exception as e:
            logger.error(f"Failed to update {json_file}: {e}")

    return count


def migrate(storage_path: str, tenant_name: str = 'suno4kids', dry_run: bool = False) -> bool:
    """
    Run the full migration.

    Args:
        storage_path: Base session storage path (e.g. /tmp/workshop_sessions)
        tenant_name: Tenant name to migrate data under (default: suno4kids)
        dry_run: If True, only log what would happen without making changes

    Returns:
        True if migration was performed, False if skipped (already complete)
    """
    # Resolve script directory (where data/ and static/ live)
    script_dir = Path(__file__).resolve().parent

    # Check marker
    if check_migration_complete(script_dir):
        logger.info("Migration already completed (marker file exists). Nothing to do.")
        return False

    if dry_run:
        logger.info("=== DRY RUN MODE — no files will be moved ===")

    storage = Path(storage_path)
    total_moved = 0

    # 1. Move profiles
    logger.info("--- Moving profiles ---")
    src_profiles = storage / 'profiles'
    dest_profiles = storage / tenant_name / 'profiles'
    total_moved += move_json_files(src_profiles, dest_profiles, dry_run)

    # 2. Move projects
    logger.info("--- Moving projects ---")
    src_projects = storage / 'projects'
    dest_projects = storage / tenant_name / 'projects'
    total_moved += move_json_files(src_projects, dest_projects, dry_run)

    # 3. Move static/audio child dirs
    logger.info("--- Moving audio directories ---")
    src_audio = script_dir / 'static' / 'audio'
    dest_audio = script_dir / 'static' / 'audio' / tenant_name
    total_moved += move_child_dirs(src_audio, dest_audio, tenant_name, dry_run)

    # 4. Move static/images child dirs
    logger.info("--- Moving image directories ---")
    src_images = script_dir / 'static' / 'images'
    dest_images = script_dir / 'static' / 'images' / tenant_name
    total_moved += move_child_dirs(src_images, dest_images, tenant_name, dry_run)

    # 5. Move static/photos child dirs
    logger.info("--- Moving photo directories ---")
    src_photos = script_dir / 'static' / 'photos'
    dest_photos = script_dir / 'static' / 'photos' / tenant_name
    total_moved += move_child_dirs(src_photos, dest_photos, tenant_name, dry_run)

    # 6. Update project JSON paths
    logger.info("--- Updating project JSON paths ---")
    updated = update_project_paths(dest_projects, tenant_name, dry_run)

    logger.info(f"Migration summary: {total_moved} items moved, {updated} project files updated")

    # 7. Write marker
    if not dry_run:
        write_marker(script_dir, dry_run)

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Migrate existing data to tenant-scoped directory structure'
    )
    parser.add_argument(
        '--storage-path',
        default=os.environ.get('SESSION_STORAGE_PATH', '/tmp/workshop_sessions'),
        help='Base session storage path (default: SESSION_STORAGE_PATH env or /tmp/workshop_sessions)'
    )
    parser.add_argument(
        '--tenant-name',
        default='suno4kids',
        help='Tenant name to migrate data under (default: suno4kids)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    args = parser.parse_args()

    logger.info(f"Starting migration: storage={args.storage_path}, tenant={args.tenant_name}, dry_run={args.dry_run}")

    try:
        result = migrate(args.storage_path, args.tenant_name, args.dry_run)
        if result:
            logger.info("Migration completed successfully.")
        else:
            logger.info("Migration skipped (already complete).")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
