"""
Batch Auto-Slicer
Automatically finds and slices all imgTiles.png and imgTuna.png files in a directory tree.
Auto-detects scaling factor from image dimensions and organizes output by source folder.

Usage:
    python batch_auto_slicer.py <input_folder> [output_folder]

Example:
    python batch_auto_slicer.py ./patches ./sliced_output
    python batch_auto_slicer.py ./AC_Sprites

The slicer will:
1. Recursively scan for imgTiles.png and imgTuna.png files
2. Auto-detect scale (1x, 2x, 4x, etc.) from image dimensions
3. Slice tiles and ships with correct tile sizes
4. Output to organized folders: output/<patch_name>/<tiles|ships>_<scale>/

Requirements:
    pip install Pillow
"""

import os
import sys
import json
import argparse
from pathlib import Path
from PIL import Image
from collections import defaultdict


# ============================================================================
# BASE DIMENSIONS (1x scale reference)
# ============================================================================
# These are the known 1x dimensions for auto-scale detection

BASE_TILES = {
    "width": 640,
    "grid_cols": 40,    # 640 / 40 = 16px tiles at 1x
}

BASE_TUNA = {
    "width": 640,
    "grid_cols": 20,    # 640 / 20 = 32px ships at 1x
}

# ============================================================================
# imgTuna.png SPRITE REGIONS (1x coordinates)
# ============================================================================
# EXACT coordinates from manual analysis - Primary_imgTuna_Sprites_Coords_Size.txt
# All coordinates are top-left corner pixel, all sizes in pixels at 1x scale

TUNA_SPRITES = {
    # Team Switching Buttons [F4] - all 60x45
    "team_buttons": {
        "width": 60,
        "height": 45,
        "teams": {
            "green":  {"x": 64,  "y": 89},
            "red":    {"x": 124, "y": 89},
            "blue":   {"x": 184, "y": 89},
            "yellow": {"x": 244, "y": 89},
        }
    },
    
    # Full Reticles area - extract as one image
    "reticles": {
        "x": 6,
        "y": 165,
        "width": 248,
        "height": 122
    },
    
    # Ships: 288x32 rows (9 frames of 32x32 each)
    "ships": {
        "row_width": 288,   # Full row width
        "height": 32,
        "frame_width": 32,  # Individual ship frame
        "frame_count": 9,
        "teams": {
            "green":  {"x": 0, "y": 292},
            "red":    {"x": 0, "y": 324},
            "blue":   {"x": 0, "y": 356},
            "yellow": {"x": 0, "y": 388},
        },
        "dir_names": ["right", "up_right", "up", "up_left", "left", "down_left", "down", "down_right", "idle"]
    },
    
    # Flags - all 13x13
    "flags": {
        "width": 13,
        "height": 13,
        "teams": {
            "green":  {"x": 288, "y": 311},
            "red":    {"x": 288, "y": 343},
            "blue":   {"x": 288, "y": 375},
            "yellow": {"x": 288, "y": 407},
            "white":  {"x": 288, "y": 439},
        }
    },
    
    # Grenade Sprite (full strip)
    "grenade": {
        "x": 6,
        "y": 582,
        "width": 76,
        "height": 13
    },
    
    # Radar Guide Box
    "radar_box": {
        "x": 609,
        "y": 967,
        "width": 25,
        "height": 22
    },
    
    # Grenade Trails - all 172x19
    "trails_grenade": {
        "width": 172,
        "height": 19,
        "teams": {
            "white":  {"x": 10, "y": 603},
            "green":  {"x": 10, "y": 620},
            "red":    {"x": 10, "y": 637},
            "blue":   {"x": 10, "y": 654},
            "yellow": {"x": 10, "y": 671},
        }
    },
    
    # Missile Trails - all 87x10
    "trails_missile": {
        "width": 87,
        "height": 10,
        "teams": {
            "green":  {"x": 11,  "y": 692},
            "red":    {"x": 101, "y": 692},
            "blue":   {"x": 11,  "y": 703},
            "yellow": {"x": 101, "y": 702},
            "white":  {"x": 210, "y": 670},
        }
    },
    
    # Critical Smoke / Explosion (grenade explosion, missile wall hit, etc)
    "explosion_smoke": {
        "x": 10,
        "y": 720,
        "width": 172,
        "height": 19
    },
    
    # Missile Tip - 5x5
    "missile_tip": {
        "x": 8,
        "y": 756,
        "width": 5,
        "height": 5
    },
    
    # Shrapnel (grenade/missile after hit) - 5x5
    "shrapnel": {
        "x": 3,
        "y": 756,
        "width": 5,
        "height": 5
    },
    
    # Grenade After Explosion Smoke (full area)
    "grenade_explosion_smoke": {
        "x": 0,
        "y": 780,
        "width": 395,
        "height": 106
    },
    
    # Ship Death Explosion (full area)
    "ship_death_explosion": {
        "x": 0,
        "y": 885,
        "width": 403,
        "height": 274
    },
}


def detect_scale(img_width, base_width):
    """
    Detect scaling factor from image width.
    
    Returns scale as string (e.g., "1x", "2x", "4x") and multiplier.
    """
    if img_width <= 0 or base_width <= 0:
        return "1x", 1
    
    scale = img_width / base_width
    
    # Round to nearest common scale
    if scale <= 1.25:
        return "1x", 1
    elif scale <= 2.5:
        return "2x", 2
    elif scale <= 3.5:
        return "3x", 3
    elif scale <= 5:
        return "4x", 4
    elif scale <= 7:
        return "6x", 6
    elif scale <= 10:
        return "8x", 8
    else:
        return f"{int(scale)}x", int(scale)


def is_empty_tile(img, threshold=5):
    """Check if tile is fully transparent or near-empty."""
    data = list(img.getdata())
    visible = sum(1 for p in data if len(p) > 3 and p[3] > 10)
    return visible < threshold


def slice_tuna_image(img_path, scale, output_dir):
    """
    Slice imgTuna.png using exact sprite coordinates from manual analysis.
    Extracts full strips for animated sprites (can be split in-engine).
    
    Args:
        img_path: Path to imgTuna.png
        scale: Scale multiplier (1, 2, 4, etc.)
        output_dir: Output directory for sliced sprites
    
    Returns:
        Tuple of (saved_count, empty_count)
    """
    img = Image.open(img_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    saved = 0
    empty = 0
    manifest = {}
    
    def s(val):
        """Scale a coordinate/size by the scale factor."""
        return int(val * scale)
    
    def save_sprite(sprite, name, category, metadata=None):
        """Save a sprite and add to manifest."""
        nonlocal saved, empty
        
        if is_empty_tile(sprite):
            empty += 1
            return False
        
        sprite_path = output_dir / f"{name}.png"
        sprite.save(sprite_path, "PNG")
        
        entry = {
            "file": f"{name}.png",
            "category": category
        }
        if metadata:
            entry.update(metadata)
        
        manifest[name] = entry
        saved += 1
        return True
    
    # --- TEAM SWITCHING BUTTONS (60x45 each) ---
    btns = TUNA_SPRITES["team_buttons"]
    for team_name, coords in btns["teams"].items():
        x, y = s(coords["x"]), s(coords["y"])
        w, h = s(btns["width"]), s(btns["height"])
        sprite = img.crop((x, y, x + w, y + h))
        save_sprite(sprite, f"button_team_{team_name}", "ui", {"team": team_name})
    
    # --- RETICLES (full 248x122 area) ---
    ret = TUNA_SPRITES["reticles"]
    x, y = s(ret["x"]), s(ret["y"])
    w, h = s(ret["width"]), s(ret["height"])
    sprite = img.crop((x, y, x + w, y + h))
    save_sprite(sprite, "reticles_full", "ui", {"width": ret["width"], "height": ret["height"]})
    
    # --- SHIPS (9 frames of 32x32 per team) ---
    ships = TUNA_SPRITES["ships"]
    dir_names = ships["dir_names"]
    for team_name, coords in ships["teams"].items():
        for dir_idx, dir_name in enumerate(dir_names):
            x = s(coords["x"] + dir_idx * ships["frame_width"])
            y = s(coords["y"])
            w = s(ships["frame_width"])
            h = s(ships["height"])
            sprite = img.crop((x, y, x + w, y + h))
            save_sprite(sprite, f"ship_{team_name}_{dir_idx}_{dir_name}", "ships", {
                "team": team_name,
                "direction": dir_name,
                "direction_index": dir_idx
            })
    
    # --- FLAGS (13x13 each) ---
    flags = TUNA_SPRITES["flags"]
    for team_name, coords in flags["teams"].items():
        x, y = s(coords["x"]), s(coords["y"])
        w, h = s(flags["width"]), s(flags["height"])
        sprite = img.crop((x, y, x + w, y + h))
        save_sprite(sprite, f"flag_{team_name}", "flags", {"team": team_name})
    
    # --- GRENADE (76x13, 5 frames → 15x13 per frame) ---
    gren = TUNA_SPRITES["grenade"]
    grenade_frames = 5
    frame_w = gren["width"] // grenade_frames  # 15px
    for i in range(grenade_frames):
        x = s(gren["x"] + i * frame_w)
        y = s(gren["y"])
        w = s(frame_w)
        h = s(gren["height"])
        sprite = img.crop((x, y, x + w, y + h))
        save_sprite(sprite, f"grenade_frame_{i}", "projectiles", {"frame": i})
    
    # --- RADAR BOX (25x22) ---
    radar = TUNA_SPRITES["radar_box"]
    x, y = s(radar["x"]), s(radar["y"])
    w, h = s(radar["width"]), s(radar["height"])
    sprite = img.crop((x, y, x + w, y + h))
    save_sprite(sprite, "radar_box", "ui")
    
    # --- GRENADE TRAILS (172x19 each - FULL STRIPS) ---
    gtrails = TUNA_SPRITES["trails_grenade"]
    for team_name, coords in gtrails["teams"].items():
        x, y = s(coords["x"]), s(coords["y"])
        w, h = s(gtrails["width"]), s(gtrails["height"])
        sprite = img.crop((x, y, x + w, y + h))
        save_sprite(sprite, f"trail_grenade_{team_name}", "effects", {
            "team": team_name,
            "width": gtrails["width"],
            "height": gtrails["height"]
        })
    
    # --- MISSILE TRAILS (87x10 each - FULL STRIPS) ---
    mtrails = TUNA_SPRITES["trails_missile"]
    for team_name, coords in mtrails["teams"].items():
        x, y = s(coords["x"]), s(coords["y"])
        w, h = s(mtrails["width"]), s(mtrails["height"])
        sprite = img.crop((x, y, x + w, y + h))
        save_sprite(sprite, f"trail_missile_{team_name}", "effects", {
            "team": team_name,
            "width": mtrails["width"],
            "height": mtrails["height"]
        })
    
    # --- EXPLOSION SMOKE (172x19 - FULL STRIP) ---
    exp_smoke = TUNA_SPRITES["explosion_smoke"]
    x, y = s(exp_smoke["x"]), s(exp_smoke["y"])
    w, h = s(exp_smoke["width"]), s(exp_smoke["height"])
    sprite = img.crop((x, y, x + w, y + h))
    save_sprite(sprite, "explosion_smoke", "effects", {
        "width": exp_smoke["width"],
        "height": exp_smoke["height"]
    })
    
    # --- MISSILE TIP (5x5) ---
    tip = TUNA_SPRITES["missile_tip"]
    x, y = s(tip["x"]), s(tip["y"])
    w, h = s(tip["width"]), s(tip["height"])
    sprite = img.crop((x, y, x + w, y + h))
    save_sprite(sprite, "missile_tip", "projectiles")
    
    # --- SHRAPNEL (5x5) ---
    shrap = TUNA_SPRITES["shrapnel"]
    x, y = s(shrap["x"]), s(shrap["y"])
    w, h = s(shrap["width"]), s(shrap["height"])
    sprite = img.crop((x, y, x + w, y + h))
    save_sprite(sprite, "shrapnel", "projectiles")
    
    # --- GRENADE EXPLOSION SMOKE (395x106 - FULL AREA) ---
    gexp = TUNA_SPRITES["grenade_explosion_smoke"]
    x, y = s(gexp["x"]), s(gexp["y"])
    w, h = s(gexp["width"]), s(gexp["height"])
    sprite = img.crop((x, y, x + w, y + h))
    save_sprite(sprite, "grenade_explosion_smoke", "effects", {
        "width": gexp["width"],
        "height": gexp["height"]
    })
    
    # --- SHIP DEATH EXPLOSION (403x274 - FULL AREA) ---
    ship_exp = TUNA_SPRITES["ship_death_explosion"]
    x, y = s(ship_exp["x"]), s(ship_exp["y"])
    w, h = s(ship_exp["width"]), s(ship_exp["height"])
    sprite = img.crop((x, y, x + w, y + h))
    save_sprite(sprite, "ship_death_explosion", "effects", {
        "width": ship_exp["width"],
        "height": ship_exp["height"]
    })
    
    # --- Save manifest ---
    categories = {}
    for entry in manifest.values():
        cat = entry.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    
    manifest_data = {
        "source": Path(img_path).name,
        "scale": scale,
        "sprite_type": "tuna",
        "total_sprites": saved,
        "categories": categories,
        "sprites": manifest
    }
    
    with open(output_dir / "manifest.json", 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    return saved, empty


def slice_image(img_path, tile_size, output_dir, sprite_type="tiles"):
    """
    Slice a single image into tiles.
    
    Returns:
        Tuple of (saved_count, empty_count)
    """
    img = Image.open(img_path)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    
    width, height = img.size
    cols = width // tile_size
    rows = height // tile_size
    
    output_dir = Path(output_dir)
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
    
    # Save manifest
    manifest_data = {
        "source": Path(img_path).name,
        "tile_size": tile_size,
        "grid_cols": cols,
        "grid_rows": rows,
        "total_tiles": saved,
        "tiles": manifest
    }
    
    with open(output_dir / "manifest.json", 'w') as f:
        json.dump(manifest_data, f, indent=2)
    
    return saved, empty


def find_sprite_sheets(input_folder):
    """
    Recursively find all imgTiles.png and imgTuna.png files.
    
    Returns:
        List of dicts with path, type, and parent folder info
    """
    input_folder = Path(input_folder)
    found = []
    
    for root, dirs, files in os.walk(input_folder):
        root_path = Path(root)
        
        for fname in files:
            fname_lower = fname.lower()
            
            if fname_lower == "imgtiles.png":
                found.append({
                    "path": root_path / fname,
                    "type": "tiles",
                    "folder": root_path.name,
                    "parent": root_path.parent.name if root_path.parent != input_folder else ""
                })
            elif fname_lower == "imgtuna.png":
                found.append({
                    "path": root_path / fname,
                    "type": "ships",
                    "folder": root_path.name,
                    "parent": root_path.parent.name if root_path.parent != input_folder else ""
                })
    
    return found


def get_output_folder_name(sheet_info):
    """
    Generate a clean output folder name from the source path.
    
    Examples:
        "AC Default Sheets" -> "ac_default_sheets"
        "Upscaled AC Sheets" -> "upscaled_ac_sheets"
    """
    # Combine parent and folder if parent exists
    if sheet_info["parent"]:
        name = f"{sheet_info['parent']}_{sheet_info['folder']}"
    else:
        name = sheet_info["folder"]
    
    # Clean up the name
    name = name.lower()
    name = name.replace(" ", "_")
    name = name.replace("-", "_")
    name = "".join(c for c in name if c.isalnum() or c == "_")
    
    # Remove redundant underscores
    while "__" in name:
        name = name.replace("__", "_")
    
    return name.strip("_")


def batch_auto_slice(input_folder, output_folder=None):
    """
    Main batch processing function.
    
    Args:
        input_folder: Root folder to scan for sprite sheets
        output_folder: Output folder (default: input_folder/sliced_output)
    """
    input_folder = Path(input_folder)
    
    if output_folder is None:
        output_folder = input_folder / "sliced_output"
    else:
        output_folder = Path(output_folder)
    
    print("\n" + "=" * 70)
    print("BATCH AUTO-SLICER")
    print("=" * 70)
    print(f"Input:  {input_folder}")
    print(f"Output: {output_folder}")
    print("=" * 70)
    
    # Find all sprite sheets
    sheets = find_sprite_sheets(input_folder)
    
    if not sheets:
        print("\nNo imgTiles.png or imgTuna.png files found!")
        print("Make sure your sprite sheets are named exactly 'imgTiles.png' or 'imgTuna.png'")
        return
    
    print(f"\nFound {len(sheets)} sprite sheet(s):")
    for s in sheets:
        print(f"  - {s['path'].relative_to(input_folder)} ({s['type']})")
    
    # Group by source folder for organized output
    results = []
    
    for sheet in sheets:
        img = Image.open(sheet["path"])
        width, height = img.size
        
        # Detect scale and calculate tile size
        if sheet["type"] == "tiles":
            scale_name, scale_mult = detect_scale(width, BASE_TILES["width"])
            tile_size = (BASE_TILES["width"] // BASE_TILES["grid_cols"]) * scale_mult
            base_ref = f"{BASE_TILES['grid_cols']} cols"
        else:  # ships/tuna
            scale_name, scale_mult = detect_scale(width, BASE_TUNA["width"])
            tile_size = (BASE_TUNA["width"] // BASE_TUNA["grid_cols"]) * scale_mult
            base_ref = f"{BASE_TUNA['grid_cols']} cols"
        
        # Generate output folder name
        folder_name = get_output_folder_name(sheet)
        out_subdir = f"{sheet['type']}_{scale_name}"
        out_path = output_folder / folder_name / out_subdir
        
        print(f"\n{'─' * 70}")
        print(f"Processing: {sheet['path'].name}")
        print(f"  Source:     {sheet['path'].relative_to(input_folder)}")
        print(f"  Dimensions: {width}x{height}")
        print(f"  Detected:   {scale_name} scale ({base_ref} → {tile_size}x{tile_size}px)")
        print(f"  Output:     {out_path.relative_to(output_folder)}")
        
        # Use different slicing method for imgTuna vs imgTiles
        if sheet["type"] == "ships":
            # imgTuna has non-uniform sprite regions - use special slicer
            saved, empty = slice_tuna_image(
                sheet["path"],
                scale_mult,
                out_path
            )
        else:
            # imgTiles is a uniform grid
            saved, empty = slice_image(
                sheet["path"],
                tile_size,
                out_path,
                sheet["type"]
            )
        
        print(f"  Result:     {saved} saved, {empty} empty")
        
        results.append({
            "source": str(sheet["path"].relative_to(input_folder)),
            "output": str(out_path.relative_to(output_folder)),
            "scale": scale_name,
            "tile_size": tile_size,
            "saved": saved,
            "empty": empty
        })
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total_saved = sum(r["saved"] for r in results)
    total_empty = sum(r["empty"] for r in results)
    
    # Group by output folder
    by_folder = defaultdict(list)
    for r in results:
        folder = r["output"].split("/")[0] if "/" in r["output"] else r["output"]
        by_folder[folder].append(r)
    
    for folder, items in sorted(by_folder.items()):
        print(f"\n{folder}/")
        for r in items:
            subdir = r["output"].split("/")[-1] if "/" in r["output"] else r["output"]
            print(f"  └─ {subdir}: {r['saved']} sprites ({r['scale']}, {r['tile_size']}px)")
    
    print(f"\n{'─' * 70}")
    print(f"Total: {total_saved} sprites saved, {total_empty} empty tiles skipped")
    print(f"Output directory: {output_folder}")
    print("=" * 70)
    
    # Save batch manifest
    batch_manifest = {
        "input_folder": str(input_folder),
        "output_folder": str(output_folder),
        "total_sprites": total_saved,
        "sheets_processed": len(results),
        "results": results
    }
    
    with open(output_folder / "batch_manifest.json", 'w') as f:
        json.dump(batch_manifest, f, indent=2)
    
    print(f"\nBatch manifest saved to: {output_folder}/batch_manifest.json")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-detect and slice all sprite sheets in a folder tree",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python batch_auto_slicer.py ./patches
  python batch_auto_slicer.py ./AC_Sprites ./output
  python batch_auto_slicer.py "C:/Games/AC/Sprites" "C:/Projects/sliced"

The slicer auto-detects:
  - imgTiles.png at any scale (1x=16px, 2x=32px, 4x=64px tiles)
  - imgTuna.png at any scale (1x=32px, 2x=64px, 4x=128px ships)

Output structure:
  output/
    <source_folder_name>/
      tiles_1x/
      tiles_4x/
      ships_1x/
      ships_4x/
        """
    )
    parser.add_argument("input_folder", help="Root folder containing sprite sheets")
    parser.add_argument("output_folder", nargs="?", default=None,
                        help="Output folder (default: input_folder/sliced_output)")
    
    args = parser.parse_args()
    
    if not Path(args.input_folder).exists():
        print(f"ERROR: Input folder not found: {args.input_folder}")
        sys.exit(1)
    
    batch_auto_slice(args.input_folder, args.output_folder)


if __name__ == "__main__":
    main()
