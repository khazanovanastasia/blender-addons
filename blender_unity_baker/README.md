# Unity Texture Baker

Blender addon for automated baking of procedural materials into Unity-ready textures with MRAO channel packing.

## Features

- **One-click baking** of Albedo, Normal Map, and MRAO textures
- **MRAO packing** (Metallic/Roughness/AO into RGB channels)
- **Individual resolution** settings per texture type
- **Quick presets** for fast workflow
- **Blender 3.0-5.0** compatible

## Installation

1. Install Pillow in Blender's Python:
   ```python
   # Run in Blender Scripting
   import subprocess, sys
   subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "--break-system-packages"])
   ```

2. Install addon:
   - Edit → Preferences → Add-ons → Install
   - Select `blender_unity_baker.py`
   - Enable the checkbox

3. Restart Blender

## Usage

1. Select mesh object with UV unwrap and material
2. Press `N` → **Unity Baker** tab
3. Set export path and resolution
4. Click **Bake for Unity**

## Output

- `ObjectName_Albedo.png` - Base color (sRGB)
- `ObjectName_Normal.png` - Tangent space normal map (Linear)
- `ObjectName_MRAO.png` - Packed channels (Linear):
  - **R** = Metallic
  - **G** = Roughness
  - **B** = Ambient Occlusion

## Unity Setup

1. Import textures
2. Set Normal Map type
3. **Disable sRGB** for MRAO texture (critical!)
4. Assign to material

## Requirements

- Blender 3.0+
- Python 3.10+
- Pillow library

## License

MIT
