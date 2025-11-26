import bpy
import os
from bpy.props import StringProperty, FloatProperty
from bpy.types import Operator, Panel

def load_image(filepath):
    return bpy.data.images.load(filepath, check_existing=True)

def create_tiled_material(context):
    mat = bpy.data.materials.new(name="Tiled Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    nodes.clear()

    import os
    addon_dir = os.path.dirname(os.path.realpath(__file__))
    json_path = os.path.join(addon_dir, "material_node_structure.json")
    with open(json_path, "r") as f:
        node_data = json.load(f)

    created_nodes = {}

    for node in node_data["nodes"]:
        new_node = nodes.new(type=node["type"])
        new_node.name = node["name"]
        new_node.location = node["location"]
        created_nodes[node["name"]] = new_node

        if node["type"] == "TEX_IMAGE":
            if "image" in node:
                image = bpy.data.images.get(node["image"])
                if not image:
                    image = bpy.data.images.load(node["image"])
                new_node.image = image
        elif node["type"] == "MAPPING":
            if "vector_type" in node:
                new_node.vector_type = node["vector_type"]

    for link in node_data["links"]:
        from_node = created_nodes[link["from_node"]]
        to_node = created_nodes[link["to_node"]]
        links.new(from_node.outputs[link["from_socket"]], to_node.inputs[link["to_socket"]])

    material_output = next(node for node in created_nodes.values() if node.type == 'OUTPUT_MATERIAL')
    mat.node_tree.nodes.active = material_output

    return mat

class MATERIAL_OT_create_tiled_material(Operator):
    bl_idname = "material.create_tiled_material"
    bl_label = "Create Tiled Material"
    
    def execute(self, context):
        obj = context.active_object
        if obj:
            mat = create_tiled_material(context)
            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
        return {'FINISHED'}

class MATERIAL_OT_load_texture(Operator):
    bl_idname = "material.load_texture"
    bl_label = "Load Texture"
    
    filepath: StringProperty(subtype="FILE_PATH")
    texture_type: StringProperty()
    
    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "No file selected")
            return {'CANCELLED'}
        
        try:
            image = load_image(self.filepath)
            material = context.object.active_material
            
            if self.texture_type.endswith('_a'):
                nodes = material.node_tree.nodes
                image_node = nodes.get(f"Image Texture.{self.texture_type}")
                if image_node:
                    image_node.image = image
                
                n_filepath = self.filepath.replace('_a.', '_n.')
                if os.path.exists(n_filepath):
                    n_image = load_image(n_filepath)
                    n_image_node = nodes.get(f"Image Texture.{self.texture_type.replace('_a', '_n')}")
                    if n_image_node:
                        n_image_node.image = n_image
            
            context.scene.tile_texture_paths[self.texture_type] = self.filepath
            
        except Exception as e:
            self.report({'ERROR'}, f"Error loading texture: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class MATERIAL_PT_tiled_material(Panel):
    bl_label = "Tiled Material"
    bl_idname = "MATERIAL_PT_tiled_material"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        
        layout.operator("material.create_tiled_material", text="Create Tiled Material")
        
        for i in range(4):
            row = layout.row()
            row.prop(scene, f"tile{i+1}_path", text=f"Tile {i+1}")
            row.operator("material.load_texture", text="", icon='FILE_FOLDER').texture_type = f"tile{i+1}_a"
        
        layout.label(text="Tile Scales:")
        for i in range(4):
            layout.prop(scene, f"tile{i+1}_scale", text=f"Tile {i+1} Scale")

def register():
    bpy.utils.register_class(MATERIAL_OT_create_tiled_material)
    bpy.utils.register_class(MATERIAL_OT_load_texture)
    bpy.utils.register_class(MATERIAL_PT_tiled_material)
    
    bpy.types.Scene.tile_texture_paths = {}
    for i in range(4):
        setattr(bpy.types.Scene, f"tile{i+1}_path", StringProperty(name=f"Tile {i+1} Path"))
        setattr(bpy.types.Scene, f"tile{i+1}_scale", FloatProperty(name=f"Tile {i+1} Scale", default=1.0, min=0.1, max=10.0))

def unregister():
    bpy.utils.unregister_class(MATERIAL_OT_create_tiled_material)
    bpy.utils.unregister_class(MATERIAL_OT_load_texture)
    bpy.utils.unregister_class(MATERIAL_PT_tiled_material)
    
    for i in range(4):
        delattr(bpy.types.Scene, f"tile{i+1}_path")
        delattr(bpy.types.Scene, f"tile{i+1}_scale")
    del bpy.types.Scene.tile_texture_paths

if __name__ == "__main__":
    register()