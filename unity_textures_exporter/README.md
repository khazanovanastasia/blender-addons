# Export Unity Textures for Blender

A Blender add-on designed to export textures from active material in Unity-compatible format.

## Features

- Export textures from the active material of the selected object
- Automatically detect and export key texture types: Albedo, Normal, Metallic, Roughness, and Specular
- Save textures in PNG format with Unity-friendly naming convention
- Simple one-click export with directory selection dialog

## Requirements

- Blender version 2.93 or higher
- Python 3.7+

## Installation

1. Download the ZIP archive with the add-on
2. In Blender, go to **Edit > Preferences > Add-ons**
3. Click **"Install"** and select the downloaded ZIP file
4. Find **"Export Unity Textures"** in the add-on list and activate it

## Usage

1. Select an object with a material that contains texture nodes
2. In the 3D Viewport, go to **Object > Export Unity Textures**
3. Choose the export directory in the file browser dialog
4. Click **"Export Unity Textures"** to save all connected textures from the Principled BSDF node
5. Textures will be saved with the naming format: `[MaterialName]_[TextureType].png`

## Supported Texture Types

| Blender Input | Unity Texture |
|---------------|---------------|
