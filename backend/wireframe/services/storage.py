import asyncio
import logging
import shutil
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image

logger = logging.getLogger(__name__)

class LocalStorageService:
    def __init__(self, base_root: str = "./storage_data"):
        """
        :param base_root: The local root folder where all jobs will be saved.
        """
        self.base_root = Path(base_root)
        self.base_root.mkdir(parents=True, exist_ok=True)

    async def save_filtered_images(self, job_id: str, images: List[Dict[str, Any]]) -> int:
        """
        Saves a list of images to: ./storage_data/{job_id}/schematics/
        """
        # Define the job-specific path
        target_dir = self.base_root / job_id / "schematics"

        # Run the blocking I/O operation in a separate thread
        # to keep the Async Event Loop (ARQ) responsive.
        count = await asyncio.to_thread(
            self._write_files_sync, target_dir, images
        )

        return count

    def _write_files_sync(self, target_dir: Path, images: List[Dict[str, Any]]) -> int:
        """
        Synchronous helper function to actually write bytes to disk.
        Assumes that item["image"] is image bytes.
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        saved_count = 0

        for i, item in enumerate(images):
            try:
                img_bytes = item["image"]
                # Construct filename: schematic_001.png
                filename = f"schematic_{i:03d}.png"
                file_path = target_dir / filename

                # Write the bytes directly to disk
                with open(file_path, "wb") as f:
                    f.write(img_bytes)
                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to write image to {target_dir}: {e}")
                # We continue saving others even if one fails
                continue

        logger.info(f"Storage: Saved {saved_count} images to {target_dir}")
        return saved_count