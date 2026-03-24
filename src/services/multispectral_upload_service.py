"""
Multispectral Image Upload Service

Handles batch upload of multispectral imagery, grouping by filename,
creating composites, and storing metadata.
"""

import os
import tempfile
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Dict, Any
from uuid import uuid4
from datetime import datetime
from fastapi import UploadFile
import aiofiles
import logging

from src.services.multispectral import MultispectralProcessor
from src.services.image_service import upload_to_supabase_storage
from src.core.supabase_client import admin_supabase
from src.schemas.image import ImageCreateResponse, MultispectralUploadResponse

logger = logging.getLogger(__name__)


async def save_temp_file(file: UploadFile) -> str:
    """Save uploaded file to temporary location"""
    await file.seek(0)
    contents = await file.read()
    
    # Create temp file with original extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    temp_file.write(contents)
    temp_file.flush()
    temp_file.close()
    
    return temp_file.name


async def upload_multispectral_images(
    user_id: str,
    files: List[UploadFile],
    orchard_id: str = None
) -> MultispectralUploadResponse:
    """
    Upload and process multispectral images - creates detection-ready images
    
    Args:
        user_id: User ID
        files: List of uploaded files (multispectral bands)
        orchard_id: Optional orchard association
        
    Returns:
        MultispectralUploadResponse with detection-ready images
    """
    logger.info(f"Starting multispectral upload for user {user_id}")
    logger.info(f"Received {len(files)} files")
    
    temp_files = []
    band_image_records = []
    composite_image_records = []
    complete_sets_info = []
    incomplete_sets_info = []
    
    try:
        # Step 1: Save all uploaded files to temp storage
        file_mapping = {}  # {filename: temp_path}
        for file in files:
            logger.info(f"Processing upload: {file.filename}")
            temp_path = await save_temp_file(file)
            temp_files.append(temp_path)
            file_mapping[file.filename] = temp_path
        
        # Step 2: Group images by base name and validate completeness
        all_sets = MultispectralProcessor.group_images(list(file_mapping.keys()))
        complete_sets = MultispectralProcessor.filter_complete_sets(all_sets)
        
        logger.info(f"Found {len(all_sets)} total sets, {len(complete_sets)} complete")
        
        # Track incomplete sets for user feedback
        for base_name, mset in all_sets.items():
            if not mset.is_complete:
                incomplete_sets_info.append({
                    "base_name": base_name,
                    "present_bands": sorted(mset.band_paths.keys()),
                    "missing_bands": mset.missing_bands
                })
        
        # Step 3: Upload all band images to storage (even from incomplete sets)
        # This allows users to see what was uploaded
        for filename, temp_path in file_mapping.items():
            parsed = MultispectralProcessor.parse_filename(filename)
            if not parsed:
                logger.warning(f"Skipping invalid filename: {filename}")
                continue
                
            base_name, band_num = parsed
            
            # Upload band image to Supabase storage
            image_id = str(uuid4())
            file_extension = os.path.splitext(filename)[1].lower()
            storage_file_name = f"multispectral/{user_id}/{image_id}{file_extension}"
            
            # Read temp file and create UploadFile-like object for upload
            with open(temp_path, 'rb') as f:
                file_content = f.read()
            
            # Create temporary UploadFile for storage upload
            class TempUploadFile:
                def __init__(self, content, filename, content_type="image/jpeg"):
                    self.content = content
                    self.filename = filename
                    self.content_type = content_type
                    self.position = 0
                
                async def seek(self, position):
                    self.position = position
                
                async def read(self):
                    return self.content
            
            temp_upload = TempUploadFile(file_content, storage_file_name)
            file_path = await upload_to_supabase_storage(temp_upload, storage_file_name)
            
            # Create database record for band image
            now = datetime.utcnow()
            is_part_of_complete_set = base_name in complete_sets
            
            metadata = {
                "original_filename": filename,
                "storage_filename": storage_file_name,
                "content_type": "image/jpeg",
                "is_multispectral": True,
                "multispectral_base_name": base_name,
                "band_number": band_num,
                "band_info": MultispectralProcessor.BAND_INFO.get(band_num, {}),
                "is_complete_set": is_part_of_complete_set,
                "orchard_id": orchard_id
            }
            
            data = {
                "id": image_id,
                "user_id": user_id,
                "file_path": file_path,
                "file_name": storage_file_name,
                "metadata": metadata,
                "created_at": now.isoformat()
            }
            
            result = admin_supabase.table("images").insert(data).execute()
            if result.data:
                band_record = ImageCreateResponse(**result.data[0])
                band_image_records.append(band_record)
                logger.info(f"✅ Uploaded band {band_num} of {base_name}")
        
        # Step 4: Process complete sets - create ONLY detection-ready images
        for base_name, mset in complete_sets.items():
            logger.info(f"Processing {base_name} - Creating detection image...")
            
            # Build band_paths with actual temp file locations
            band_paths = {}
            for band_num, filename in mset.band_paths.items():
                band_paths[band_num] = file_mapping[filename]
            
            # Create ALIGNED RGB composite for TRUE color detection
            # Uses AKAZE feature matching to align Band 1 (Blue) and Band 3 (Red) to Band 2 (Green)
            logger.info(f"Creating aligned RGB composite for {base_name}...")
            detection_array = MultispectralProcessor.create_aligned_rgb_composite(
                band_paths, use_parallel=True
            )
            
            # Save detection image to temp file
            detection_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_files.append(detection_temp.name)
            Image.fromarray(detection_array).save(detection_temp.name, 'JPEG', quality=95)
            detection_temp.close()
            
            # Upload detection image to storage
            detection_id = str(uuid4())
            detection_storage_name = f"multispectral/{user_id}/detection/{detection_id}.jpg"
            
            with open(detection_temp.name, 'rb') as f:
                detection_content = f.read()
            
            temp_upload_detection = TempUploadFile(detection_content, detection_storage_name, "image/jpeg")
            detection_file_path = await upload_to_supabase_storage(temp_upload_detection, detection_storage_name)
            
            # Extract GPS metadata with MAPVIEW logging
            logger.info("\n" + "="*80)
            logger.info("🗺️  [MAPVIEW] Extracting GPS for map mosaic...")
            print("\n" + "="*80)
            print("🗺️  [MAPVIEW] Extracting GPS for map mosaic...")
            print(f"   Band paths: {band_paths}")
            print("="*80)
            
            try:
                gps_data = MultispectralProcessor.extract_gps_from_bands(band_paths)
                print(f"\n✅ GPS Extraction completed. Result: {gps_data}")
            except Exception as gps_err:
                print(f"\n❌ GPS Extraction failed with error: {gps_err}")
                import traceback
                traceback.print_exc()
                gps_data = None
            
            if gps_data:
                logger.info(f"✅ [MAPVIEW] GPS FOUND: ({gps_data['gps_latitude']:.6f}, {gps_data['gps_longitude']:.6f})")
                print(f"✅ [MAPVIEW] GPS FOUND: ({gps_data['gps_latitude']:.6f}, {gps_data['gps_longitude']:.6f})")
            else:
                logger.error(f"❌ [MAPVIEW] NO GPS - image will NOT appear on map")
                print(f"❌ [MAPVIEW] NO GPS - image will NOT appear on map")
            logger.info("="*80)
            print("="*80)
            
            # Store detection with GPS in metadata
            logger.info(f"\n📊 [MAPVIEW-DB] Storing in database...")
            logger.info(f"   Lat: {gps_data.get('gps_latitude') if gps_data else 'NULL'}")
            logger.info(f"   Lon: {gps_data.get('gps_longitude') if gps_data else 'NULL'}")
            logger.info(f"   Alt: {gps_data.get('gps_altitude') if gps_data else 'NULL'}")
            
            detection_metadata = {
                "original_filename": f"{base_name}_rgb_composite.jpg",
                "storage_filename": detection_storage_name,
                "content_type": "image/jpeg",
                "is_multispectral_detection": True,
                "multispectral_base_name": base_name,
                "composite_type": "aligned_rgb",
                "alignment_method": "AKAZE_feature_matching",
                "optimized_for": "YOLO_detection",
                "description": "Aligned true RGB composite - Blue/Green/Red bands aligned with AKAZE",
                "orchard_id": orchard_id,
                "gps_data": gps_data,
                "gps_latitude": gps_data.get('gps_latitude') if gps_data else None,
                "gps_longitude": gps_data.get('gps_longitude') if gps_data else None,
                "gps_altitude": gps_data.get('gps_altitude') if gps_data else None
            }
            
            detection_data = {
                "id": detection_id,
                "user_id": user_id,
                "file_path": detection_file_path,
                "file_name": detection_storage_name,
                "metadata": detection_metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            result_detection = admin_supabase.table("images").insert(detection_data).execute()
            if result_detection.data:
                detection_record = ImageCreateResponse(**result_detection.data[0])
                composite_image_records.append(detection_record)  # Add to results
                logger.info(f"✅ [MAPVIEW-DB] Stored detection image in database")
                logger.info(f"   ID: {detection_id}")
                logger.info(f"   📦 [DEBUG] Stored metadata: {detection_metadata}")
                logger.info(f"   📦 [DEBUG] Response metadata: {detection_record.metadata}")
                if gps_data:
                    logger.info(f"   🗺️  Map marker: ({gps_data['gps_latitude']:.6f}, {gps_data['gps_longitude']:.6f}) ✓")
                else:
                    logger.warning(f"   ❌ No GPS coordinate for map")
                
                # Add to complete sets info
                complete_sets_info.append({
                    "base_name": base_name,
                    "detection_id": detection_id,
                    "has_gps": gps_data is not None,
                    "gps_latitude": gps_data.get('gps_latitude') if gps_data else None,
                    "gps_longitude": gps_data.get('gps_longitude') if gps_data else None,
                    "gps_altitude": gps_data.get('gps_altitude') if gps_data else None,
                    "bands": sorted(band_paths.keys()),
                    "description": "Aligned RGB composite (AKAZE) - True color optimized for YOLO detection",
                    "map_ready": gps_data is not None
                })
        
        # Calculate statistics
        total_uploads = len(files)
        processed_sets = len(complete_sets)
        discarded_images = len([s for s in all_sets.values() if not s.is_complete]) * 6  # Approx
        
        logger.info(f"✅ Multispectral upload complete:")
        logger.info(f"   Total uploads: {total_uploads}")
        logger.info(f"   Processed sets: {processed_sets}")
        logger.info(f"   Composites created: {len(composite_image_records)}")
        logger.info(f"   Band images stored: {len(band_image_records)}")
        
        return MultispectralUploadResponse(
            complete_sets=complete_sets_info,
            incomplete_sets=incomplete_sets_info,
            composite_images=composite_image_records,
            band_images=band_image_records,
            total_uploads=total_uploads,
            processed_sets=processed_sets,
            discarded_images=len(incomplete_sets_info)
        )
        
    except Exception as e:
        logger.error(f"Error processing multispectral upload: {e}", exc_info=True)
        raise Exception(f"Multispectral upload failed: {str(e)}")
        
    finally:
        # Cleanup all temp files
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")


class TempUploadFile:
    """Helper class to mimic UploadFile for internal uploads"""
    def __init__(self, content, filename, content_type="image/jpeg"):
        self.content = content
        self.filename = filename
        self.content_type = content_type
        self.position = 0
    
    async def seek(self, position):
        self.position = position
    
    async def read(self):
        return self.content
