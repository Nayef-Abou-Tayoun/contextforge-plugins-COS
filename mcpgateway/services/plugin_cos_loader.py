# -*- coding: utf-8 -*-
"""Location: ./mcpgateway/services/plugin_cos_loader.py
Copyright 2026
SPDX-License-Identifier: Apache-2.0

IBM Cloud Object Storage Plugin Loader Service.

Provides dynamic plugin loading from IBM COS without requiring gateway redeployment.
Supports background sync, hot reload via Redis pub/sub, and local caching.
"""

# Standard
import asyncio
import hashlib
import logging
import os
from pathlib import Path
import shutil
import tempfile
from typing import Optional

# Third-Party
import ibm_boto3
from ibm_botocore.client import Config as BotoConfig
from ibm_botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class COSPluginLoader:
    """Load and sync plugins from IBM Cloud Object Storage.

    Features:
    - Downloads plugin config and files from COS bucket
    - Caches locally for fast access
    - Background sync with configurable interval
    - Checksum validation to detect changes
    - Automatic plugin reload on changes

    Environment Variables:
        PLUGINS_COS_BUCKET: COS bucket name
        PLUGINS_COS_ENDPOINT: COS endpoint URL
        PLUGINS_COS_API_KEY: IBM Cloud API key
        PLUGINS_COS_INSTANCE_ID: COS service instance ID (optional)
        PLUGINS_COS_CONFIG_PATH: Path to config.yaml in bucket (default: plugins/config.yaml)
        PLUGINS_COS_SYNC_INTERVAL: Sync interval in seconds (default: 300)
        PLUGINS_LOCAL_CACHE_DIR: Local cache directory (default: /tmp/contextforge-plugins)
    """

    def __init__(self) -> None:
        """Initialize COS client and configuration."""
        self.bucket = os.getenv("PLUGINS_COS_BUCKET")
        self.endpoint = os.getenv("PLUGINS_COS_ENDPOINT")
        self.api_key = os.getenv("PLUGINS_COS_API_KEY")
        self.instance_id = os.getenv("PLUGINS_COS_INSTANCE_ID", "")
        self.config_path = os.getenv("PLUGINS_COS_CONFIG_PATH", "plugins/config_cos.yaml")
        self.sync_interval = int(os.getenv("PLUGINS_COS_SYNC_INTERVAL", "300"))

        # Use temp directory if not specified
        default_cache = Path(tempfile.gettempdir()) / "contextforge-plugins"
        self.cache_dir = Path(os.getenv("PLUGINS_LOCAL_CACHE_DIR", str(default_cache)))

        self._validate_config()

        # Initialize COS client
        self.cos_client = ibm_boto3.client(
            "s3",
            ibm_api_key_id=self.api_key,
            ibm_service_instance_id=self.instance_id,
            config=BotoConfig(signature_version="oauth"),
            endpoint_url=self.endpoint,
        )

        # Track last sync checksum
        self._last_checksum: Optional[str] = None
        self._sync_task: Optional[asyncio.Task] = None

    def _validate_config(self) -> None:
        """Validate required COS configuration."""
        if not self.bucket:
            raise ValueError("PLUGINS_COS_BUCKET environment variable is required")
        if not self.endpoint:
            raise ValueError("PLUGINS_COS_ENDPOINT environment variable is required")
        if not self.api_key:
            raise ValueError("PLUGINS_COS_API_KEY environment variable is required")

    def _calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA256 checksum of content."""
        return hashlib.sha256(content).hexdigest()

    async def download_plugins(self) -> tuple[Path, bool]:
        """Download plugin config and files from COS.

        Returns:
            Tuple of (config_path, changed) where changed indicates if plugins were updated
        """
        logger.info("Downloading plugins from COS bucket: %s", self.bucket)

        # Create cache directory
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Download config.yaml first
        config_local_path = self.cache_dir / "config.yaml"
        try:
            response = self.cos_client.get_object(Bucket=self.bucket, Key=self.config_path)
            config_content = response["Body"].read()

            # Check if config changed
            current_checksum = self._calculate_checksum(config_content)
            changed = current_checksum != self._last_checksum

            # Write config file
            config_local_path.write_bytes(config_content)
            self._last_checksum = current_checksum

            logger.info("Downloaded config.yaml (changed: %s, checksum: %s)", changed, current_checksum[:8])

        except ClientError as e:
            logger.error("Failed to download config.yaml from COS: %s", e)
            # If config exists locally, use it
            if config_local_path.exists():
                logger.warning("Using cached config.yaml")
                return config_local_path, False
            raise

        # Download all plugin files
        try:
            paginator = self.cos_client.get_paginator("list_objects_v2")
            plugin_count = 0

            for page in paginator.paginate(Bucket=self.bucket, Prefix="plugins/"):
                for obj in page.get("Contents", []):
                    key = obj["Key"]

                    # Skip directories and config.yaml (already downloaded)
                    if key.endswith("/") or key == self.config_path:
                        continue

                    # Download file
                    local_path = self.cache_dir / key
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    try:
                        self.cos_client.download_file(self.bucket, key, str(local_path))
                        plugin_count += 1
                        logger.debug("Downloaded %s", key)
                    except ClientError as e:
                        logger.warning("Failed to download %s: %s", key, e)

            logger.info("Downloaded %d plugin files from COS", plugin_count)

        except ClientError as e:
            logger.error("Failed to list/download plugin files from COS: %s", e)
            # Continue with existing cached files if available

        return config_local_path, changed

    async def sync_once(self) -> bool:
        """Perform a single sync operation.

        Returns:
            True if plugins were updated and reload is needed
        """
        try:
            config_path, changed = await self.download_plugins()

            if changed:
                logger.info("Plugins changed, triggering reload")
                # Import here to avoid circular dependency
                from mcpgateway.plugins import invalidate_all_plugin_managers

                await invalidate_all_plugin_managers()
                return True

            logger.debug("No plugin changes detected")
            return False

        except Exception as e:
            logger.error("Failed to sync plugins from COS: %s", e, exc_info=True)
            return False

    async def sync_loop(self) -> None:
        """Continuously sync plugins from COS at configured interval."""
        logger.info("Starting COS plugin sync loop (interval: %ds)", self.sync_interval)

        while True:
            try:
                await self.sync_once()
            except Exception as e:
                logger.error("Error in sync loop: %s", e, exc_info=True)

            await asyncio.sleep(self.sync_interval)

    def start_sync_task(self) -> None:
        """Start background sync task."""
        if self._sync_task is not None:
            logger.warning("Sync task already running")
            return

        self._sync_task = asyncio.create_task(self.sync_loop())
        logger.info("Started COS plugin sync background task")

    async def stop_sync_task(self) -> None:
        """Stop background sync task."""
        if self._sync_task is None:
            return

        self._sync_task.cancel()
        try:
            await self._sync_task
        except asyncio.CancelledError:
            pass

        self._sync_task = None
        logger.info("Stopped COS plugin sync background task")

    def cleanup_cache(self) -> None:
        """Remove cached plugin files."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            logger.info("Cleaned up plugin cache directory: %s", self.cache_dir)


# Global singleton instance
_cos_loader: Optional[COSPluginLoader] = None


def get_cos_loader() -> Optional[COSPluginLoader]:
    """Get the global COS loader instance."""
    return _cos_loader


def initialize_cos_loader() -> COSPluginLoader:
    """Initialize and return the global COS loader instance."""
    global _cos_loader  # noqa: PLW0603
    if _cos_loader is None:
        _cos_loader = COSPluginLoader()
    return _cos_loader


async def shutdown_cos_loader() -> None:
    """Shutdown the global COS loader instance."""
    global _cos_loader  # noqa: PLW0603
    if _cos_loader is not None:
        await _cos_loader.stop_sync_task()
        _cos_loader = None

# Made with Bob
