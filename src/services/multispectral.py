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
import os
from concurrent.futures import ThreadPoolExecutor

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False
    
try:
    import rasterio
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False

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
    def create_aligned_rgb_composite(
        band_paths: Dict[int, str],
        output_path: Optional[str] = None,
        use_parallel: bool = True
    ) -> np.ndarray:
        """
        Create TRUE RGB composite with band alignment using AKAZE feature matching
        
        WHY: Multispectral cameras have 6 separate sensors at different positions.
        This causes parallax → bands are misaligned → RGB shift in composites.
        SOLUTION: Align Band 1 (Blue) and Band 3 (Red) to Band 2 (Green) using feature matching.
        
        PROCESS:
        1. Load RGB bands (1=Blue, 2=Green, 3=Red)
        2. Use Band 2 (Green) as reference (middle wavelength, best SNR)
        3. Detect features with AKAZE (fast, accurate)
        4. Match features between bands
        5. Compute homography (perspective transformation)
        6. Warp misaligned bands to align with reference
        7. Stack R-G-B → True color composite
        8. Enhance with CLAHE
        
        Args:
            band_paths: Dictionary {1: path, 2: path, ..., 6: path}
            output_path: Optional path to save composite
            use_parallel: Load bands in parallel (faster)
            
        Returns:
            RGB numpy array (height, width, 3) - aligned true color composite
        """
        logger.info("🎨 Creating ALIGNED RGB composite with AKAZE...")
        
        if not OPENCV_AVAILABLE:
            logger.warning("⚠️ OpenCV not available - falling back to unaligned composite")
            return MultispectralProcessor._create_simple_rgb_composite(band_paths, output_path, use_parallel)
        
        # Load RGB bands in parallel
        if use_parallel:
            required_bands = {1: band_paths[1], 2: band_paths[2], 3: band_paths[3]}
            loaded = MultispectralProcessor.load_bands_parallel(required_bands)
            band_1_blue = loaded[1]
            band_2_green = loaded[2]
            band_3_red = loaded[3]
        else:
            band_1_blue = np.array(Image.open(band_paths[1])).astype(np.float32)
            band_2_green = np.array(Image.open(band_paths[2])).astype(np.float32)
            band_3_red = np.array(Image.open(band_paths[3])).astype(np.float32)
        
        # Handle multi-channel images (take first channel)
        if len(band_1_blue.shape) == 3:
            band_1_blue = band_1_blue[:, :, 0]
        if len(band_2_green.shape) == 3:
            band_2_green = band_2_green[:, :, 0]
        if len(band_3_red.shape) == 3:
            band_3_red = band_3_red[:, :, 0]
        
        logger.info(f"  Loaded bands: Blue={band_1_blue.shape}, Green={band_2_green.shape}, Red={band_3_red.shape}")
        
        # Use Band 2 (Green) as reference for alignment
        reference = band_2_green.copy()
        
        # Normalize bands to 8-bit for feature detection
        def normalize_to_uint8(band):
            p2, p98 = np.percentile(band, (2, 98))
            if p98 - p2 > 1e-8:
                clipped = np.clip(band, p2, p98)
                normalized = ((clipped - p2) / (p98 - p2) * 255).astype(np.uint8)
            else:
                normalized = np.zeros_like(band, dtype=np.uint8)
            return normalized
        
        ref_uint8 = normalize_to_uint8(reference)
        blue_uint8 = normalize_to_uint8(band_1_blue)
        red_uint8 = normalize_to_uint8(band_3_red)
        
        # Align Blue and Red bands to Green reference
        logger.info("  🔍 Aligning Blue band to Green reference...")
        aligned_blue = MultispectralProcessor._align_band_akaze(blue_uint8, ref_uint8)
        
        logger.info("  🔍 Aligning Red band to Green reference...")
        aligned_red = MultispectralProcessor._align_band_akaze(red_uint8, ref_uint8)
        
        # Stack as RGB (Red, Green, Blue)
        rgb = np.dstack([aligned_red, ref_uint8, aligned_blue])
        
        # Apply CLAHE for contrast enhancement
        logger.info("  ✨ Applying CLAHE contrast enhancement...")
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        rgb[:, :, 0] = clahe.apply(rgb[:, :, 0])  # Red
        rgb[:, :, 1] = clahe.apply(rgb[:, :, 1])  # Green
        rgb[:, :, 2] = clahe.apply(rgb[:, :, 2])  # Blue
        
        logger.info(f"✅ Aligned RGB composite created: {rgb.shape}")
        
        if output_path:
            Image.fromarray(rgb).save(output_path, quality=95)
            logger.info(f"💾 Saved aligned composite to: {output_path}")
        
        return rgb
    
    @staticmethod
    def _align_band_akaze(source: np.ndarray, reference: np.ndarray) -> np.ndarray:
        """
        Align source band to reference band using AKAZE feature matching
        
        Args:
            source: Band to align (uint8)
            reference: Reference band (uint8)
            
        Returns:
            Aligned source band (uint8)
        """
        try:
            # Create AKAZE detector
            detector = cv2.AKAZE_create()
            
            # Detect keypoints and compute descriptors
            kp1, desc1 = detector.detectAndCompute(source, None)
            kp2, desc2 = detector.detectAndCompute(reference, None)
            
            if desc1 is None or desc2 is None or len(kp1) < 4 or len(kp2) < 4:
                logger.warning("    ⚠️ Not enough features detected - using unaligned band")
                return source
            
            # Match features using BFMatcher
            matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            matches = matcher.knnMatch(desc1, desc2, k=2)
            
            # Apply ratio test (Lowe's ratio test)
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)
            
            logger.info(f"    Found {len(good_matches)} good matches out of {len(matches)} total")
            
            if len(good_matches) < 10:
                logger.warning("    ⚠️ Not enough good matches - using unaligned band")
                return source
            
            # Extract matched keypoints
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            
            # Compute homography
            H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            
            if H is None:
                logger.warning("    ⚠️ Failed to compute homography - using unaligned band")
                return source
            
            # Warp source to align with reference
            height, width = reference.shape
            aligned = cv2.warpPerspective(source, H, (width, height))
            
            logger.info(f"    ✅ Band aligned successfully")
            return aligned
            
        except Exception as e:
            logger.error(f"    ❌ Alignment failed: {e} - using unaligned band")
            return source
    
    @staticmethod
    def _create_simple_rgb_composite(
        band_paths: Dict[int, str],
        output_path: Optional[str] = None,
        use_parallel: bool = True
    ) -> np.ndarray:
        """
        Fallback: Create simple (unaligned) RGB composite
        Used when OpenCV is not available
        """
        logger.info("Creating simple RGB composite (no alignment)...")
        
        # Load RGB bands
        if use_parallel:
            required_bands = {1: band_paths[1], 2: band_paths[2], 3: band_paths[3]}
            loaded = MultispectralProcessor.load_bands_parallel(required_bands)
            band_1_blue = loaded[1]
            band_2_green = loaded[2]
            band_3_red = loaded[3]
        else:
            band_1_blue = np.array(Image.open(band_paths[1])).astype(np.float32)
            band_2_green = np.array(Image.open(band_paths[2])).astype(np.float32)
            band_3_red = np.array(Image.open(band_paths[3])).astype(np.float32)
        
        # Normalize each band
        def normalize_band(band):
            if len(band.shape) == 3:
                band = band[:, :, 0]
            p2, p98 = np.percentile(band, (2, 98))
            if p98 - p2 > 1e-8:
                clipped = np.clip(band, p2, p98)
                return ((clipped - p2) / (p98 - p2) * 255).astype(np.uint8)
            return np.zeros_like(band, dtype=np.uint8)
        
        r = normalize_band(band_3_red)
        g = normalize_band(band_2_green)
        b = normalize_band(band_1_blue)
        
        rgb = np.dstack([r, g, b])
        
        if output_path:
            Image.fromarray(rgb).save(output_path, quality=95)
        
        return rgb
    
    @staticmethod
    def create_detection_image(
        band_paths: Dict[int, str],
        band_choice: int = 2,
        output_path: Optional[str] = None
    ) -> np.ndarray:
        """
        DEPRECATED: Use create_aligned_rgb_composite instead
        
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
        """Convert GPS coordinates to decimal degrees
        
        Handles tuple/list of (degrees, minutes, seconds) which can be:
        - plain floats/ints
        - fractions.Fraction objects  
        - tuples of the above
        """
        try:
            # Handle Fraction objects and convert to float
            if len(value) < 3:
                logger.warning(f"⚠️ GPS value has < 3 components: {value}")
                return None
            
            d = float(value[0])  # Degrees
            m = float(value[1])  # Minutes
            s = float(value[2])  # Seconds
            
            result = d + (m / 60.0) + (s / 3600.0)
            logger.debug(f"   GPS conversion: {d}° {m}' {s}\" → {result:.6f}°")
            return result
        except Exception as conv_err:
            logger.warning(f"⚠️ Failed to convert GPS value {value}: {conv_err}")
            return None
    
    @staticmethod
    def _extract_gps_from_exifread(tiff_path: str) -> Optional[Dict]:
        """Extract GPS using exifread library - more robust for TIFF files
        
        exifread is specifically designed for reading EXIF data and handles
        TIFF files better than Pillow's getexif().
        """
        try:
            import exifread
            logger.info(f"   📖 Using exifread to read {os.path.basename(tiff_path)}")
            
            with open(tiff_path, 'rb') as f:
                tags = exifread.process_file(f, details=False)
                logger.debug(f"      Found {len(tags)} tags via exifread")
                
                # Look for GPS tags
                gps_tags = {k: v for k, v in tags.items() if 'GPS' in k}
                if gps_tags:
                    logger.info(f"      ✅ Found GPS tags: {list(gps_tags.keys())}")
                    
                    # Extract GPS coordinates
                    if 'GPS GPSLatitude' in gps_tags and 'GPS GPSLongitude' in gps_tags:
                        lat_val = gps_tags['GPS GPSLatitude'].values
                        lon_val = gps_tags['GPS GPSLongitude'].values
                        alt_val = gps_tags.get('GPS GPSAltitude')
                        
                        logger.info(f"      Raw GPS - Lat: {lat_val}, Lon: {lon_val}")
                        
                        # Convert to decimal degrees
                        lat = MultispectralProcessor._convert_to_degrees(lat_val)
                        lon = MultispectralProcessor._convert_to_degrees(lon_val)
                        
                        # Handle reference (N/S, E/W)
                        lat_ref = gps_tags.get('GPS GPSLatitudeRef')
                        lon_ref = gps_tags.get('GPS GPSLongitudeRef')
                        
                        if lat_ref and str(lat_ref).strip() == 'S':
                            lat = -lat
                        if lon_ref and str(lon_ref).strip() == 'W':
                            lon = -lon
                        
                        alt = None
                        if alt_val:
                            try:
                                alt = float(alt_val.values)
                            except:
                                pass
                        
                        logger.info(f"      ✅ Converted - Lat: {lat:.6f}, Lon: {lon:.6f}, Alt: {alt}")
                        
                        return {
                            'gps_latitude': lat,
                            'gps_longitude': lon,
                            'gps_altitude': alt
                        }
                
                logger.debug(f"      No GPS tags found via exifread")
            
            return None
            
        except ImportError:
            logger.debug(f"   💡 exifread not available (install: pip install exifread)")
            return None
        except Exception as e:
            logger.warning(f"   ⚠️ exifread extraction error: {e}")
            return None
    
    @staticmethod
    def _extract_gps_from_tiff_tags(tiff_path: str) -> Optional[Dict]:
        """Extract GPS from TIFF-specific tag structures
        
        TIFF files can store EXIF differently than JPEG.
        This tries multiple approaches:
        1. Read all TIFF tags
        2. Look for EXIF SubIFD (tag 34665)
        3. Extract GPS from there
        """
        try:
            logger.info(f"   🔨 Reading TIFF tags directly from {os.path.basename(tiff_path)}")
            
            img = Image.open(tiff_path)
            
            # Method 1: Try to get EXIF from getexif() with all IFDs
            try:
                exif_data = img.getexif()
                if exif_data:
                    logger.debug(f"   📝 Found {len(exif_data)} EXIF tags")
                    
                    # Look for GPS Info tag directly
                    for tag_num, value in exif_data.items():
                        tag_name = TAGS.get(tag_num, tag_num)
                        logger.debug(f"      Tag {tag_num} ({tag_name}): {type(value).__name__}")
                        
                        if tag_name == 'GPSInfo' or tag_num == 34853:
                            logger.info(f"      ✅ Found GPSInfo!")
                            gps_info = {}
                            try:
                                if isinstance(value, dict):
                                    for gps_tag, gps_val in value.items():
                                        sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                                        gps_info[sub_tag_name] = gps_val
                                else:
                                    logger.debug(f"      Trying value.items()...")
                                    for gps_tag, gps_val in value.items():
                                        sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                                        gps_info[sub_tag_name] = gps_val
                                
                                if gps_info:
                                    logger.info(f"      Extracted GPS tags: {list(gps_info.keys())}")
                                    return gps_info
                            except Exception as e:
                                logger.warning(f"      Failed to parse GPSInfo: {e}")
            except Exception as e:
                logger.debug(f"   getexif() error: {e}")
            
            # Method 2: Try reading all TIFF tags with tag() method
            try:
                logger.debug(f"   Trying Image.tag() method...")
                all_tags = img.tag_v2 if hasattr(img, 'tag_v2') else {}
                if all_tags:
                    logger.debug(f"   Found {len(all_tags)} TIFF tags via tag_v2")
                    # Log tag names for debugging
                    tag_names = [TAGS.get(t, t) for t in list(all_tags.keys())[:20]]
                    logger.debug(f"   Tags: {tag_names}")
            except Exception as e:
                logger.debug(f"   tag_v2 error: {e}")
            
            logger.info(f"   ❌ No GPS found via TIFF tag methods")
            return None
            
        except Exception as e:
            logger.warning(f"   Error reading TIFF tags: {e}")
            return None
    
    @staticmethod
    def _extract_gps_from_rasterio(tiff_path: str) -> Optional[Dict]:
        """Extract GPS coordinates from TIFF file using rasterio
        
        Rasterio is better at handling geospatial TIFF metadata and georeference info.
        """
        try:
            import rasterio
            
            logger.debug(f"   🔨 Attempting rasterio GPS extraction from {os.path.basename(tiff_path)}")
            
            with rasterio.open(tiff_path) as src:
                # Method 1: Try to get bounds and calculate center point
                bounds = src.bounds
                if bounds and bounds != (0, 0, 0, 0):
                    # bounds = (left, bottom, right, top)
                    center_lon = (bounds.left + bounds.right) / 2
                    center_lat = (bounds.bottom + bounds.top) / 2
                    logger.info(f"      ✅ Rasterio extracted center: lat={center_lat:.6f}, lon={center_lon:.6f}")
                    return {
                        'gps_latitude': center_lat,
                        'gps_longitude': center_lon,
                        'gps_altitude': None
                    }
                
                logger.debug(f"      ⚠️ Rasterio: No bounds/GPS available")
                return None
                
        except ImportError:
            logger.debug(f"   💡 Rasterio not available (install: pip install rasterio)")
            return None
        except Exception as rio_err:
            logger.debug(f"   ⚠️ Rasterio extraction error: {rio_err}")
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
            
            logger.info(f"\n🧭 [MAPVIEW] Starting GPS extraction from {len(band_paths)} bands...")
            
            # Try each band (start with Band 1)
            for band_num in sorted(band_paths.keys()):
                band_file = band_paths[band_num]
                logger.info(f"   🔍 Band {band_num}: Scanning {os.path.basename(band_file)}")
                logger.info(f"      File path: {band_file}")
                
                img = Image.open(band_file)
                logger.debug(f"      File format: {img.format}, Mode: {img.mode}")
                
                # Use modern Pillow API (getexif instead of _getexif)
                exif = img.getexif()
                
                if not exif:
                    logger.warning(f"      ⚠️ No EXIF IFD found via Pillow getexif()")
                    
                    # For TIFF files, try rasterio as fallback (better for geospatial TIFF)
                    if band_file.lower().endswith(('.tif', '.tiff')):
                        logger.info(f"      💡 Trying rasterio for TIFF file...")
                        try:
                            import rasterio
                            with rasterio.open(band_file) as src:
                                # Get tags (EXIF-like metadata)
                                tags = src.tags()
                                if tags:
                                    logger.debug(f"      ✓ Rasterio tags: {list(tags.keys())}")
                                
                                # Get bounds (georeferencing)
                                bounds = src.bounds
                                if bounds:
                                    logger.debug(f"      📍 Rasterio bounds: {bounds}")
                        except ImportError:
                            logger.warning(f"      ⚠️ Rasterio not installed - install: pip install rasterio")
                        except Exception as rio_err:
                            logger.warning(f"      ⚠️ Rasterio error: {rio_err}")
                    
                    logger.debug(f"      💭 Skipping Band {band_num}: No EXIF data")
                    continue
                else:
                    logger.debug(f"      ✓ EXIF data found, {len(exif)} tags")
                    # Show all EXIF tags for debugging
                    exif_tags = [TAGS.get(tag, tag) for tag in exif.keys()]
                    logger.debug(f"      EXIF tags: {exif_tags[:10]}" + ("..." if len(exif_tags) > 10 else ""))
                
                gps_info = None
                for tag, value in exif.items():
                    tag_name = TAGS.get(tag, tag)
                    if tag_name == 'GPSInfo':
                        logger.info(f"      ✅ Found GPSInfo tag!")
                        gps_info = {}
                        try:
                            # Modern Pillow returns GPSInfo as dict-like object (IFDInfo)
                            # Handle both dict and dict-like objects
                            if isinstance(value, dict):
                                gps_items = value.items()
                            else:
                                # Try to treat as dict-like object
                                gps_items = value.items() if hasattr(value, 'items') else []
                            
                            for gps_tag, gps_value in gps_items:
                                sub_tag_name = GPSTAGS.get(gps_tag, gps_tag)
                                gps_info[sub_tag_name] = gps_value
                        except Exception as gps_parse_err:
                            logger.warning(f"⚠️ Failed to parse GPSInfo: {gps_parse_err}")
                            gps_info = None
                        
                        # Debug: Show what was parsed
                        if gps_info:
                            logger.debug(f"   ✓ Parsed GPSInfo keys: {list(gps_info.keys())}")
                        break
                
                # After loop: Check if GPSInfo tag was ever found
                if gps_info is None and exif:
                    logger.warning(f"      ⚠️ GPSInfo tag NOT found in EXIF data")
                    logger.warning(f"      📝 Available EXIF tags (first 20): {[TAGS.get(t, t) for t in list(exif.keys())[:20]]}")
                
                if not gps_info:
                    logger.debug(f"💭 Band {band_num}: No GPS data in EXIF")
                    continue
                
                # Convert to decimal degrees
                lat = None
                lon = None
                altitude = None
                
                # Get latitude
                if 'GPSLatitude' in gps_info and 'GPSLatitudeRef' in gps_info:
                    logger.debug(f"   GPS Latitude data: {gps_info['GPSLatitude']}")
                    lat = MultispectralProcessor._convert_to_degrees(gps_info['GPSLatitude'])
                    if lat is not None and gps_info['GPSLatitudeRef'] == 'S':
                        lat = -lat
                    logger.debug(f"   → Converted latitude: {lat}")
                
                # Get longitude  
                if 'GPSLongitude' in gps_info and 'GPSLongitudeRef' in gps_info:
                    logger.debug(f"   GPS Longitude data: {gps_info['GPSLongitude']}")
                    lon = MultispectralProcessor._convert_to_degrees(gps_info['GPSLongitude'])
                    if lon is not None and gps_info['GPSLongitudeRef'] == 'W':
                        lon = -lon
                    logger.debug(f"   → Converted longitude: {lon}")
                
                # Get altitude
                if 'GPSAltitude' in gps_info:
                    try:
                        # GPSAltitude can be a Fraction or float
                        alt_value = gps_info['GPSAltitude']
                        altitude = float(alt_value)
                        logger.debug(f"   GPS Altitude: {altitude}m")
                    except Exception as alt_err:
                        logger.warning(f"   ⚠️ Failed to parse altitude: {alt_err}")
                        altitude = None
                
                if lat is not None and lon is not None:
                    result = {
                        'gps_latitude': lat,
                        'gps_longitude': lon,
                        'gps_altitude': altitude
                    }
                    logger.info("="*80)
                    logger.info(f"✅ [MAPVIEW-GPS-SUCCESS] GPS extracted from Band {band_num}")
                    logger.info(f"📍 Coordinates: lat={lat:.6f}, lon={lon:.6f}, alt={altitude}")
                    logger.info(f"🗺️  Map will DISPLAY this location ✓")
                    logger.info("="*80)
                    print("\n" + "="*80)
                    print(f"✅ SUCCESS: GPS data extracted and will be stored in database")
                    print(f"   📍 lat={lat:.6f}, lon={lon:.6f}")
                    print("="*80 + "\n")
                    return result
                else:
                    logger.warning(f"⚠️ Band {band_num}: Incomplete GPS data (lat={lat}, lon={lon})")
            
            # Fallback: Try rasterio for TIFF files if Pillow extraction failed
            logger.info("\n🔄 [MAPVIEW] Pillow extraction failed, trying specialized TIFF extraction...")
            for band_num in sorted(band_paths.keys()):
                band_file = band_paths[band_num]
                if band_file.lower().endswith(('.tif', '.tiff')):
                    logger.info(f"   🔍 Attempting TIFF-specific extraction on Band {band_num}...")
                    logger.info(f"      Calling _extract_gps_from_exifread()...")
                    
                    # Try exifread FIRST - it's best at reading TIFF EXIF data
                    gps_result = MultispectralProcessor._extract_gps_from_exifread(band_file)
                    logger.info(f"      Result from exifread: {gps_result is not None}")
                    
                    if gps_result and 'gps_latitude' in gps_result:
                        # Validate coordinates are realistic
                        lat = gps_result.get('gps_latitude', 0)
                        lon = gps_result.get('gps_longitude', 0)
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            logger.info("="*80)
                            logger.info(f"✅ [MAPVIEW-GPS-SUCCESS] GPS extracted via exifread (Band {band_num})")
                            logger.info(f"📍 Coordinates: lat={lat:.6f}, lon={lon:.6f}")
                            logger.info(f"🗺️  Map will DISPLAY this location ✓")
                            logger.info("="*80)
                            return gps_result
                        else:
                            logger.warning(f"      ⚠️ Invalid GPS from exifread: lat={lat}, lon={lon}")
                    
                    logger.info(f"      Calling _extract_gps_from_tiff_tags()...")
                    
                    # Try TIFF tag reading next
                    gps_result = MultispectralProcessor._extract_gps_from_tiff_tags(band_file)
                    logger.info(f"      Result from TIFF tags: {gps_result is not None}")
                    
                    if gps_result:
                        logger.info(f"      GPS result keys: {list(gps_result.keys())}")
                        # Convert the dict to standard format if needed
                        if 'GPSLatitude' in gps_result and 'GPSLongitude' in gps_result:
                            lat = MultispectralProcessor._convert_to_degrees(gps_result['GPSLatitude'])
                            lon = MultispectralProcessor._convert_to_degrees(gps_result['GPSLongitude'])
                            if lat and lon:
                                if gps_result.get('GPSLatitudeRef') == 'S':
                                    lat = -lat
                                if gps_result.get('GPSLongitudeRef') == 'W':
                                    lon = -lon
                                
                                alt = None
                                try:
                                    alt = float(gps_result.get('GPSAltitude', 0))
                                except:
                                    pass
                                
                                logger.info("="*80)
                                logger.info(f"✅ [MAPVIEW-GPS-SUCCESS] GPS extracted from TIFF tags (Band {band_num})")
                                logger.info(f"📍 Coordinates: lat={lat:.6f}, lon={lon:.6f}, alt={alt}")
                                logger.info(f"🗺️  Map will DISPLAY this location ✓")
                                logger.info("="*80)
                                return {
                                    'gps_latitude': lat,
                                    'gps_longitude': lon,
                                    'gps_altitude': alt
                                }
                        else:
                            logger.warning(f"      GPS result missing latitude/longitude")
                    else:
                        logger.info(f"      No GPS from TIFF tags, trying rasterio...")
                    
                    # Try rasterio as final fallback
                    logger.info(f"      Calling _extract_gps_from_rasterio() [LAST RESORT]...")
                    gps_result = MultispectralProcessor._extract_gps_from_rasterio(band_file)
                    logger.info(f"      Result from rasterio: {gps_result is not None}")
                    
                    if gps_result:
                        lat = gps_result.get('gps_latitude', 0)
                        lon = gps_result.get('gps_longitude', 0)
                        # Validate rasterio result
                        if -90 <= lat <= 90 and -180 <= lon <= 180:
                            logger.info("="*80)
                            logger.info(f"✅ [MAPVIEW-GPS-SUCCESS] GPS extracted via rasterio (Band {band_num})")
                            logger.info(f"📍 Coordinates: lat={lat:.6f}, lon={lon:.6f}")
                            logger.info(f"🗺️  Map will DISPLAY this location ✓")
                            logger.info("="*80)
                            return gps_result
                        else:
                            logger.warning(f"      ⚠️ Rasterio returned invalid coordinates: lat={lat}, lon={lon}")
            
            logger.error("\n" + "="*80)
            logger.error(f"❌ [MAPVIEW-GPS-FAILED] No GPS data found in any band (All methods exhausted)")
            logger.error(f"   🗺️  Map will show: 'No GPS Data Available'")
            logger.error(f"   💡 Next steps:")
            logger.error(f"      1. Verify GPS data exists in image properties")
            logger.error(f"      2. Check if GPS is in XMP or other custom tags")
            logger.error(f"      3. Try opening image with exifread library")
            logger.error("="*80)
            return None
            
        except Exception as e:
            logger.error(f"\n❌ [MAPVIEW-GPS-ERROR] GPS extraction failed with exception:")
            logger.error(f"   Exception: {type(e).__name__}: {e}")
            logger.error(f"   This means GPS data will NOT be stored in database")
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
