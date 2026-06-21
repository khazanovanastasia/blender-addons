bl_info = {
    "name": "Unity Texture Baker",
    "author": "khazanovanastasia",
    "version": (1, 3, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Unity Baker",
    "description": "Bake procedural materials and export textures for Unity (Blender 3.x - 5.x)",
    "category": "Material",
}

import bpy
from .blender_unity_baker import classes, UnityBakerProperties


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.unity_baker_props = bpy.props.PointerProperty(type=UnityBakerProperties)
    print("Unity Texture Baker зарегистрирован")


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.unity_baker_props
    print("Unity Texture Baker удален")


if __name__ == "__main__":
    register()