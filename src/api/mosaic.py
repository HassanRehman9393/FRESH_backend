"""
API endpoints for ortho-mosaic tile serving and metadata
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
from src.api.deps import get_current_user
from src.services.ortho_mosaic_service import OrthoMosaicService
from src.core.supabase_client import admin_supabase
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mosaic", tags=["mosaic"])


def _clean_url(url: str) -> str:
    """Remove trailing ? from Supabase URLs"""
    if url and url.endswith('?'):
        return url[:-1]
    return url


def _get_preview_url(file_path: str, file_name: str, user_id: str) -> str:
    """
    Get the appropriate preview URL for an image file.
    For TIFF files, attempt to return a JPG thumbnail path.
    For other formats, return the original URL.
    """
    file_ext = file_name.lower().split('.')[-1] if file_name else ''
    
    # For TIFF files, try to return JPG thumbnail URL
    if file_ext in ['tif', 'tiff']:
        # Construct thumbnail path: same path with .jpg extension
        thumb_path = file_path.rsplit('.', 1)[0] + '_thumb.jpg' if file_path else None
        if thumb_path:
            try:
                thumb_url = admin_supabase.storage.from_('images').get_public_url(thumb_path)
                thumb_url = _clean_url(thumb_url)
                # Return thumbnail if it's a valid URL (will be checked when loading)
                return thumb_url
            except:
                pass
    
    # Fallback to original URL
    orig_url = admin_supabase.storage.from_('images').get_public_url(file_path) if file_path else None
    return _clean_url(orig_url) if orig_url else None


@router.get("/bounds")
async def get_mosaic_bounds(current_user: dict = Depends(get_current_user)):
    """
    Get bounding box and metadata for user's GPS mosaic
    
    Returns bounds, center, optimal zoom level, and image count
    """
    try:
        # Fetch all images with GPS for this user
        result = admin_supabase.table("images").select("*").eq(
            "user_id", current_user["user_id"]
        ).execute()
        
        images_with_gps = []
        for record in result.data:
            metadata = record.get("metadata", {})
            lat = metadata.get("gps_latitude")
            lon = metadata.get("gps_longitude")
            
            if lat is not None and lon is not None:
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    images_with_gps.append(record)
        
        if not images_with_gps:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No GPS-tagged images found"
            )
        
        # Calculate bounds
        bounds = OrthoMosaicService.get_mosaic_bounds(images_with_gps)
        if not bounds:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not calculate mosaic bounds"
            )
        
        # Calculate optimal zoom
        optimal_zoom = OrthoMosaicService.get_optimal_zoom_level(bounds)
        
        return {
            "bounds": bounds,
            "optimal_zoom": optimal_zoom,
            "image_count": bounds.get("image_count", 0),
            "center": {
                "lat": bounds["center_lat"],
                "lng": bounds["center_lon"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get mosaic bounds: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate bounds: {str(e)}"
        )


@router.get("/info")
async def get_mosaic_info(current_user: dict = Depends(get_current_user)):
    """
    Get comprehensive mosaic information and statistics
    
    Returns image count, GPS coverage, tile generation status, etc.
    """
    try:
        # Fetch all images with GPS
        result = admin_supabase.table("images").select("*").eq(
            "user_id", current_user["user_id"]
        ).execute()
        
        total_images = len(result.data)
        
        images_with_gps = []
        gps_stats = {
            "min_lat": None,
            "max_lat": None,
            "min_lon": None,
            "max_lon": None,
            "min_alt": None,
            "max_alt": None
        }
        
        for record in result.data:
            metadata = record.get("metadata", {})
            lat = metadata.get("gps_latitude")
            lon = metadata.get("gps_longitude")
            alt = metadata.get("gps_altitude")
            
            if lat is not None and lon is not None:
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    images_with_gps.append(record)
                    
                    # Update stats
                    if gps_stats["min_lat"] is None or lat < gps_stats["min_lat"]:
                        gps_stats["min_lat"] = lat
                    if gps_stats["max_lat"] is None or lat > gps_stats["max_lat"]:
                        gps_stats["max_lat"] = lat
                    if gps_stats["min_lon"] is None or lon < gps_stats["min_lon"]:
                        gps_stats["min_lon"] = lon
                    if gps_stats["max_lon"] is None or lon > gps_stats["max_lon"]:
                        gps_stats["max_lon"] = lon
                    
                    if alt is not None:
                        if gps_stats["min_alt"] is None or alt < gps_stats["min_alt"]:
                            gps_stats["min_alt"] = alt
                        if gps_stats["max_alt"] is None or alt > gps_stats["max_alt"]:
                            gps_stats["max_alt"] = alt
        
        bounds = OrthoMosaicService.get_mosaic_bounds(images_with_gps)
        
        return {
            "status": "ready" if images_with_gps else "no_data",
            "total_images": total_images,
            "images_with_gps": len(images_with_gps),
            "coverage_percent": round((len(images_with_gps) / total_images * 100) if total_images > 0 else 0, 1),
            "bounds": bounds,
            "gps_statistics": gps_stats,
            "tile_generation": {
                "status": "ready",
                "cached": False,
                "last_generated": None
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get mosaic info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get mosaic info: {str(e)}"
        )


@router.get("/images-geojson")
async def get_mosaic_geojson(current_user: dict = Depends(get_current_user)):
    """
    Get all GPS images as GeoJSON FeatureCollection
    
    Useful for displaying as markers or styling in Leaflet
    """
    try:
        result = admin_supabase.table("images").select("*").eq(
            "user_id", current_user["user_id"]
        ).execute()
        
        features = []
        
        for record in result.data:
            metadata = record.get("metadata", {})
            lat = metadata.get("gps_latitude")
            lon = metadata.get("gps_longitude")
            
            if lat is not None and lon is not None:
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    file_path = record.get("file_path")
                    file_name = record.get("file_name", "")
                    image_url = None
                    
                    # Generate clean public URL
                    if file_path:
                        if file_path.startswith("http"):
                            image_url = _clean_url(file_path)
                        else:
                            try:
                                raw_url = admin_supabase.storage.from_('images').get_public_url(file_path)
                                image_url = _clean_url(raw_url)
                            except Exception as e:
                                logger.warning(f"Failed to generate URL from file_path {file_path}: {e}")
                    
                    # Fallback: try to generate from file_name
                    if not image_url and file_name:
                        try:
                            storage_path = f"{current_user['user_id']}/{file_name}" if not file_name.startswith(current_user['user_id']) else file_name
                            raw_url = admin_supabase.storage.from_('images').get_public_url(storage_path)
                            image_url = _clean_url(raw_url)
                        except Exception as e:
                            logger.warning(f"Failed to generate URL from file_name {file_name}: {e}")
                    
                    # Skip images without valid URLs
                    if not image_url:
                        logger.warning(f"Image {record.get('id')} - no valid URL generated")
                        continue
                    
                    feature = {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "properties": {
                            "id": record.get("id"),
                            "file_name": file_name,
                            "image_url": image_url,
                            "latitude": lat,
                            "longitude": lon,
                            "altitude": metadata.get("gps_altitude"),
                            "timestamp": record.get("created_at"),
                            "description": f"{file_name} - GPS ({lat:.6f}, {lon:.6f})"
                        }
                    }
                    features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "features": features,
            "properties": {
                "name": f"Ortho-Mosaic ({len(features)} images)",
                "count": len(features)
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to generate GeoJSON: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate GeoJSON: {str(e)}"
        )


@router.post("/generate-tiles")
async def generate_mosaic_tiles(current_user: dict = Depends(get_current_user)):
    """
    Trigger XYZ tile generation for user's mosaic (async operation)
    
    Returns job status and tile generation parameters
    """
    try:
        user_id = current_user["user_id"]
        
        # Fetch all images with GPS
        result = admin_supabase.table("images").select("*").eq(
            "user_id", user_id
        ).execute()
        
        images_with_gps = []
        for record in result.data:
            metadata = record.get("metadata", {})
            lat = metadata.get("gps_latitude")
            lon = metadata.get("gps_longitude")
            
            if lat is not None and lon is not None:
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    images_with_gps.append(record)
        
        if not images_with_gps:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No GPS-tagged images found"
            )
        
        # For now, just return tile info (actual tile generation would be async)
        bounds = OrthoMosaicService.get_mosaic_bounds(images_with_gps)
        optimal_zoom = OrthoMosaicService.get_optimal_zoom_level(bounds)
        
        logger.info(f"📡 Tile generation requested for user {user_id} "
                   f"({len(images_with_gps)} images)")
        
        return {
            "status": "queued",
            "message": "Tiles ready for display",
            "images_to_tile": len(images_with_gps),
            "optimal_zoom": optimal_zoom,
            "bounds": bounds,
            "estimated_tiles": len(images_with_gps) * 4,  # Rough estimate
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tile generation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tile generation failed: {str(e)}"
        )
