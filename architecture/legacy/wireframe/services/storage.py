import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import List
from PIL import Image
from wireframe.agents.state import ImageDataDict, ExtractedCircuitDict

logger = logging.getLogger(__name__)

class LocalStorageService:
    def __init__(self, base_root: str = "./storage_data"):
        """
        :param base_root: The local root folder where all jobs will be saved.
        """
        self.base_root = Path(base_root)
        self.base_root.mkdir(parents=True, exist_ok=True)

    async def save_filtered_images(self, job_id: str, images: List[ImageDataDict]) -> int:
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

    def _write_files_sync(self, target_dir: Path, images: List[ImageDataDict]) -> int:
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

    async def save_extracted_circuits(self, job_id: str, extracted_circuits: List[ExtractedCircuitDict]) -> int:
        """
        Saves extracted circuit information as JSON to: ./storage_data/{job_id}/schematics/extracted_circuits.json
        """
        target_file = self.base_root / job_id / "schematics" / "extracted_circuits.json"
        
        count = await asyncio.to_thread(
            self._write_json_sync, target_file, extracted_circuits
        )
        
        return count

    def _write_json_sync(self, target_file: Path, extracted_circuits: List[ExtractedCircuitDict]) -> int:
        """
        Synchronous helper function to write JSON data to disk.
        """
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(extracted_circuits, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Storage: Saved {len(extracted_circuits)} extracted circuits to {target_file}")
            return len(extracted_circuits)
            
        except Exception as e:
            logger.error(f"Failed to write JSON to {target_file}: {e}")
            return 0