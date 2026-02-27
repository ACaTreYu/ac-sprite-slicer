# Sprite Tools

A Python toolkit for slicing sprite sheets, categorizing tiles, and generating 3D meshes for Unreal Engine 5.

## Overview

```
batch_auto_slicer.py   → ⭐ Auto-find & slice all sprites (recommended)
sprite_slicer.py       → Slice individual sprite sheets
tile_categorizer.py    → Analyze & categorize tiles by visual features
generate_ue5_meshes.py → Generate OBJ meshes for UE5 import
```

## Requirements

```bash
pip install Pillow
```

---

## 📁 Folder Setup

Place your sprite sheet folders **inside** the `sprite_tools` directory:

```
sprite_tools/                     ← You are here
│
├── batch_auto_slicer.py          ← The scripts
├── sprite_slicer.py
├── tile_categorizer.py
├── generate_ue5_meshes.py
├── README.md
│
├── input/                        ← CREATE THIS - put your sprites here
│   ├── AC Default Sheets/        ← Each patch/version gets its own folder
│   │   ├── imgTiles.png          ← Must be named exactly "imgTiles.png"
│   │   └── imgTuna.png           ← Must be named exactly "imgTuna.png"
│   │
│   ├── Upscaled 4x/              ← Another version (any folder name works)
│   │   ├── imgTiles.png
│   │   └── imgTuna.png
│   │
│   └── My Custom Patch/          ← Partial sets are fine too
│       └── imgTiles.png
│
└── output/                       ← CREATED AUTOMATICALLY by the scripts
    └── (sliced tiles appear here)
```

### Quick Start

1. Create an `input` folder inside `sprite_tools`
2. Put each sprite sheet set in its own subfolder inside `input`
3. Make sure files are named exactly `imgTiles.png` and/or `imgTuna.png`
4. Open terminal in `sprite_tools` folder and run:

```bash
python batch_auto_slicer.py ./input ./output
```

That's it! Your sliced tiles will appear in `output/`.

---

## ⭐ Batch Auto-Slicer (Recommended)

The easiest way to slice multiple sprite sheets at once. Just point it at a folder!

```bash
python batch_auto_slicer.py ./input
python batch_auto_slicer.py ./input ./output
```

**What it does:**
1. Recursively finds all `imgTiles.png` and `imgTuna.png` files
2. Auto-detects scale from image dimensions (1x, 2x, 4x, etc.)
3. Slices with correct tile sizes automatically
4. Organizes output by source folder name

**Example input structure:**
```
input/
├── AC Default Sheets/
│   ├── imgTiles.png    (640x1600 = 1x)
│   └── imgTuna.png     (640x1320 = 1x)
├── Upscaled 4x/
│   ├── imgTiles.png    (2560x6400 = 4x)
│   └── imgTuna.png     (2560x5280 = 4x)
└── Custom 2x Patch/
    └── imgTiles.png    (1280x3200 = 2x)
```

**Auto-generated output:**
```
output/
├── ac_default_sheets/
│   ├── tiles_1x/       (16x16 tiles)
│   └── ships_1x/       (32x32 ships)
├── upscaled_4x/
│   ├── tiles_4x/       (64x64 tiles)
│   └── ships_4x/       (128x128 ships)
├── custom_2x_patch/
│   └── tiles_2x/       (32x32 tiles)
└── batch_manifest.json
```

**Scale auto-detection:**
| Image Width | Detected Scale | Tile Size | Ship Size |
|-------------|----------------|-----------|-----------|
| 640px       | 1x             | 16px      | 32px      |
| 1280px      | 2x             | 32px      | 64px      |
| 2560px      | 4x             | 64px      | 128px     |
| 5120px      | 8x             | 128px     | 256px     |

**imgTuna handling:**
Unlike imgTiles (uniform 16x16 grid), imgTuna has non-uniform sprite regions:
- **Ships** start at Y=292 (5 teams × 9 directions)
- **Reticles** at Y=171 (6 weapon states)
- **Projectiles** (grenade, missile, shrapnel)
- **Effects** (smoke trails, explosions)
- **Flags** (per team)

The slicer extracts each region from its correct coordinates and names sprites descriptively:
```
ships_1x/
├── ship_green_0_right.png
├── ship_green_1_up_right.png
├── ...
├── reticle_missile_red.png
├── grenade_frame_0.png
├── explosion_frame_0.png
├── flag_green.png
└── manifest.json
```

---

## Quick Start (Manual)

### 1. Slice Your Sprite Sheets

```bash
# Single sprite sheet
python sprite_slicer.py tiles.png 16 output/tiles

# Ships (32x32 sprites)
python sprite_slicer.py ships.png 32 output/ships --type ships

# Dual-scale batch (edit AC_GAME_CONFIG in script first)
python sprite_slicer.py --batch
```

**Output:**
- Individual PNG files with RGBA transparency
- `manifest.json` with grid positions and metadata

### 2. Categorize Tiles

```bash
# Categorize and assign heights for 3D extrusion
python tile_categorizer.py output/tiles

# With preview sheets
python tile_categorizer.py output/tiles --preview

# Batch multiple directories
python tile_categorizer.py --batch output/tiles_1x output/tiles_4x --preview
```

**Output:**
- Updated `manifest.json` with `category` and `height_uu`
- Preview sheets showing tiles by category (optional)

### 3. Generate UE5 Meshes

```bash
# Generate OBJ meshes
python generate_ue5_meshes.py output/tiles

# With ships
python generate_ue5_meshes.py output/tiles --ships_dir output/ships

# Batch mode (standard directory structure)
python generate_ue5_meshes.py --batch
```

**Output:**
- OBJ + MTL files per sprite
- Textures copied to `textures/` subfolder

## Full Pipeline Example

```bash
# 1. Slice dual-scale sprite sheets
python sprite_slicer.py sprites/imgTiles.png 16 sliced/tiles_1x
python sprite_slicer.py sprites_4x/imgTiles.png 64 sliced/tiles_4x
python sprite_slicer.py sprites/imgTuna.png 32 sliced/ships_1x --type ships
python sprite_slicer.py sprites_4x/imgTuna.png 128 sliced/ships_4x --type ships

# 2. Categorize tiles (assigns heights)
python tile_categorizer.py sliced/tiles_1x --preview
python tile_categorizer.py sliced/tiles_4x --preview

# 3. Generate UE5 meshes
python generate_ue5_meshes.py --batch
```

## Directory Structure

After running the full pipeline:

```
sprite_tools/
├── input/                        ← Your source sprites
├── output/
│   ├── ac_default_sheets/
│   │   ├── tiles_1x/
│   │   │   ├── tiles_0001.png
│   │   │   ├── tiles_0002.png
│   │   │   └── manifest.json
│   │   └── ships_1x/
│   ├── upscaled_4x/
│   │   ├── tiles_4x/
│   │   └── ships_4x/
│   └── previews/
│       ├── tiles_1x_detailed_wall.png
│       └── ...
├── meshes_1x/
│   ├── tiles/
│   │   ├── tiles_0001.obj
│   │   ├── tiles_0001.mtl
│   │   └── textures/
│   └── ships/
└── meshes_4x/
```

## Tile Categories & Heights

The categorizer uses visual analysis to assign tiles to categories:

| Category        | Height (UU) | Description                    |
|-----------------|-------------|--------------------------------|
| floor           | 5           | Flat floor tiles               |
| metal_floor     | 5           | Clean metal/industrial floor   |
| dark_grate      | 5           | Vents, floor grating           |
| organic         | 5           | Grass, nature elements         |
| generic         | 5           | Misc floor tiles               |
| tech_blue       | 30          | Blue tech/emissive panels      |
| tech_red        | 30          | Red tech/emissive panels       |
| detailed_wall   | 50          | Textured walls, cover          |
| metal_textured  | 50          | Industrial walls               |
| sparse          | 0           | Near-empty tiles (skip)        |

**Customize heights** by editing `CATEGORY_HEIGHTS` in `tile_categorizer.py`.

**Per-tile overrides**: Edit `manifest.json` directly:

```json
"tiles_0123": {
  "file": "tiles_0123.png",
  "category": "detailed_wall",
  "height_uu": 100  // Override to 100 UU
}
```

## Scale Reference

| Scale | Tile Size | World Size | Use Case                    |
|-------|-----------|------------|------------------------------|
| 1x    | 16px      | 100 UU     | Tactical overview, low VRAM  |
| 4x    | 64px      | 100 UU     | Close-up, high-quality       |

Ships are 2x tile size (32px → 200 UU, 128px → 200 UU).

## UE5 Import Guide

1. **Import OBJ files** via Content Browser drag & drop
2. **Enable options:**
   - ☑ Import Textures
   - ☑ Create New Materials
3. **Texture settings** (for pixel art):
   - Filter: **Nearest**
   - Compression: **UserInterface2D (RGBA)** or **TC_EditorIcon**
4. **Transparency** (for tiles with alpha):
   - Material Blend Mode: **Masked**
   - Connect texture Alpha → Opacity Mask

## manifest.json Format

```json
{
  "source": "imgTiles.png",
  "tile_size": 16,
  "grid_cols": 40,
  "grid_rows": 100,
  "total_tiles": 2338,
  "categories": {
    "detailed_wall": 1589,
    "organic": 284
  },
  "tiles": {
    "tiles_0001": {
      "file": "tiles_0001.png",
      "row": 0,
      "col": 1,
      "index": 1,
      "category": "detailed_wall",
      "height_uu": 50
    }
  }
}
```

## Tips

- **Empty tiles** (< 5 visible pixels) are automatically skipped
- **Preview sheets** are 10×10 grids, scaled up for visibility
- **Batch mode** expects `sliced/tiles_1x`, `sliced/tiles_4x`, etc.
- **Ships** get 1 UU height (flat planes for top-down view)

## License

MIT - Do whatever you want with it.