bl_info = {
    "name": "Export Unity Textures",
    "author": "khazanovanastasia",
    "version": (2, 0),
    "blender": (3, 3, 0),
    "location": "3D View > Object > Export Unity Textures",
    "description": "Exports Principled BSDF textures as Unity-ready maps",
    "category": "Import-Export",
}

import bpy
from . import exporter

def register():
    exporter.register()

def unregister():
    exporter.unregister()

if __name__ == "__main__":
    register()
