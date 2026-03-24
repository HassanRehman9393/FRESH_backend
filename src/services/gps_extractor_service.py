"""
GPS data extraction service for images with EXIF data
"""

from typing import Dict, Any, Optional, Tuple
import tempfile
import os
import logging

logger = logging.getLogger(__name__)


class GPSExtractorService:
    """Service for extracting GPS coordinates from image EXIF data"""
    
    @staticmethod
    def extract_gps_from_exif(file_bytes: bytes, filename: str = "image") -> Dict[str, Any]:
        """
        Extract GPS coordinates from image EXIF data using exifread
        
        Args:
            file_bytes: Image file content as bytes
            filename: Original filename (for logging)
        
        Returns:
            Dict with keys: latitude, longitude, altitude (or empty dict if no GPS found)
        """
        try:
            import exifread
        except ImportError:
            logger.warning("exifread not installed - GPS extraction unavailable")
            return {}
        
        try:
            # Create temporary file to read EXIF data
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
                tmp.write(file_bytes)
                tmp.flush()
                tmp_path = tmp.name
            
            gps_data = {}
            
            try:
                # Read EXIF data
                with open(tmp_path, 'rb') as img_file:
                    tags = exifread.process_file(img_file, details=False)
                    
                    # Extract GPS info
                    gps_latitude = GPSExtractorService._get_decimal_from_exif(tags, 'GPS GPSLatitude', 'GPS GPSLatitudeRef')
                    gps_longitude = GPSExtractorService._get_decimal_from_exif(tags, 'GPS GPSLongitude', 'GPS GPSLongitudeRef')
                    gps_altitude = GPSExtractorService._get_altitude_from_exif(tags)
                    gps_timestamp = GPSExtractorService._get_timestamp_from_exif(tags)
                    
                    # Only include if we have valid coordinates
                    if gps_latitude is not None and gps_longitude is not None:
                        gps_data = {
                            "gps_latitude": gps_latitude,
                            "gps_longitude": gps_longitude
                        }
                        
                        if gps_altitude is not None:
                            gps_data["gps_altitude"] = gps_altitude
                        
                        if gps_timestamp:
                            gps_data["gps_timestamp"] = gps_timestamp
                        
                        logger.info(f"✅ GPS extracted from {filename}: "
                                   f"({gps_latitude}, {gps_longitude})")
                    else:
                        logger.debug(f"⚠️ No GPS coordinates found in {filename}")
            
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_path)
                except:
                    pass
            
            return gps_data
            
        except Exception as e:
            logger.error(f"Failed to extract GPS from {filename}: {str(e)}")
            return {}
    
    @staticmethod
    def _get_decimal_from_exif(tags: Dict, lat_tag: str, lat_ref_tag: str) -> Optional[float]:
        """
        Convert EXIF GPS coordinates to decimal format
        
        Args:
            tags: EXIF tags dictionary from exifread
            lat_tag: Tag name for latitude (e.g., 'GPS GPSLatitude')
            lat_ref_tag: Tag name for latitude reference (e.g., 'GPS GPSLatitudeRef')
        
        Returns:
            Decimal coordinate or None if not found
        """
        try:
            if lat_tag not in tags or lat_ref_tag not in tags:
                return None
            
            # Get coordinate value
            coord_value = tags[lat_tag].values
            
            # coord_value is a list of Fractions: [degrees, minutes, seconds]
            if not coord_value or len(coord_value) < 3:
                return None
            
            # Convert fractions to decimal
            degrees = float(coord_value[0].num) / float(coord_value[0].den)
            minutes = float(coord_value[1].num) / float(coord_value[1].den)
            seconds = float(coord_value[2].num) / float(coord_value[2].den)
            
            # Combine into decimal degrees
            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            
            # Apply direction (S and W are negative)
            direction = str(tags[lat_ref_tag].values)
            if direction in ('S', 'W'):
                decimal = -decimal
            
            # Validate range
            if lat_tag == 'GPS GPSLatitude':
                if -90 <= decimal <= 90:
                    return round(decimal, 6)  # 6 decimal places = ~0.11m precision
            else:  # Longitude
                if -180 <= decimal <= 180:
                    return round(decimal, 6)
            
            logger.warning(f"Invalid coordinate range: {decimal}")
            return None
            
        except (ValueError, ZeroDivisionError, AttributeError, IndexError) as e:
            logger.debug(f"Failed to parse coordinate: {str(e)}")
            return None
    
    @staticmethod
    def _get_altitude_from_exif(tags: Dict) -> Optional[float]:
        """Extract altitude from EXIF GPS data"""
        try:
            if 'GPS GPSAltitude' not in tags:
                return None
            
            alt_value = tags['GPS GPSAltitude'].values
            if not alt_value:
                return None
            
            # Convert fraction to float
            altitude = float(alt_value[0].num) / float(alt_value[0].den)
            
            # Check for altitude ref (0 = above sea level, 1 = below)
            if 'GPS GPSAltitudeRef' in tags:
                ref = int(tags['GPS GPSAltitudeRef'].values[0])
                if ref == 1:
                    altitude = -altitude
            
            return round(altitude, 2)
        
        except (ValueError, ZeroDivisionError, AttributeError, IndexError):
            return None
    
    @staticmethod
    def _get_timestamp_from_exif(tags: Dict) -> Optional[str]:
        """Extract timestamp from EXIF GPS or DateTime data"""
        try:
            # Try GPS timestamp first
            if 'GPS GPSDate' in tags:
                gps_date = str(tags['GPS GPSDate'].values)
                return gps_date
            
            # Fallback to image datetime
            if 'EXIF DateTimeOriginal' in tags:
                return str(tags['EXIF DateTimeOriginal'].values)
            
            if 'Image DateTime' in tags:
                return str(tags['Image DateTime'].values)
            
            return None
        
        except (AttributeError, ValueError):
            return None
