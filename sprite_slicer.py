"""
Sprite Sheet Slicer
Slices sprite sheets into individual tiles/sprites with RGBA transparency.
Skips empty tiles and generates a manifest.json for each output.

Usage:
    python sprite_slicer.py <input_image> <tile_size> <output_dir> [--type tiles|ships]

Example:
    python sprite_slicer.py imgTiles.png 16 output/tiles_1x --type tiles
    python sprite_slicer.py imgTuna.png 32 output/ships_1x --type ships

Requirements:
    pip install Pillow
"""

import os
import sys
import json
import argparse
from pathlib import Path
from PIL import Image


def is_empty_tile(img, threshold=5):
    """
    Check if tile is fully transparent or near-empty.
    
    Args:
        img: PIL Image in RGBA mode
        threshold: Minimum visible pixels to be considered non-empty
    
    Returns:
        True if tile is empty/near-empty
    """
    data = list(img.getdata())
    # Count pixels with alpha > 10
    visible = sum(1 for p in data if len(p) > 3 and p[3] > 10)
    return visible < threshold


def slice_spritesheet(input_path, tile_size, output_dir, sprite_type="tiles"):
    """
    Slice a sprite sheet into individual tiles.
    
    Args:
        input_path: Path to the sprite sheet image
        tile_size: Size of each tile (assumes square tiles)
        output_dir: Directory to save sliced tiles
        sprite_type: Type prefix for naming ('tiles' or 'ships')
    
    Returns:
        Tuple of (saved_count, empty_count)
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    
    print(f"\n{'='*50}")
    print(f"Sprite Sheet Slicer")
    print(f"{'='*50}")
    print(f"Input: {input_path}")
    print(f"Tile Size: {tile_size}x{tile_size}")
    print(f"Output: {output_dir}")
    print(f"Type: {sprite_type}")
    print(f"{'='*50}\n")
    
    # Load and convert to RGBA
    img = Image.open(input_path)
    if img.mode != "RGBA":
        print(f"Converting from {img.mode} to RGBA...")
        img = img.convert("RGBA")
    
    width, height = img.size
    cols = width // tile_size
    rows = height // tile_size
    
    print(f"Image: {width}x{height}")
    print(f"Grid: {cols} cols × {rows} rows = {cols * rows} potential tiles")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved = 0
    empty = 0
    manifest = {}
    
    for row in range(rows):
        for col in range(cols):
            x = col * tile_size
            y = row * tile_size
            
            tile = img.crop((x, y, x + tile_size, y + tile_size))
            
            if is_empty_tile(tile):
                empty += 1
                continue
            
            tile_idx = row * cols + col
            tile_name = f"{sprite_type}_{tile_idx:04d}"
            tile_path = output_dir / f"{tile_name}.png"
            
            tile.save(tile_path, "PNG")
            
            manifest[tile_name] = {
                "file": f"{tile_name}.png",
                "row": row,
                "col": col,
                "index": tile_idx
            }
            saved += 1
    
    print(f"\nSaved: {saved} tiles")
    print(f"Empty (skipped): {empty} tiles")
    
    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump({
            "source": input_path.name,
            "tile_size": tile_size,
            "grid_cols": cols,
            "grid_rows": rows,
            "total_tiles": saved,
            "tiles": manifest
        }, f, indent=2)
    
    print(f"Manifest saved: {manifest_path}")
    
    return saved, empty


def batch_slice(config):
    """
    Batch slice multiple sprite sheets from a config dict.
    
    Args:
        config: Dict mapping output names to slice configurations
                Each config has: path, tile_size, output_dir, type
    """
    print("\n" + "="*60)
    print("BATCH SPRITE SHEET SLICER")
    print("="*60)
    
    results = {}
    for name, cfg in config.items():
        saved, empty = slice_spritesheet(
            input_path=cfg["path"],
            tile_size=cfg["tile_size"],
            output_dir=cfg["output_dir"],
            sprite_type=cfg.get("type", "tiles")
        )
        results[name] = {"saved": saved, "empty": empty}
    
    print("\n" + "="*60)
    print("BATCH SUMMARY")
    print("="*60)
    for name, r in results.items():
        print(f"  {name}: {r['saved']} saved, {r['empty']} empty")
    
    return results


# ============================================================================
# EXAMPLE: AC Game Dual-Scale Configuration
# ============================================================================
AC_GAME_CONFIG = {
    "tiles_1x": {
        "path": "sprite_sheets/imgTiles.png",  # 640x1600
        "tile_size": 16,
        "output_dir": "sliced/tiles_1x",
        "type": "tiles"
    },
    "tiles_4x": {
        "path": "sprite_sheets_4x/imgTiles.png",  # 2560x6400
        "tile_size": 64,
        "output_dir": "sliced/tiles_4x",
        "type": "tiles"
    },
    "ships_1x": {
        "path": "sprite_sheets/imgTuna.png",  # 640x1320
        "tile_size": 32,
        "output_dir": "sliced/ships_1x",
        "type": "ships"
    },
    "ships_4x": {
        "path": "sprite_sheets_4x/imgTuna.png",  # 2560x5280
        "tile_size": 128,
        "output_dir": "sliced/ships_4x",
        "type": "ships"
    }
}


def main():
    parser = argparse.ArgumentParser(
        description="Slice sprite sheets into individual tiles with transparency"
    )
    parser.add_argument("input", nargs="?", help="Input sprite sheet image")
    parser.add_argument("tile_size", nargs="?", type=int, help="Tile size (e.g., 16, 32, 64)")
    parser.add_argument("output_dir", nargs="?", help="Output directory")
    parser.add_argument("--type", default="tiles", choices=["tiles", "ships"],
                        help="Sprite type for naming (default: tiles)")
    parser.add_argument("--batch", action="store_true",
                        help="Run batch mode with AC_GAME_CONFIG")
    
    args = parser.parse_args()
    
    if args.batch:
        # Run batch mode with built-in config
        # Modify AC_GAME_CONFIG paths as needed
        batch_slice(AC_GAME_CONFIG)
    elif args.input and args.tile_size and args.output_dir:
        slice_spritesheet(args.input, args.tile_size, args.output_dir, args.type)
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("QUICK START EXAMPLES")
        print("="*60)
        print("  Single sheet:  python sprite_slicer.py tiles.png 16 output/")
        print("  Ships:         python sprite_slicer.py ships.png 32 output/ --type ships")
        print("  Batch mode:    python sprite_slicer.py --batch")
        print("\nEdit AC_GAME_CONFIG in the script for custom batch processing.")


if __name__ == "__main__":
    main()
