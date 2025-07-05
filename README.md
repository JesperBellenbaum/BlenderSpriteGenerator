# Blender Sprite Generator

A complete 2D/2.5D sprite rendering and atlas packing solution for game development.

## Overview

This project consists of two main components:

1. **Blender Addon** (`__init__.py`) - Renders multi-angle sprites with normal and depth passes
2. **Atlas Packer** (`atlas_packer.py`) - Packs individual sprite frames into texture atlases

## 🎮 Blender Addon

### Features
- **Multi-angle rendering**: 8 angles (or custom) around your 3D model
- **Roll control**: Tilt perspectives for 2.5D gameplay (uphill/downhill views)
- **Multi-pass rendering**: Color, Normal, and Depth passes in one go
- **Animation support**: Render animated sprites with frame stepping
- **Camera modes**: Orthographic or Perspective rendering
- **Flexible output**: Custom resolution, transparent backgrounds

### Installation
1. Copy `__init__.py` to your Blender addons folder
2. Enable "2D/2.5D Sprite Renderer" in Blender preferences
3. Find the panel in **View3D > Sidebar > Sprite Renderer**

### Usage
1. **Select your 3D model** in Blender
2. **Configure settings** in the Sprite Renderer panel:
   - **Output Folder**: Where to save sprites
   - **Basename**: Prefix for output files (e.g., "tank")
   - **Number of Angles**: How many rotation angles (default: 8)
   - **Distance Factor**: Camera distance multiplier (1.2 = 20% margin)
   - **Roll Settings**: For 2.5D - tilt angles and steps
   - **Resolution**: 32x32 to 512x512 pixels
3. **Click "Render Sprites"**

### Output Files
The addon generates files in this format:
```
basename_C_YY_RR.png      # Color pass (YY=angle, RR=roll)
basename_N_YY_RR.png      # Normal pass  
basename_Z_YY_RR.exr      # Depth pass
```

Example with 8 angles, 5 roll steps:
```
tank_C_00_00.png, tank_C_01_00.png, ..., tank_C_07_04.png  (40 color frames)
tank_N_00_00.png, tank_N_01_00.png, ..., tank_N_07_04.png  (40 normal frames)
tank_Z_00_00.exr, tank_Z_01_00.exr, ..., tank_Z_07_04.exr  (40 depth frames)
```

## 📦 Atlas Packer

### Features
- **Single-sheet packing**: Combines all sprites into one atlas per pass
- **JSON metadata**: Clean, easy-to-parse frame coordinates
- **No rotation**: Sprites remain upright (rotated: false)
- **Multi-pass support**: Handles Color, Normal, and Depth passes
- **Configurable size**: 1024x1024 to 4096x4096 atlas size

### Requirements
```bash
pip install PyTexturePacker
```

### Usage

#### Basic Command
```bash
python atlas_packer.py <input_folder> <output_folder> <basename>
```

#### Examples
```bash
# Pack sprites with default settings (4096x4096 atlas)
python atlas_packer.py samples atlases render

# Pack with smaller atlas size
python atlas_packer.py samples atlases render --size 2048

# Keep original files after packing
python atlas_packer.py samples atlases render --keep-raw
```

#### Options
- `--size 1024|2048|4096`: Maximum atlas size (default: 4096)
- `--keep-raw`: Keep original sprite files after packing

### Output Files
The atlas packer creates:
```
basename_color.png   + basename_color.json    # Color atlas + metadata
basename_normal.png  + basename_normal.json   # Normal atlas + metadata  
basename_depth.png   + basename_depth.json    # Depth atlas + metadata
```

### JSON Format
Each JSON file contains frame coordinates:
```json
{
  "frames": {
    "frame_000.png": {
      "frame": {"x": 0, "y": 0, "w": 512, "h": 512},
      "rotated": false,
      "spriteSourceSize": {"x": 0, "y": 0, "w": 512, "h": 512},
      "sourceSize": {"w": 512, "h": 512}
    }
  },
  "meta": {
    "image": "atlases/render_color.png",
    "format": "RGBA8888",
    "size": {"w": 4096, "h": 4096}
  }
}
```

## 🚀 Complete Workflow

1. **Model in Blender**: Create your 3D model/character
2. **Render Sprites**: Use the Blender addon to generate multi-angle sprites
3. **Pack Atlases**: Use the atlas packer to combine sprites into game-ready atlases
4. **Use in Game**: Load atlases in your game engine with consistent UV coordinates

## 📁 File Structure
```
BlenderSpriteGenerator/
├── __init__.py              # Blender addon
├── atlas_packer.py          # Atlas packing script
├── samples/                 # Example sprite renders
│   ├── render_C_00_00.png   # Individual color frames
│   ├── render_N_00_00.png   # Individual normal frames
│   └── render_Z_00_00.exr   # Individual depth frames
├── atlases/                 # Packed atlases
│   ├── render_color.png     # Color atlas
│   ├── render_color.json    # Color metadata
│   ├── render_normal.png    # Normal atlas
│   ├── render_normal.json   # Normal metadata
│   ├── render_depth.png     # Depth atlas
│   └── render_depth.json    # Depth metadata
└── README.md               # This file
```

## 🎯 Game Integration

The atlases are designed for easy integration:
- **Same frame names**: `frame_000.png` exists in all three atlases
- **Identical UV coordinates**: Same pixel positions across color/normal/depth
- **No rotation**: All sprites remain upright for simpler shaders
- **JSON format**: Easy to parse in any game engine

Perfect for 2D/2.5D games requiring multi-pass rendering with color, normal mapping, and depth information!