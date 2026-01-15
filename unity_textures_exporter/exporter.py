bl_info = {
    "name": "Export Unity Textures (Bake + Albedo/Normal/Metallic/Roughness/Specular)",
    "author": "ChatGPT",
    "version": (1, 2),
    "blender": (2, 93, 0),
    "location": "3D View > Object > Export Unity Textures",
    "description": "Автоматически бейкает и экспортирует PBR-текстуры для Unity",
    "category": "Import-Export",
}

import bpy
import os

# ------------------------------------------------------------
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ------------------------------------------------------------

def find_principled_bsdf(material):
    if not material or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            return node
    return None


def create_bake_image(name, size):
    img = bpy.data.images.new(name=name, width=size, height=size)
    img.generated_color = (0, 0, 0, 1)
    return img


def save_image(image, export_path):
    image.filepath_raw = os.path.join(export_path, image.name + ".png")
    image.file_format = 'PNG'
    image.save()


def bake_socket(obj, material, bake_type, image_name, size, export_path):
    # создаём изображение
    image = bpy.data.images.new(image_name, width=size, height=size, alpha=False)

    nodes = material.node_tree.nodes

    # image texture node (ОБЯЗАТЕЛЬНО активный)
    img_node = nodes.new(type='ShaderNodeTexImage')
    img_node.image = image
    nodes.active = img_node

    # подготовка объекта
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # настройки Cycles
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 1

    # настройки bake
    scene.render.bake.use_clear = True
    scene.render.bake.use_selected_to_active = False

    # сам bake
    bpy.ops.object.bake(type=bake_type)

    # сохранение
    image.filepath_raw = os.path.join(export_path, image_name + '.png')
    image.file_format = 'PNG'
    image.save()

    # очистка
    nodes.remove(img_node)


# ------------------------------------------------------------
# ОСНОВНАЯ ЛОГИКА ЭКСПОРТА
# ------------------------------------------------------------

def export_unity_textures(obj, export_path, size=2048):
    material = obj.active_material
    bsdf = find_principled_bsdf(material)
    if not bsdf:
        return

    os.makedirs(export_path, exist_ok=True)

    bake_socket(obj, material, bsdf, "Albedo", 'DIFFUSE', size, export_path)
    bake_socket(obj, material, bsdf, "Normal", 'NORMAL', size, export_path)
    bake_socket(obj, material, bsdf, "Metallic", 'EMIT', size, export_path)
    bake_socket(obj, material, bsdf, "Roughness", 'ROUGHNESS', size, export_path)
    bake_socket(obj, material, bsdf, "Specular", 'GLOSSY', size, export_path)


# ------------------------------------------------------------
# ОПЕРАТОР BLENDER
# ------------------------------------------------------------

class ExportUnityTexturesOperator(bpy.types.Operator):
    bl_idname = "object.export_unity_textures"
    bl_label = "Export Unity Textures (Bake)"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(
        name="Export Path",
        description="Папка для экспорта текстур",
        subtype='DIR_PATH'
    )

    texture_size: bpy.props.IntProperty(
        name="Texture Size",
        default=2048,
        min=256,
        max=8192
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'WARNING'}, "Активный объект или материал не найден")
            return {'CANCELLED'}

        export_unity_textures(obj, self.directory, self.texture_size)
        self.report({'INFO'}, "Текстуры успешно запечены и экспортированы")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# ------------------------------------------------------------
# РЕГИСТРАЦИЯ
# ------------------------------------------------------------

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
