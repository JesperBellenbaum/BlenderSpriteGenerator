#!/usr/bin/env python3
"""
Sprite Atlas Packer

A standalone script to pack sprite frames into texture atlases.
This script can be used to pack the output from the Blender Sprite Renderer addon.

Usage:
    python atlas_packer.py <input_directory> <output_directory> <basename> [options]

Requirements:
    pip install PyTexturePacker

Author: Enhanced from Blender Sprite Renderer addon
"""

import os
import sys
import glob
import shutil
import argparse
import json
from pathlib import Path

try:
    from PyTexturePacker import Packer
except ImportError:
    print("Error: PyTexturePacker is not installed.")
    print("Install it with: pip install PyTexturePacker")
    sys.exit(1)


def pack_sprites(input_dir, output_dir, basename, max_size=2048, keep_raw=False):
    """
    Pack sprite frames into atlases.
    
    Args:
        input_dir: Directory containing sprite frames
        output_dir: Directory to save atlases
        basename: Base name for output files
        max_size: Maximum atlas size (default: 2048)
        keep_raw: Keep original frames after packing (default: False)
    """
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    def _pack_pass(glob_pattern, pass_name, description):
        """Pack a specific rendering pass (color, normal, depth)."""
        files = sorted(glob.glob(os.path.join(input_dir, glob_pattern)))
        if not files:
            print(f"No files found for {description} pass (pattern: {glob_pattern})")
            return False
        
        print(f"Found {len(files)} files for {description} pass")
        
        try:
            # Create a temporary directory for this pass
            temp_dir = os.path.join(input_dir, f"temp_{pass_name}")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Copy files to temp directory with simple names for packing
            for i, file_path in enumerate(files):
                ext = os.path.splitext(file_path)[1]
                temp_file = os.path.join(temp_dir, f"frame_{i:03d}{ext}")
                import shutil
                shutil.copy2(file_path, temp_file)
            
            # Create packer and pack the images
            packer = Packer.create(
                max_width=max_size, 
                max_height=max_size, 
                bg_color=0x00000000,
                enable_rotated=False,  # stops 90° rotation
                atlas_format="json"    # JSON format instead of plist
            )
            
            # Output paths
            atlas_path = os.path.join(output_dir, f"{basename}_{pass_name}")
            
            # Pack the temporary directory
            packer.pack(temp_dir + "/", atlas_path)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir)
            
            print(f"✓ Packed {description} atlas: {output_dir}/{basename}_{pass_name}.png")
            print(f"  - {len(files)} frames packed")
            print(f"  - Metadata saved to: {output_dir}/{basename}_{pass_name}.json")
            
            return True
            
        except Exception as e:
            print(f"✗ Error packing {description} atlas: {e}")
            # Clean up temp directory if it exists
            try:
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except:
                pass
            return False
    
    # Pack different rendering passes
    results = {}
    
    # Color pass (main sprites)
    results['color'] = _pack_pass("*_C_*.png", "color", "Color")
    
    # Normal pass
    results['normal'] = _pack_pass("*_N_*.png", "normal", "Normal")
    
    # Depth pass (try both PNG and EXR formats)
    results['depth'] = _pack_pass("*_Z_*.png", "depth", "Depth")
    if not results['depth']:
        results['depth'] = _pack_pass("*_Z_*.exr", "depth", "Depth")
    
    # Summary
    successful_packs = sum(1 for success in results.values() if success)
    total_packs = len(results)
    
    print(f"\nPacking Summary:")
    print(f"✓ {successful_packs}/{total_packs} atlases packed successfully")
    
    if not keep_raw and successful_packs > 0:
        print("\nCleaning up original frames...")
        # Remove original files that were successfully packed
        for pattern, pass_name in [("*_C_*.png", "color"), ("*_N_*.png", "normal"), ("*_Z_*.png", "depth")]:
            if results.get(pass_name):
                files = glob.glob(os.path.join(input_dir, pattern))
                for file_path in files:
                    try:
                        os.remove(file_path)
                        print(f"  Removed: {os.path.basename(file_path)}")
                    except Exception as e:
                        print(f"  Warning: Could not remove {file_path}: {e}")
    
    return successful_packs > 0


def main():
    parser = argparse.ArgumentParser(
        description="Pack sprite frames into texture atlases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Pack sprites with default settings
  python atlas_packer.py ./sprites ./output character
  
  # Pack with custom atlas size and keep originals
  python atlas_packer.py ./sprites ./output character --size 4096 --keep-raw
  
  # Pack sprites from current directory
  python atlas_packer.py . ./atlases my_character --size 1024
        """
    )
    
    parser.add_argument("input_dir", help="Directory containing sprite frames")
    parser.add_argument("output_dir", help="Directory to save atlases")
    parser.add_argument("basename", help="Base name for output files")
    parser.add_argument("--size", type=int, choices=[2048, 4096, 8192], default=4096,
                        help="Maximum atlas size (default: 4096)")
    parser.add_argument("--keep-raw", action="store_true",
                        help="Keep original frames after packing")
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory does not exist: {args.input_dir}")
        sys.exit(1)
    
    # Check if input directory has sprite files
    sprite_files = glob.glob(os.path.join(args.input_dir, "*_C_*.png"))
    if not sprite_files:
        print(f"Error: No sprite files found in {args.input_dir}")
        print("Expected files with pattern: *_C_*.png")
        sys.exit(1)
    
    print(f"Atlas Packer")
    print(f"============")
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Base name: {args.basename}")
    print(f"Max atlas size: {args.size}x{args.size}")
    print(f"Keep raw frames: {args.keep_raw}")
    print()
    
    # Pack the sprites
    success = pack_sprites(
        args.input_dir, 
        args.output_dir, 
        args.basename, 
        args.size, 
        args.keep_raw
    )
    
    if success:
        print(f"\n✓ Atlas packing completed successfully!")
        print(f"Output directory: {args.output_dir}")
    else:
        print(f"\n✗ Atlas packing failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
