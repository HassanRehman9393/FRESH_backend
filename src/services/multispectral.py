"""
Multispectral Image Processing Service

Handles grouping, validation, and composition of 6-band multispectral imagery.
Naming convention: IMG_XXXX_B where B is band number (1-6)

Example:
  IMG_0197_1.jpg  (Band 1: Blue)
  IMG_0197_2.jpg  (Band 2: Green)
  IMG_0197_3.jpg  (Band 3: Red)
  IMG_0197_4.jpg  (Band 4: Red Edge)
  IMG_0197_5.jpg  (Band 5: NIR)
  IMG_0197_6.jpg  (Band 6: Additional)
"""

import re
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


@dataclass
class MultispectralSet:
    """Represents a complete 6-band multispectral image set"""
    base_name: str
    band_paths: Dict[int, str]  # {1: 'path/to/IMG_0197_1.jpg', 2: '...', ...}
    is_complete: bool
    missing_bands: List[int]
    

class MultispectralProcessor:
    """Process and compose multispectral imagery"""
    
    # Band wavelength reference (typical drone multispectral camera)
    BAND_INFO = {
        1: {"name": "Blue", "wavelength": "~475nm", "visible": True},
        2: {"name": "Green", "wavelength": "~560nm", "visible": True},
        3: {"name": "Red", "wavelength": "~668nm", "visible": True},
        4: {"name": "Red Edge", "wavelength": "~717nm", "visible": False},
        5: {"name": "NIR", "wavelength": "~840nm", "visible": False},
        6: {"name": "Additional", "wavelength": "Variable", "visible": False},
    }
    
    @staticmethod
    def _load_single_band(path: str) -> Tuple[str, np.ndarray]:
        """
        Load a single band image (helper for parallel loading)
        
        Returns: (path, numpy_array)
        """
        img = Image.open(path)
        arr = np.array(img)
        
        # Handle multi-channel images (take first channel)
        if len(arr.shape) == 3:
            arr = arr[:, :, 0]
        
        # Convert to float32 for processing
        arr = arr.astype(np.float32)
        
        return path, arr
    
    @staticmethod
    def load_bands_parallel(band_paths: Dict[int, List[int]]) -> Dict[int, np.ndarray]:
        """
        Load multiple bands in parallel (MUCH FASTER for TIFF files)
        
        Args:
            band_paths: {band_num: path, ...}
            
        Returns:
            {band_num: numpy_array, ...}
        """
        logger.info(f"⚡ Loading {len(band_paths)} bands in parallel...")
        
        # Use ThreadPoolExecutor for parallel I/O
        with ThreadPoolExecutor(max_workers=6) as executor:
            # Submit all loading tasks
            futures = {
                executor.submit(MultispectralProcessor._load_single_band, path): band_num
                for band_num, path in band_paths.items()
            }
            
            # Collect results
            loaded_bands = {}
            for future in futures:
                band_num = futures[future]
                path, arr = future.result()
                loaded_bands[band_num] = arr
                logger.info(f"  Band {band_num}: {arr.shape}, {arr.min():.0f}-{arr.max():.0f}")
        
        logger.info("✅ All bands loaded")
        return loaded_bands
    
    @staticmethod
    def parse_filename(filename: str) -> Optional[Tuple[str, int]]:
        """
        Parse multispectral image filename
        
        Args:
            filename: e.g., 'IMG_0197_1.jpg' or 'IMG_0197_1'
            
        Returns:
            Tuple of (base_name, band_number) or None if invalid
            Example: ('IMG_0197', 1)
        """
        # Match pattern: anything_digit or anything_digit.extension
        # IMG_0197_1.jpg -> base='IMG_0197', band=1
        # IMG_0197_1 -> base='IMG_0197', band=1
        match = re.match(r'^(.+?)_(\d+)(?:\.\w+)?$', filename)
        
        if match:
            base_name = match.group(1)
            band_num = int(match.group(2))
            
            # Validate band number (1-6 for 6-band multispectral)
            if 1 <= band_num <= 6:
                return (base_name, band_num)
        
        return None
    
    @staticmethod
    def group_images(file_paths: List[str]) -> Dict[str, MultispectralSet]:
        """
        Group images by base name and validate completeness
        
        Args:
            file_paths: List of image file paths
            
        Returns:
            Dictionary of base_name -> MultispectralSet
            
        Example:
            Input: [
                'IMG_0197_1.jpg', 'IMG_0197_2.jpg', ..., 'IMG_0197_6.jpg',
                'IMG_0198_1.jpg', 'IMG_0198_2.jpg'  # Only 2 bands
            ]
            
            Output: {
                'IMG_0197': MultispectralSet(is_complete=True, ...),
                'IMG_0198': MultispectralSet(is_complete=False, missing=[3,4,5,6])
            }
        """
        groups: Dict[str, Dict[int, str]] = {}
        
        # Group files by base name
        for file_path in file_paths:
            filename = Path(file_path).name
            parsed = MultispectralProcessor.parse_filename(filename)
            
            if parsed:
                base_name, band_num = parsed
                
                if base_name not in groups:
                    groups[base_name] = {}
                
                groups[base_name][band_num] = file_path
            else:
                logger.warning(f"Skipping invalid filename: {filename}")
        
        # Create MultispectralSet objects with validation
        result = {}
        for base_name, bands in groups.items():
            expected_bands = set(range(1, 7))  # Bands 1-6
            present_bands = set(bands.keys())
            missing_bands = sorted(expected_bands - present_bands)
            is_complete = len(missing_bands) == 0
            
            result[base_name] = MultispectralSet(
                base_name=base_name,
                band_paths=bands,
                is_complete=is_complete,
                missing_bands=missing_bands
            )
            
            if is_complete:
                logger.info(f"✅ Complete set found: {base_name} (6 bands)")
            else:
                logger.warning(
                    f"⚠️ Incomplete set: {base_name} - Missing bands {missing_bands}"
                )
        
        return result
    
    @staticmethod
    def filter_complete_sets(
        multispectral_sets: Dict[str, MultispectralSet]
    ) -> Dict[str, MultispectralSet]:
        """
        Filter only complete 6-band sets
        
        Args:
            multispectral_sets: All grouped sets
            
        Returns:
            Only complete sets (have all 6 bands)
        """
        complete = {
            name: mset 
            for name, mset in multispectral_sets.items() 
            if mset.is_complete
        }
        
        discarded_count = len(multispectral_sets) - len(complete)
        if discarded_count > 0:
            logger.info(f"📊 Processing {len(complete)} complete sets")
            logger.info(f"🗑️ Discarding {discarded_count} incomplete sets")
        
        return complete
    
    @staticmethod
    def create_false_color_composite(
        band_paths: Dict[int, str],
        output_path: Optional[str] = None,
        normalize: bool = True,
        use_parallel: bool = True
    ) -> np.ndarray:
        """
        Create False Color Composite (CIR) for vegetation analysis
        
        Composite: NIR-Red-Green (Bands 5-3-2)
        - Healthy vegetation appears RED (high NIR reflection)
        - Water appears DARK BLUE/BLACK (absorbs NIR)
        - Soil appears BROWN/GRAY
        - Stressed plants appear less red (reduced NIR)
        
        Args:
            band_paths: Dictionary {1: path, 2: path, ..., 6: path}
            output_path: Optional path to save composite image
            normalize: Whether to normalize band values to 0-255
            use_parallel: Load bands in parallel for speed (default True)
            
        Returns:
            RGB numpy array (height, width, 3)
        """
        logger.info("Creating False Color Composite (NIR-R-G)...")
        
        # Load required bands (5, 3, 2) - PARALLEL for speed
        if use_parallel:
            required_bands = {5: band_paths[5], 3: band_paths[3], 2: band_paths[2]}
            loaded = MultispectralProcessor.load_bands_parallel(required_bands)
            band_5_nir = loaded[5]
            band_3_red = loaded[3]
            band_2_green = loaded[2]
        else:
            # Sequential loading (slower)
            def load_band(path: str) -> np.ndarray:
                """Load and normalize a band image (handles TIFF, JPEG, PNG)"""
                img = Image.open(path)
                arr = np.array(img)
                if len(arr.shape) == 3:
                    arr = arr[:, :, 0]
                arr = arr.astype(np.float32)
                logger.info(f"  Loaded: shape={arr.shape}, range={arr.min():.2f}-{arr.max():.2f}")
                return arr
            
            band_5_nir = load_band(band_paths[5])
            band_3_red = load_band(band_paths[3])
            band_2_green = load_band(band_paths[2])
        
        # Normalize bands with contrast stretch
        def normalize_band(band: np.ndarray) -> np.ndarray:
            """Normalize band to 0-255 range with contrast stretch"""
            p2, p98 = np.percentile(band, (2, 98))
            if p98 - p2 < 1e-8:
                return np.zeros_like(band, dtype=np.uint8)
            
            band_clipped = np.clip(band, p2, p98)
            band_norm = ((band_clipped - p2) / (p98 - p2) * 255).astype(np.uint8)
            
            logger.info(f"  Normalized: p2={p2:.2f}, p98={p98:.2f}, output={band_norm.min()}-{band_norm.max()}")
            return band_norm
        
        nir_norm = normalize_band(band_5_nir)
        red_norm = normalize_band(band_3_red)
        green_norm = normalize_band(band_2_green)
        
        # Stack into RGB (NIR -> R, Red -> G, Green -> B)
        composite = np.dstack([nir_norm, red_norm, green_norm])
        
        logger.info(f"📊 Composite: {composite.shape}, range={composite.min()}-{composite.max()}")
        
        if output_path:
            Image.fromarray(composite).save(output_path, quality=95)
            logger.info(f"💾 Saved to: {output_path}")
        
        logger.info("✅ False Color Composite created")
        return composite
    
    @staticmethod
    def create_true_color_composite(
        band_paths: Dict[int, str],
        output_path: Optional[str] = None,
        normalize: bool = True,
        use_parallel: bool = True
    ) -> np.ndarray:
        """
        Create True Color Composite (looks like normal photo)
        
        Composite: Red-Green-Blue (Bands 3-2-1)
        - Looks like a standard RGB photo
        - Useful for visual reference
        
        Args:
            band_paths: Dictionary {1: path, 2: path, ..., 6: path}
            output_path: Optional path to save composite image
            normalize: Whether to normalize band values to 0-255
            use_parallel: Load bands in parallel for speed (default True)
            
        Returns:
            RGB numpy array (height, width, 3)
        """
        logger.info("Creating True Color Composite (R-G-B)...")
        
        # Load visible bands in parallel
        if use_parallel:
            required_bands = {3: band_paths[3], 2: band_paths[2], 1: band_paths[1]}
            loaded = MultispectralProcessor.load_bands_parallel(required_bands)
            band_3_red = loaded[3]
            band_2_green = loaded[2]
            band_1_blue = loaded[1]
        else:
            def load_band(path: str) -> np.ndarray:
                img = Image.open(path)
                arr = np.array(img)
                if len(arr.shape) == 3:
                    arr = arr[:, :, 0]
                return arr.astype(np.float32)
            
            band_3_red = load_band(band_paths[3])
            band_2_green = load_band(band_paths[2])
            band_1_blue = load_band(band_paths[1])
        
        def normalize_band(band: np.ndarray) -> np.ndarray:
            """Normalize band to 0-255 with contrast stretch"""
            p2, p98 = np.percentile(band, (2, 98))
            if p98 - p2 < 1e-8:
                return np.zeros_like(band, dtype=np.uint8)
            band_clipped = np.clip(band, p2, p98)
            return ((band_clipped - p2) / (p98 - p2) * 255).astype(np.uint8)
        
        red_norm = normalize_band(band_3_red)
        green_norm = normalize_band(band_2_green)
        blue_norm = normalize_band(band_1_blue)
        
        composite = np.dstack([red_norm, green_norm, blue_norm])
        
        if output_path:
            Image.fromarray(composite).save(output_path, quality=95)
            logger.info(f"💾 Saved to: {output_path}")
        
        logger.info("✅ True Color Composite created")
        return composite
    
    @staticmethod
    def calculate_ndvi(
        band_paths: Dict[int, str],
        use_parallel: bool = True
    ) -> np.ndarray:
        """
        Calculate NDVI (Normalized Difference Vegetation Index)
        
        NDVI = (NIR - Red) / (NIR + Red)
        
        Values:
        - -1 to 0: Water, bare soil, rock, snow
        - 0 to 0.2: Bare soil, sparse vegetation
        - 0.2 to 0.5: Moderate vegetation
        - 0.5 to 1.0: Dense, healthy vegetation
        
        Args:
            band_paths: Dictionary {1: path, 2: path, ..., 6: path}
            use_parallel: Load bands in parallel (default True)
            
        Returns:
            NDVI array (values from -1 to 1)
        """
        logger.info("Calculating NDVI...")
        
        # Load NIR and Red bands
        if use_parallel:
            required_bands = {5: band_paths[5], 3: band_paths[3]}
            loaded = MultispectralProcessor.load_bands_parallel(required_bands)
            nir = loaded[5]
            red = loaded[3]
        else:
            def load_band(path: str) -> np.ndarray:
                img = Image.open(path)
                arr = np.array(img)
                if len(arr.shape) == 3:
                    arr = arr[:, :, 0]
                return arr.astype(np.float32)
            
            nir = load_band(band_paths[5])
            red = load_band(band_paths[3])
        
        logger.info(f"  NIR: {nir.min():.2f}-{nir.max():.2f}")
        logger.info(f"  Red: {red.min():.2f}-{red.max():.2f}")
        
        # Calculate NDVI with epsilon to avoid division by zero
        ndvi = (nir - red) / (nir + red + 1e-8)
        
        # Clip to valid range [-1, 1]
        ndvi = np.clip(ndvi, -1, 1)
        
        logger.info(f"✅ NDVI: [{ndvi.min():.3f}, {ndvi.max():.3f}]")
        return ndvi
    
    @staticmethod
    def visualize_ndvi(
        ndvi: np.ndarray,
        output_path: Optional[str] = None,
        colormap: str = 'RdYlGn'
    ) -> np.ndarray:
        """
        Create color visualization of NDVI
        
        Args:
            ndvi: NDVI array from calculate_ndvi()
            output_path: Optional path to save visualization
            colormap: Matplotlib colormap name (default: RdYlGn - Red-Yellow-Green)
            
        Returns:
            RGB image (height, width, 3) with color-coded NDVI
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib import cm
            
            # Normalize NDVI to 0-1 for colormap
            ndvi_norm = (ndvi + 1) / 2.0  # [-1, 1] -> [0, 1]
            
            # Apply colormap
            cmap = cm.get_cmap(colormap)
            colored = cmap(ndvi_norm)
            
            # Convert to RGB (0-255)
            rgb = (colored[:, :, :3] * 255).astype(np.uint8)
            
            if output_path:
                Image.fromarray(rgb).save(output_path)
                logger.info(f"💾 Saved NDVI visualization to: {output_path}")
            
            return rgb
            
        except ImportError:
            logger.warning("Matplotlib not available - using grayscale NDVI")
            # Fallback: grayscale visualization
            ndvi_normalized = ((ndvi + 1) / 2.0 * 255).astype(np.uint8)
            gray_rgb = np.dstack([ndvi_normalized] * 3)
            
            if output_path:
                Image.fromarray(gray_rgb).save(output_path)
            
            return gray_rgb
    
    @staticmethod
    def create_detection_image(
        band_paths: Dict[int, str],
        band_choice: int = 2,
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """
        Create YOLO-compatible detection image from single band (NO alignment issues)
        
        WHY: Multispectral bands are often misaligned - composites show RGB shift.
        YOLO was trained on aligned RGB photos, so use single sharp band instead.
        
        RECOMMENDED BANDS:
        - Band 2 (Green): Best for fruit detection (good contrast, sharp)
        - Band 3 (Red): Alternative for ripe fruit
        - Band 1 (Blue): Least recommended (more noise)
        
        Args:
            band_paths: Dictionary {1: path, 2: path, ..., 6: path}
            band_choice: Which band to use (default 2 = Green)
            output_path: Optional path to save detection image
            
        Returns:
            RGB numpy array (height, width, 3) - grayscale converted to RGB for YOLO
        """
        logger.info(f"Creating detection image from Band {band_choice}...")
        
        # Load single band
        img = Image.open(band_paths[band_choice])
        arr = np.array(img)
        
        # Handle multi-channel
        if len(arr.shape) == 3:
            arr = arr[:, :, 0]
        
        # Convert to float for processing
        arr = arr.astype(np.float32)
        
        logger.info(f"  Band {band_choice}: shape={arr.shape}, range={arr.min():.0f}-{arr.max():.0f}")
        
        # Normalize with contrast stretch
        p2, p98 = np.percentile(arr, (2, 98))
        if p98 - p2 > 1e-8:
            arr_clipped = np.clip(arr, p2, p98)
            arr_norm = ((arr_clipped - p2) / (p98 - p2) * 255).astype(np.uint8)
        else:
            arr_norm = np.zeros_like(arr, dtype=np.uint8)
        
        # Convert grayscale to RGB (YOLO expects 3 channels)
        rgb = np.dstack([arr_norm, arr_norm, arr_norm])
        
        logger.info(f"✅ Detection image created: {rgb.shape}")
        
        if output_path:
            Image.fromarray(rgb).save(output_path, quality=95)
            logger.info(f"💾 Saved detection image to: {output_path}")
        
        return rgb
    
    @staticmethod
    def resize_for_speed(
        image_array: np.ndarray,
        max_dimension: int = 1280
    ) -> np.ndarray:
        """
        Resize image to reduce processing time (optional optimization)
        
        Args:
            image_array: Input image array
            max_dimension: Maximum width or height
            
        Returns:
            Resized image array
        """
        height, width = image_array.shape[:2]
        
        if max(height, width) <= max_dimension:
            return image_array
        
        # Calculate new dimensions
        if width > height:
            new_width = max_dimension
            new_height = int(height * (max_dimension / width))
        else:
            new_height = max_dimension
            new_width = int(width * (max_dimension / height))
        
        # Resize
        img = Image.fromarray(image_array)
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        
        logger.info(f"⚡ Resized from {width}x{height} to {new_width}x{new_height}")
        
        return np.array(img_resized)
    
    @staticmethod
    def _convert_to_degrees(value):
        """Convert GPS coordinates to decimal degrees"""
        try:
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        except:
            return None
    
    @staticmethod
    def extract_gps_from_bands(band_paths: Dict[int, str]) -> Optional[Dict]:
        """
        Extract GPS metadata from any band and convert to decimal degrees
        
        Args:
            band_paths: Dictionary {1: path, 2: path, ..., 6: path}
            
        Returns:
            Dictionary with lat, lon, altitude in decimal degrees or None
        """
        try:
            from PIL.ExifTags import TAGS, GPSTAGS
            
            # Try each band (start with Band 1)
            for band_num in sorted(band_paths.keys()):
                img = Image.open(band_paths[band_num])
                exif = img._getexif()
                
                if not exif:
                    continue
                
                gps_info = None
                for tag, value in exif.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name == 'GPSInfo':
                        gps_info = {}
                        for gps_tag in value:
                            sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                            gps_info[sub_tag_name] = value[gps_tag]
                        break
                
                if not gps_info:
                    continue
                
                # Convert to decimal degrees
                lat = None
                lon = None
                altitude = None
                
                # Get latitude
                if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
                    lat = MultispectralProcessor._convert_to_degrees(gps_info['GPSLatitude'])
                    if gps_info['GPSLatitudeRef'] == 'S':
                        lat = -lat
                
                # Get longitude  
                if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
                    lon = MultispectralProcessor._convert_to_degrees(gps_info['GPSLongitude'])
                    if gps_info['GPSLongitudeRef'] == 'W':
                        lon = -lon
                
                # Get altitude
                if 'GPSAltitude' in gps_info:
                    try:
                        altitude = float(gps_info['GPSAltitude'])
                    except:
                        altitude = None
                
                if lat is not None and lon is not None:
                    result = {
                        'latitude': lat,
                        'longitude': lon,
                        'altitude': altitude
                    }
                    logger.info(f"📍 GPS data from Band {band_num}: lat={lat:.6f}, lon={lon:.6f}, alt={altitude}")
                    return result
            
            logger.warning("⚠️ No GPS data found in any band")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting GPS: {e}")
            import traceback
            traceback.print_exc()
            return None


# Example usage
if __name__ == "__main__":
    # Example: Group uploaded images
    uploaded_files = [
        "uploads/IMG_0197_1.jpg",
        "uploads/IMG_0197_2.jpg",
        "uploads/IMG_0197_3.jpg",
        "uploads/IMG_0197_4.jpg",
        "uploads/IMG_0197_5.jpg",
        "uploads/IMG_0197_6.jpg",
        "uploads/IMG_0198_1.jpg",  # Incomplete set
        "uploads/IMG_0198_2.jpg",
    ]
    
    # Group and validate
    all_sets = MultispectralProcessor.group_images(uploaded_files)
    complete_sets = MultispectralProcessor.filter_complete_sets(all_sets)
    
    # Process each complete set
    for base_name, mset in complete_sets.items():
        print(f"\nProcessing {base_name}...")
        
        # Create False Color Composite (best for vegetation)
        composite = MultispectralProcessor.create_false_color_composite(
            mset.band_paths,
            output_path=f"outputs/{base_name}_false_color.jpg"
        )
        
        # Calculate NDVI
        ndvi = MultispectralProcessor.calculate_ndvi(mset.band_paths)
        
        # Visualize NDVI
        ndvi_viz = MultispectralProcessor.visualize_ndvi(
            ndvi,
            output_path=f"outputs/{base_name}_ndvi.jpg"
        )
        
        print(f"✅ {base_name} processed successfully")
