"""
UE5 Mesh Generator
Generates OBJ mesh files from sliced sprite tiles for import into Unreal Engine.
Uses height_uu from manifest.json to create extruded 3D tiles.

Usage:
    python generate_ue5_meshes.py [tiles_dir] [--scale SCALE] [--ships_dir SHIPS_DIR]

Example:
    python generate_ue5_meshes.py sliced/tiles_1x
    python generate_ue5_meshes.py sliced/tiles_1x --ships_dir sliced/ships_1x
    python generate_ue5_meshes.py --batch  # Process both 1x and 4x

Requirements:
    - manifest.json with height_uu (run tile_categorizer.py first)
    - No external dependencies (pure Python)

UE5 Import Notes:
    1. Import OBJ files via Content Browser
    2. Enable "Import Textures" and "Create New Materials"
    3. Set texture filtering to "Nearest" for pixel art look
    4. For transparent tiles: Set material blend mode to Masked,
       connect texture alpha to Opacity Mask
"""

import os
import sys
import json
import shutil
import argparse
from pathlib import Path


# ============================================================================
# SCALE CONFIGURATIONS
# ============================================================================
# 1 tile = 100 Unreal Units = 1 meter
# Ships are 2x tile size

SCALE_CONFIGS = {
    "1x": {
        "tile_size_uu": 100,   # 16px tile = 100 UU
        "ship_size_uu": 200,   # 32px ship = 200 UU
    },
    "4x": {
        "tile_size_uu": 100,   # Same world scale, higher res texture
        "ship_size_uu": 200,
    }
}


def generate_box_obj(width, height, depth, name, texture_file):
    """
    Generate OBJ content for an extruded box with proper UV mapping.
    
    Args:
        width: Box width in Unreal Units
        height: Box height (Y dimension) in Unreal Units  
        depth: Box extrusion depth (Z dimension) in Unreal Units
        name: Mesh name
        texture_file: Relative path to texture
    
    Returns:
        Tuple of (obj_content, mtl_content)
    """
    w, h, d = width / 2, height / 2, depth
    
    # Vertices: bottom face (z=0), top face (z=depth)
    vertices = [
        f"v {-w} {-h} 0",   # 1: bottom-left-front
        f"v {w} {-h} 0",    # 2: bottom-right-front
        f"v {w} {h} 0",     # 3: bottom-right-back
        f"v {-w} {h} 0",    # 4: bottom-left-back
        f"v {-w} {-h} {d}", # 5: top-left-front
        f"v {w} {-h} {d}",  # 6: top-right-front
        f"v {w} {h} {d}",   # 7: top-right-back
        f"v {-w} {h} {d}",  # 8: top-left-back
    ]
    
    # UVs: Full texture for top/bottom, tiled for sides based on height ratio
    side_v = depth / width if width > 0 else 1
    uvs = [
        "vt 0 0", "vt 1 0", "vt 1 1", "vt 0 1",  # Top face (full texture)
        f"vt 0 0", f"vt 1 0", f"vt 1 {side_v}", f"vt 0 {side_v}",  # Sides (tiled)
    ]
    
    # Normals
    normals = [
        "vn 0 0 -1",  # 1: down
        "vn 0 0 1",   # 2: up
        "vn 0 -1 0",  # 3: front
        "vn 0 1 0",   # 4: back
        "vn -1 0 0",  # 5: left
        "vn 1 0 0",   # 6: right
    ]
    
    # Faces: v/vt/vn
    faces = [
        "f 8/4/2 7/3/2 6/2/2 5/1/2",  # Top (looking down at it)
        "f 1/1/1 2/2/1 3/3/1 4/4/1",  # Bottom
        "f 1/5/3 5/8/3 6/7/3 2/6/3",  # Front
        "f 3/5/4 7/8/4 8/7/4 4/6/4",  # Back
        "f 4/5/5 8/8/5 5/7/5 1/6/5",  # Left
        "f 2/5/6 6/8/6 7/7/6 3/6/6",  # Right
    ]
    
    obj = f"# {name}\n"
    obj += f"mtllib {name}.mtl\n"
    obj += f"o {name}\n\n"
    obj += "\n".join(vertices) + "\n\n"
    obj += "\n".join(uvs) + "\n\n"
    obj += "\n".join(normals) + "\n\n"
    obj += f"usemtl {name}_mat\n"
    obj += "\n".join(faces) + "\n"
    
    mtl = f"# Material for {name}\n"
    mtl += f"newmtl {name}_mat\n"
    mtl += "Ka 1.0 1.0 1.0\n"    # Ambient
    mtl += "Kd 1.0 1.0 1.0\n"    # Diffuse
    mtl += "Ks 0.0 0.0 0.0\n"    # Specular (none for pixel art)
    mtl += "d 1.0\n"              # Opacity
    mtl += "illum 2\n"            # Illumination model
    mtl += f"map_Kd {texture_file}\n"
    
    return obj, mtl


def process_tiles(tiles_dir, output_dir, tile_size_uu=100):
    """
    Generate meshes for all tiles using heights from manifest.
    
    Args:
        tiles_dir: Directory with sliced tiles and manifest.json
        output_dir: Output directory for OBJ files
        tile_size_uu: Tile size in Unreal Units
    
    Returns:
        Number of meshes generated
    """
    tiles_dir = Path(tiles_dir)
    output_dir = Path(output_dir)
    
    manifest_path = tiles_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"  ERROR: No manifest.json in {tiles_dir}")
        return 0
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    textures_dir = output_dir / "textures"
    textures_dir.mkdir(exist_ok=True)
    
    count = 0
    for tile_name, tile_info in manifest["tiles"].items():
        texture_file = tile_info["file"]
        height = tile_info.get("height_uu", 5)  # Default 5 UU if not categorized
        
        src = tiles_dir / texture_file
        if not src.exists():
            continue
        
        # Copy texture
        shutil.copy(src, textures_dir / texture_file)
        
        # Generate mesh
        obj, mtl = generate_box_obj(
            tile_size_uu, tile_size_uu, height,
            tile_name, f"textures/{texture_file}"
        )
        
        with open(output_dir / f"{tile_name}.obj", 'w') as f:
            f.write(obj)
        with open(output_dir / f"{tile_name}.mtl", 'w') as f:
            f.write(mtl)
        
        count += 1
    
    return count


def process_ships(ships_dir, output_dir, ship_size_uu=200):
    """
    Generate flat plane meshes for ships (minimal height for top-down view).
    
    Args:
        ships_dir: Directory with sliced ships and manifest.json
        output_dir: Output directory for OBJ files
        ship_size_uu: Ship size in Unreal Units
    
    Returns:
        Number of meshes generated
    """
    ships_dir = Path(ships_dir)
    output_dir = Path(output_dir)
    
    manifest_path = ships_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"  ERROR: No manifest.json in {ships_dir}")
        return 0
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    textures_dir = output_dir / "textures"
    textures_dir.mkdir(exist_ok=True)
    
    count = 0
    for ship_name, ship_info in manifest["tiles"].items():
        texture_file = ship_info["file"]
        
        src = ships_dir / texture_file
        if not src.exists():
            continue
        
        # Copy texture
        shutil.copy(src, textures_dir / texture_file)
        
        # Ships are flat planes (1 UU height)
        obj, mtl = generate_box_obj(
            ship_size_uu, ship_size_uu, 1,
            ship_name, f"textures/{texture_file}"
        )
        
        with open(output_dir / f"{ship_name}.obj", 'w') as f:
            f.write(obj)
        with open(output_dir / f"{ship_name}.mtl", 'w') as f:
            f.write(mtl)
        
        count += 1
    
    return count


def batch_generate(base_dir="."):
    """
    Generate meshes for standard 1x and 4x directory structure.
    
    Expected structure:
        base_dir/
            sliced/
                tiles_1x/
                tiles_4x/
                ships_1x/ (or tuna_1x)
                ships_4x/ (or tuna_4x)
    """
    base = Path(base_dir)
    
    print("\n" + "="*60)
    print("BATCH UE5 MESH GENERATOR")
    print("="*60)
    
    # Try common directory patterns
    tile_patterns = [
        ("sliced/tiles_1x", "meshes_1x/tiles", "1x"),
        ("sliced/tiles_4x", "meshes_4x/tiles", "4x"),
    ]
    ship_patterns = [
        ("sliced/ships_1x", "meshes_1x/ships", "1x"),
        ("sliced/tuna_1x", "meshes_1x/ships", "1x"),
        ("sliced/ships_4x", "meshes_4x/ships", "4x"),
        ("sliced/tuna_4x", "meshes_4x/ships", "4x"),
    ]
    
    for tiles_rel, output_rel, scale in tile_patterns:
        tiles_dir = base / tiles_rel
        if tiles_dir.exists():
            print(f"\nProcessing {scale} tiles...")
            cfg = SCALE_CONFIGS[scale]
            count = process_tiles(tiles_dir, base / output_rel, cfg["tile_size_uu"])
            print(f"  Generated {count} tile meshes → {output_rel}")
    
    for ships_rel, output_rel, scale in ship_patterns:
        ships_dir = base / ships_rel
        if ships_dir.exists():
            print(f"\nProcessing {scale} ships...")
            cfg = SCALE_CONFIGS[scale]
            count = process_ships(ships_dir, base / output_rel, cfg["ship_size_uu"])
            print(f"  Generated {count} ship meshes → {output_rel}")
            break  # Only process first matching pattern per scale
    
    print("\n" + "="*60)
    print("Done! Import OBJ files into UE5 Content Browser.")
    print("Remember: Set texture filtering to 'Nearest' for pixel art.")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate UE5-ready OBJ meshes from sliced sprite tiles"
    )
    parser.add_argument("tiles_dir", nargs="?", 
                        help="Directory with sliced tiles")
    parser.add_argument("--ships_dir", 
                        help="Optional: Directory with sliced ships")
    parser.add_argument("--output", default="meshes",
                        help="Output directory (default: meshes)")
    parser.add_argument("--scale", default="1x", choices=["1x", "4x"],
                        help="Scale configuration (default: 1x)")
    parser.add_argument("--batch", action="store_true",
                        help="Batch mode: process standard directory structure")
    
    args = parser.parse_args()
    
    if args.batch:
        batch_generate()
    elif args.tiles_dir:
        cfg = SCALE_CONFIGS[args.scale]
        output_dir = Path(args.output)
        
        print(f"\n{'='*50}")
        print(f"UE5 Mesh Generator")
        print(f"{'='*50}")
        
        print(f"\nProcessing tiles: {args.tiles_dir}")
        tile_count = process_tiles(args.tiles_dir, output_dir / "tiles", cfg["tile_size_uu"])
        print(f"  Generated {tile_count} tile meshes")
        
        if args.ships_dir:
            print(f"\nProcessing ships: {args.ships_dir}")
            ship_count = process_ships(args.ships_dir, output_dir / "ships", cfg["ship_size_uu"])
            print(f"  Generated {ship_count} ship meshes")
        
        print(f"\nOutput: {output_dir}")
        print("Import OBJ files into UE5 Content Browser.")
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("QUICK START EXAMPLES")
        print("="*60)
        print("  Single:  python generate_ue5_meshes.py sliced/tiles_1x")
        print("  W/ships: python generate_ue5_meshes.py sliced/tiles_1x --ships_dir sliced/ships_1x")
        print("  Batch:   python generate_ue5_meshes.py --batch")
        print("\nRun tile_categorizer.py first to set height_uu values!")


if __name__ == "__main__":
    main()
