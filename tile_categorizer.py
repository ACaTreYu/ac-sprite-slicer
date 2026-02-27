"""
Tile Categorizer & Analyzer
Analyzes sliced tiles by visual characteristics and assigns categories + heights.
Updates manifest.json with category and height_uu for 3D extrusion.

Usage:
    python tile_categorizer.py <tiles_directory> [--preview]

Example:
    python tile_categorizer.py sliced/tiles_1x --preview
    python tile_categorizer.py sliced/tiles_4x

Requirements:
    pip install Pillow
"""

import os
import sys
import json
import argparse
from pathlib import Path
from PIL import Image


# ============================================================================
# HEIGHT MAPPINGS (Unreal Units)
# ============================================================================
# Customize these for your game's scale
# Default: 1 tile (16px) = 100 UU = 1 meter

CATEGORY_HEIGHTS = {
    "floor": 5,           # Flat floor tiles
    "metal_floor": 5,     # Clean metal/industrial floor
    "dark_grate": 5,      # Vents, floor grating
    "organic": 5,         # Grass, nature elements
    "generic": 5,         # Misc floor tiles
    "tech_blue": 30,      # Blue tech/emissive panels
    "tech_red": 30,       # Red tech/emissive panels  
    "detailed_wall": 50,  # Textured walls, cover
    "metal_textured": 50, # Industrial walls
    "sparse": 0,          # Near-empty tiles (skip or minimal)
}


def analyze_tile(img):
    """
    Categorize a tile by its visual characteristics.
    
    Args:
        img: PIL Image in RGBA mode
    
    Returns:
        Tuple of (category_name, height_uu)
    """
    data = list(img.getdata())
    
    # Get visible pixels only (alpha > 128)
    visible = [(p[0], p[1], p[2]) for p in data if len(p) > 3 and p[3] > 128]
    
    if len(visible) < 10:
        return "sparse", CATEGORY_HEIGHTS["sparse"]
    
    # Calculate color statistics
    avg_r = sum(p[0] for p in visible) / len(visible)
    avg_g = sum(p[1] for p in visible) / len(visible)
    avg_b = sum(p[2] for p in visible) / len(visible)
    brightness = (avg_r + avg_g + avg_b) / 3
    
    # Color variance (texture complexity)
    variance = sum(
        abs(p[0] - avg_r) + abs(p[1] - avg_g) + abs(p[2] - avg_b) 
        for p in visible
    ) / len(visible)
    
    # Saturation (color intensity)
    saturation = sum(max(p) - min(p) for p in visible) / len(visible)
    
    # Color dominance checks
    red_dominant = avg_r > avg_g * 1.5 and avg_r > avg_b * 1.5
    blue_dominant = avg_b > avg_r * 1.3 and avg_b > avg_g * 1.2
    green_dominant = avg_g > avg_r * 1.3 and avg_g > avg_b * 1.3
    
    # Category decision tree
    if red_dominant and saturation > 30:
        return "tech_red", CATEGORY_HEIGHTS["tech_red"]
    elif blue_dominant and saturation > 25:
        return "tech_blue", CATEGORY_HEIGHTS["tech_blue"]
    elif green_dominant and saturation > 20:
        return "organic", CATEGORY_HEIGHTS["organic"]
    elif brightness < 40 and variance < 20:
        return "dark_grate", CATEGORY_HEIGHTS["dark_grate"]
    elif brightness > 80 and variance < 25:
        return "metal_floor", CATEGORY_HEIGHTS["metal_floor"]
    elif variance > 40:
        return "detailed_wall", CATEGORY_HEIGHTS["detailed_wall"]
    elif brightness < 70 and variance > 20:
        return "metal_textured", CATEGORY_HEIGHTS["metal_textured"]
    else:
        return "generic", CATEGORY_HEIGHTS["generic"]


def categorize_tiles(tiles_dir, create_preview=False):
    """
    Categorize all tiles in a directory and update the manifest.
    
    Args:
        tiles_dir: Path to sliced tiles directory (with manifest.json)
        create_preview: Whether to create preview sheets
    
    Returns:
        Dict of category counts
    """
    tiles_dir = Path(tiles_dir)
    manifest_path = tiles_dir / "manifest.json"
    
    if not manifest_path.exists():
        print(f"ERROR: No manifest.json found in {tiles_dir}")
        print("Run sprite_slicer.py first to generate tiles.")
        return {}
    
    print(f"\n{'='*50}")
    print(f"Tile Categorizer")
    print(f"{'='*50}")
    print(f"Directory: {tiles_dir}")
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    categories = {}
    tile_categories = {}
    
    tile_count = len(manifest["tiles"])
    print(f"Analyzing {tile_count} tiles...")
    
    for i, (tile_name, tile_info) in enumerate(manifest["tiles"].items()):
        img_path = tiles_dir / tile_info["file"]
        if not img_path.exists():
            continue
        
        img = Image.open(img_path)
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        category, height = analyze_tile(img)
        
        tile_categories[tile_name] = {
            **tile_info,
            "category": category,
            "height_uu": height
        }
        
        if category not in categories:
            categories[category] = []
        categories[category].append(tile_info["file"])
        
        # Progress indicator
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{tile_count}...")
    
    # Update manifest
    manifest["tiles"] = tile_categories
    manifest["categories"] = {cat: len(files) for cat, files in categories.items()}
    
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nCategories:")
    for cat, count in sorted(manifest["categories"].items(), key=lambda x: -x[1]):
        height = CATEGORY_HEIGHTS.get(cat, 5)
        print(f"  {cat}: {count} tiles (height: {height} UU)")
    
    print(f"\nManifest updated: {manifest_path}")
    
    # Create preview sheets if requested
    if create_preview:
        create_category_previews(tiles_dir, manifest, categories)
    
    return manifest["categories"]


def create_category_previews(tiles_dir, manifest, categories):
    """
    Create preview sheets for each category (10x10 grid, first 100 tiles).
    """
    tiles_dir = Path(tiles_dir)
    previews_dir = tiles_dir.parent / "previews"
    previews_dir.mkdir(exist_ok=True)
    
    tile_size = manifest["tile_size"]
    scale = max(1, 64 // tile_size)  # Scale up small tiles for visibility
    
    dir_name = tiles_dir.name
    
    print(f"\nCreating preview sheets...")
    
    for cat, files in categories.items():
        if len(files) == 0:
            continue
        
        files = sorted(files)[:100]  # Max 100 for preview
        cols = 10
        rows = (len(files) + cols - 1) // cols
        
        # Dark gray background
        sheet = Image.new('RGBA', 
            (cols * tile_size * scale, rows * tile_size * scale), 
            (40, 40, 40, 255)
        )
        
        for i, fname in enumerate(files):
            try:
                tile = Image.open(tiles_dir / fname)
                if scale > 1:
                    tile = tile.resize(
                        (tile_size * scale, tile_size * scale), 
                        Image.NEAREST
                    )
                x = (i % cols) * tile_size * scale
                y = (i // cols) * tile_size * scale
                sheet.paste(tile, (x, y), tile)
            except Exception as e:
                pass
        
        preview_path = previews_dir / f"{dir_name}_{cat}.png"
        sheet.save(preview_path)
        print(f"  Created: {preview_path.name}")
    
    print(f"Preview sheets saved to: {previews_dir}")


def batch_categorize(directories, create_previews=False):
    """
    Categorize multiple tile directories.
    """
    print("\n" + "="*60)
    print("BATCH TILE CATEGORIZER")
    print("="*60)
    
    for tiles_dir in directories:
        categorize_tiles(tiles_dir, create_preview=create_previews)


def main():
    parser = argparse.ArgumentParser(
        description="Categorize tiles by visual characteristics for 3D extrusion"
    )
    parser.add_argument("tiles_dir", nargs="?", help="Directory containing sliced tiles")
    parser.add_argument("--preview", action="store_true", 
                        help="Create preview sheets for each category")
    parser.add_argument("--batch", nargs="*",
                        help="Batch categorize multiple directories")
    
    args = parser.parse_args()
    
    if args.batch is not None:
        dirs = args.batch if args.batch else ["sliced/tiles_1x", "sliced/tiles_4x"]
        batch_categorize(dirs, create_previews=args.preview)
    elif args.tiles_dir:
        categorize_tiles(args.tiles_dir, create_preview=args.preview)
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("QUICK START EXAMPLES")
        print("="*60)
        print("  Single dir:    python tile_categorizer.py sliced/tiles_1x")
        print("  With previews: python tile_categorizer.py sliced/tiles_1x --preview")
        print("  Batch mode:    python tile_categorizer.py --batch sliced/tiles_1x sliced/tiles_4x")
        print("\nEdit CATEGORY_HEIGHTS in the script to customize extrusion heights.")


if __name__ == "__main__":
    main()
