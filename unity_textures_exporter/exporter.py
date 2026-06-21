import bpy
import os


def find_principled_bsdf(material):
    if not material or not material.use_nodes:
        return None
    for node in material.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            return node
    return None


def save_image(image, export_path, material_name, suffix):
    if not image:
        return

    filename = f"{material_name}_{suffix}.png"
    filepath = os.path.join(export_path, filename)

    image.filepath_raw = filepath
    image.file_format = 'PNG'
    image.save()
    

def get_linked_image(input_socket):
    if not input_socket or not input_socket.is_linked:
        return None

    from_node = input_socket.links[0].from_node
    if from_node.type == 'TEX_IMAGE':
        return from_node.image

    return None


def get_normal_image(bsdf):
    normal_input = bsdf.inputs.get("Normal")
    if not normal_input or not normal_input.is_linked:
        return None

    normal_node = normal_input.links[0].from_node
    if normal_node.type != 'NORMAL_MAP':
        return None


    color_input = normal_node.inputs.get("Color")
    if not color_input or not color_input.is_linked:
        return None


    tex_node = color_input.links[0].from_node
    if tex_node.type == 'TEX_IMAGE':
        return tex_node.image

    return None


def export_unity_textures(material, export_path):
    bsdf = find_principled_bsdf(material)
    if not bsdf:
        return

    os.makedirs(export_path, exist_ok=True)

    # Albedo 
    albedo_img = get_linked_image(bsdf.inputs.get("Base Color"))
    save_image(albedo_img, export_path, material.name, "Albedo")

    # Normal
    normal_img = get_normal_image(bsdf)
    save_image(normal_img, export_path, material.name, "Normal")

    # Metallic
    metallic_img = get_linked_image(bsdf.inputs.get("Metallic"))
    save_image(metallic_img, export_path, material.name, "Metallic")

    # Roughness
    roughness_img = get_linked_image(bsdf.inputs.get("Roughness"))
    save_image(roughness_img, export_path, material.name, "Roughness")

    # Specular
    specular_img = get_linked_image(bsdf.inputs.get("Specular"))
    save_image(specular_img, export_path, material.name, "Specular")
    
    
class ExportUnityTexturesOperator(bpy.types.Operator):
    bl_idname = "object.export_unity_textures"
    bl_label = "Export Unity Textures"
    bl_options = {'REGISTER', 'UNDO'}


    directory: bpy.props.StringProperty(
        name="Export Path",
        description="Папка для экспорта текстур",
        subtype='DIR_PATH'
    )

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.active_material:
            self.report({'WARNING'}, "Активный объект или материал не найден")
            return {'CANCELLED'}

        export_unity_textures(obj.active_material, self.directory)
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