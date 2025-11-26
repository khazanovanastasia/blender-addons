bl_info = {
    "name": "Export Unity Textures",
    "author": "ChatGPT",
    "version": (1, 0),
    "blender": (2, 93, 0),
    "location": "3D View > Object > Export Unity Textures",
    "description": "Экспортирует текстуры активного материала объекта в формате, пригодном для Unity",
    "category": "Import-Export",
}

import bpy
import os
from bpy_extras.image_utils import load_image

def export_textures(material, export_path):
    if not material.use_nodes:
        return

    bsdf = None
    for node in material.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            bsdf = node
            break

    if not bsdf:
        return

    def save_image(image, suffix):
        if not image:
            return
        filename = f"{material.name}_{suffix}.png"
        filepath = os.path.join(export_path, filename)
        image.filepath_raw = filepath
        image.file_format = 'PNG'
        image.save()

    # Собираем основные текстуры
    for input_name, suffix in {
        "Base Color": "Albedo",
        "Normal": "Normal",
        "Metallic": "Metallic",
        "Roughness": "Roughness",
        "Specular": "Specular"
    }.items():
        link = bsdf.inputs.get(input_name)
        if link and link.is_linked:
            tex_node = link.links[0].from_node
            if tex_node.type == 'TEX_IMAGE':
                save_image(tex_node.image, suffix)

class ExportUnityTexturesOperator(bpy.types.Operator):
    bl_idname = "object.export_unity_textures"
    bl_label = "Export Unity Textures"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(
        name="Export Path",
        description="Куда сохранять текстуры",
        subtype='DIR_PATH'
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'WARNING'}, "Объект или материал не найден")
            return {'CANCELLED'}

        export_textures(obj.active_material, self.directory)
        self.report({'INFO'}, f"Текстуры экспортированы в {self.directory}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def menu_func(self, context):
    self.layout.operator(ExportUnityTexturesOperator.bl_idname)

def register():
    bpy.utils.register_class(ExportUnityTexturesOperator)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ExportUnityTexturesOperator)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()
