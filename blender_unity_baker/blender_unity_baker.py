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
import os
from pathlib import Path


def create_image(name, width, height, alpha=False):
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])

    img = bpy.data.images.new(
        name=name,
        width=width,
        height=height,
        alpha=alpha,
        float_buffer=False
    )
    return img


def setup_image_node_in_material(material, image, active=True):
    """Добавляет Image Texture нод в конкретный материал."""
    nodes = material.node_tree.nodes
    img_node = nodes.new(type='ShaderNodeTexImage')
    img_node.image = image
    img_node.select = active
    if active:
        nodes.active = img_node
    return img_node


def setup_image_node_all_materials(obj, image):
    """
    Добавляет один и тот же Image Texture нод (с одним изображением)
    во все материалы объекта и делает его активным в каждом.
    Возвращает список добавленных нодов для последующего удаления.
    """
    added_nodes = []
    for mat in obj.data.materials:
        if mat is None or not mat.use_nodes:
            continue
        node = setup_image_node_in_material(mat, image, active=True)
        added_nodes.append((mat, node))
    return added_nodes


def remove_nodes(node_list):
    """Удаляет список нодов вида [(material, node), ...]."""
    for mat, node in node_list:
        if mat and mat.use_nodes and node.name in mat.node_tree.nodes:
            mat.node_tree.nodes.remove(node)


def bake_map(obj, bake_type, image, samples=128):
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = samples
    bpy.context.scene.cycles.bake_type = bake_type

    original_view_transform = bpy.context.scene.view_settings.view_transform
    if bake_type in ['EMIT', 'ROUGHNESS']:
        bpy.context.scene.view_settings.view_transform = 'Standard'

    if bake_type == 'DIFFUSE':
        bpy.context.scene.render.bake.use_pass_direct = False
        bpy.context.scene.render.bake.use_pass_indirect = False
        bpy.context.scene.render.bake.use_pass_color = True
    elif bake_type == 'NORMAL':
        bpy.context.scene.render.bake.normal_space = 'TANGENT'

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    try:
        bpy.ops.object.bake(type=bake_type)
        print(f"  ✓ Запекание {bake_type} завершено")
    except Exception as e:
        print(f"  ❌ Ошибка запекания {bake_type}: {str(e)}")

    bpy.context.scene.view_settings.view_transform = original_view_transform

    return image


def save_image(image, filepath, file_format='PNG'):
    image.filepath_raw = filepath
    image.file_format = file_format

    if file_format == 'PNG':
        bpy.context.scene.render.image_settings.color_mode = 'RGBA'
        bpy.context.scene.render.image_settings.compression = 15

    image.save()
    print(f"✓ Сохранено: {filepath}")


def pack_mrao_channels(metallic_path, roughness_path, ao_path, output_path):
    try:
        from PIL import Image
    except ImportError:
        print("⚠ PIL/Pillow не установлен. Установите через: pip install Pillow")
        return False

    metallic = Image.open(metallic_path).convert('L')
    roughness = Image.open(roughness_path).convert('L')
    ao = Image.open(ao_path).convert('L')

    width, height = metallic.size
    alpha = Image.new('L', (width, height), 255)

    mrao = Image.merge('RGBA', (metallic, roughness, ao, alpha))
    mrao.save(output_path)

    print(f"✓ MRAO упакован: {output_path}")
    return True


# ---------------------------------------------------------------------------
# Вспомогательные функции для запекания single-channel через Emission
# ---------------------------------------------------------------------------

def _get_principled_nodes(obj):
    """Возвращает dict {material: principled_node} для всех материалов объекта."""
    result = {}
    for mat in obj.data.materials:
        if mat is None or not mat.use_nodes:
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                result[mat] = node
                break
    return result


def _get_output_node(mat):
    for node in mat.node_tree.nodes:
        if node.type == 'OUTPUT_MATERIAL':
            return node
    return None


def bake_single_channel_emit(obj, channel_name, target_img, samples):
    """
    Запекает один канал (Metallic или Roughness) через Emission trick
    во всех материалах объекта одновременно.
    """
    principled_map = _get_principled_nodes(obj)

    # Сохраняем и подменяем output -> emission в каждом материале
    state_per_mat = []
    temp_nodes_per_mat = []

    for mat, principled in principled_map.items():
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        output = _get_output_node(mat)
        if output is None:
            continue

        original_surface_link = None
        if output.inputs['Surface'].is_linked:
            original_surface_link = output.inputs['Surface'].links[0].from_socket

        emission = nodes.new(type='ShaderNodeEmission')
        emission.inputs['Strength'].default_value = 1.0
        temp_nodes = [emission]

        if principled.inputs[channel_name].is_linked:
            channel_socket = principled.inputs[channel_name].links[0].from_socket
            try:
                separate = nodes.new(type='ShaderNodeSeparateColor')
                combine = nodes.new(type='ShaderNodeCombineColor')
            except Exception:
                separate = nodes.new(type='ShaderNodeSeparateRGB')
                combine = nodes.new(type='ShaderNodeCombineRGB')

            links.new(channel_socket, separate.inputs[0])
            links.new(separate.outputs[0], combine.inputs[0])
            links.new(separate.outputs[0], combine.inputs[1])
            links.new(separate.outputs[0], combine.inputs[2])
            links.new(combine.outputs[0], emission.inputs['Color'])
            temp_nodes += [separate, combine]
        else:
            value = principled.inputs[channel_name].default_value
            emission.inputs['Color'].default_value = (value, value, value, 1.0)

        links.new(emission.outputs['Emission'], output.inputs['Surface'])

        state_per_mat.append((mat, nodes, links, output, original_surface_link))
        temp_nodes_per_mat.append((mat, nodes, temp_nodes))

    # Добавляем image node во все материалы и запекаем
    img_nodes = setup_image_node_all_materials(obj, target_img)
    bake_map(obj, 'EMIT', target_img, samples)
    remove_nodes(img_nodes)

    # Восстанавливаем все материалы
    for mat, nodes, links, output, original_surface_link in state_per_mat:
        if original_surface_link:
            links.new(original_surface_link, output.inputs['Surface'])

    for mat, nodes, temp_nodes in temp_nodes_per_mat:
        for node in temp_nodes:
            if node.name in nodes:
                nodes.remove(node)


# ---------------------------------------------------------------------------
# Главная функция запекания
# ---------------------------------------------------------------------------

def bake_unity_textures(obj, export_path, albedo_res=1024, normal_res=1024, mrao_res=1024,
                        samples=128, bake_albedo=True, bake_normal=True, bake_mrao=True):

    if not obj or obj.type != 'MESH':
        print("⚠ Выберите mesh объект")
        return {'CANCELLED'}

    if not obj.data.materials:
        print("⚠ У объекта нет материалов")
        return {'CANCELLED'}

    Path(export_path).mkdir(parents=True, exist_ok=True)

    obj_name = obj.name
    mat_names = [m.name for m in obj.data.materials if m]

    print(f"\n{'='*60}")
    print(f"Начинаем запекание для объекта: {obj_name}")
    print(f"Материалов: {len(mat_names)} — {', '.join(mat_names)}")
    print(f"Разрешения:")
    if bake_albedo:
        print(f"  • Albedo: {albedo_res}x{albedo_res}")
    if bake_normal:
        print(f"  • Normal: {normal_res}x{normal_res}")
    if bake_mrao:
        print(f"  • MRAO: {mrao_res}x{mrao_res}")
    print(f"Samples: {samples}")
    print(f"{'='*60}\n")

    # Убеждаемся, что все материалы используют ноды
    for mat in obj.data.materials:
        if mat and not mat.use_nodes:
            mat.use_nodes = True

    temp_images = {}

    try:
        # ================================================================
        # 1. ALBEDO (Base Color)
        # ================================================================
        if bake_albedo:
            print("🎨 Запекаем Albedo...")
            albedo_img = create_image(f"{obj_name}_Albedo", albedo_res, albedo_res, alpha=False)
            temp_images['albedo'] = albedo_img

            img_nodes = setup_image_node_all_materials(obj, albedo_img)
            bake_map(obj, 'DIFFUSE', albedo_img, samples)
            remove_nodes(img_nodes)

            albedo_path = os.path.join(export_path, f"{obj_name}_Albedo.png")
            save_image(albedo_img, albedo_path)
        else:
            print("⏭️ Пропускаем Albedo (отключено)")
            albedo_path = None

        # ================================================================
        # 2. NORMAL MAP
        # ================================================================
        if bake_normal:
            print("🔵 Запекаем Normal Map...")
            normal_img = create_image(f"{obj_name}_Normal", normal_res, normal_res, alpha=False)
            temp_images['normal'] = normal_img

            img_nodes = setup_image_node_all_materials(obj, normal_img)
            bake_map(obj, 'NORMAL', normal_img, samples)
            remove_nodes(img_nodes)

            normal_path = os.path.join(export_path, f"{obj_name}_Normal.png")
            save_image(normal_img, normal_path)
        else:
            print("⏭️ Пропускаем Normal Map (отключено)")
            normal_path = None

        # ================================================================
        # 3-5. MRAO (Metallic, Roughness, AO)
        # ================================================================
        if not bake_mrao:
            print("⏭️ Пропускаем MRAO (отключено)")
            mrao_path = None
        else:
            # ------------------------------------------------------------
            # 3. METALLIC
            # ------------------------------------------------------------
            print("⚙️ Запекаем Metallic...")
            metallic_img = create_image(f"{obj_name}_Metallic", mrao_res, mrao_res, alpha=False)
            temp_images['metallic'] = metallic_img
            bake_single_channel_emit(obj, 'Metallic', metallic_img, samples)
            metallic_path = os.path.join(export_path, f"{obj_name}_Metallic_temp.png")
            save_image(metallic_img, metallic_path)

            # ------------------------------------------------------------
            # 4. ROUGHNESS
            # ------------------------------------------------------------
            print("🔘 Запекаем Roughness...")
            roughness_img = create_image(f"{obj_name}_Roughness", mrao_res, mrao_res, alpha=False)
            temp_images['roughness'] = roughness_img
            bake_single_channel_emit(obj, 'Roughness', roughness_img, samples)
            roughness_path = os.path.join(export_path, f"{obj_name}_Roughness_temp.png")
            save_image(roughness_img, roughness_path)

            # ------------------------------------------------------------
            # 5. AMBIENT OCCLUSION
            # ------------------------------------------------------------
            print("🌑 Запекаем Ambient Occlusion...")
            ao_img = create_image(f"{obj_name}_AO", mrao_res, mrao_res, alpha=False)
            temp_images['ao'] = ao_img

            img_nodes = setup_image_node_all_materials(obj, ao_img)
            bake_map(obj, 'AO', ao_img, samples)
            remove_nodes(img_nodes)

            ao_path = os.path.join(export_path, f"{obj_name}_AO_temp.png")
            save_image(ao_img, ao_path)

            # ------------------------------------------------------------
            # 6. MRAO PACKING
            # ------------------------------------------------------------
            print("📦 Упаковываем MRAO...")
            mrao_path = os.path.join(export_path, f"{obj_name}_MRAO.png")

            if pack_mrao_channels(metallic_path, roughness_path, ao_path, mrao_path):
                for temp_path in [metallic_path, roughness_path, ao_path]:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

        print(f"\n{'='*60}")
        print(f"✓ Запекание завершено успешно!")
        print(f"📂 Файлы сохранены в: {export_path}")
        if bake_albedo:
            print(f"  - {obj_name}_Albedo.png ({albedo_res}x{albedo_res})")
        if bake_normal:
            print(f"  - {obj_name}_Normal.png ({normal_res}x{normal_res})")
        if bake_mrao:
            print(f"  - {obj_name}_MRAO.png ({mrao_res}x{mrao_res})")
        print(f"{'='*60}\n")

        return {'FINISHED'}

    except Exception as e:
        print(f"❌ Ошибка при запекании: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'CANCELLED'}

    finally:
        for img in temp_images.values():
            if img and img.name in bpy.data.images:
                bpy.data.images.remove(img)


class UNITY_OT_BakeTextures(bpy.types.Operator):
    bl_idname = "unity.bake_textures"
    bl_label = "Bake for Unity"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.unity_baker_props
        obj = context.active_object

        result = bake_unity_textures(
            obj=obj,
            export_path=bpy.path.abspath(props.export_path),
            albedo_res=int(props.albedo_resolution),
            normal_res=int(props.normal_resolution),
            mrao_res=int(props.mrao_resolution),
            samples=props.samples,
            bake_albedo=props.bake_albedo,
            bake_normal=props.bake_normal,
            bake_mrao=props.bake_mrao
        )

        if result == {'FINISHED'}:
            self.report({'INFO'}, "Запекание завершено успешно!")
        else:
            self.report({'ERROR'}, "Ошибка при запекании")

        return result


class UnityBakerProperties(bpy.types.PropertyGroup):
    export_path: bpy.props.StringProperty(
        name="Export Path",
        description="Путь для сохранения текстур",
        default="//Textures/",
        subtype='DIR_PATH'
    )

    resolution_preset: bpy.props.EnumProperty(
        name="Quick Preset",
        description="Быстрая установка одинакового разрешения для всех текстур",
        items=[
            ('CUSTOM', "Custom (Individual)", "Индивидуальные настройки для каждой текстуры"),
            ('512', "512x512 (All)", "512x512 для всех"),
            ('1024', "1024x1024 (All)", "1024x1024 для всех"),
            ('2048', "2048x2048 (All)", "2048x2048 для всех"),
            ('4096', "4096x4096 (All)", "4096x4096 для всех"),
        ],
        default='CUSTOM',
        update=lambda self, context: self.sync_resolutions()
    )

    albedo_resolution: bpy.props.EnumProperty(
        name="Albedo",
        description="Разрешение для Albedo текстуры",
        items=[
            ('512', "512x512", ""),
            ('1024', "1024x1024", ""),
            ('2048', "2048x2048", ""),
            ('4096', "4096x4096", ""),
        ],
        default='1024'
    )

    normal_resolution: bpy.props.EnumProperty(
        name="Normal",
        description="Разрешение для Normal Map",
        items=[
            ('512', "512x512", ""),
            ('1024', "1024x1024", ""),
            ('2048', "2048x2048", ""),
            ('4096', "4096x4096", ""),
        ],
        default='1024'
    )

    mrao_resolution: bpy.props.EnumProperty(
        name="MRAO",
        description="Разрешение для MRAO карты (Metallic/Roughness/AO)",
        items=[
            ('512', "512x512", ""),
            ('1024', "1024x1024", ""),
            ('2048', "2048x2048", ""),
            ('4096', "4096x4096", ""),
        ],
        default='1024'
    )

    samples: bpy.props.IntProperty(
        name="Samples",
        description="Количество сэмплов для Cycles",
        default=128,
        min=1,
        max=4096
    )

    bake_albedo: bpy.props.BoolProperty(
        name="Bake Albedo",
        description="Запекать Albedo текстуру",
        default=True
    )

    bake_normal: bpy.props.BoolProperty(
        name="Bake Normal",
        description="Запекать Normal Map",
        default=True
    )

    bake_mrao: bpy.props.BoolProperty(
        name="Bake MRAO",
        description="Запекать MRAO карту (Metallic/Roughness/AO)",
        default=True
    )

    def sync_resolutions(self):
        if self.resolution_preset != 'CUSTOM':
            self.albedo_resolution = self.resolution_preset
            self.normal_resolution = self.resolution_preset
            self.mrao_resolution = self.resolution_preset


class UNITY_PT_BakerPanel(bpy.types.Panel):
    bl_label = "Unity Texture Baker"
    bl_idname = "UNITY_PT_baker_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Unity Baker'

    def draw(self, context):
        layout = self.layout
        props = context.scene.unity_baker_props

        obj = context.active_object
        box = layout.box()
        if obj and obj.type == 'MESH':
            box.label(text=f"Объект: {obj.name}", icon='OBJECT_DATA')
            if obj.data.materials:
                mat_count = len(obj.data.materials)
                if mat_count == 1:
                    box.label(text=f"Материал: {obj.data.materials[0].name}", icon='MATERIAL')
                else:
                    box.label(text=f"Материалов: {mat_count} (будут объединены)", icon='MATERIAL')
                    for mat in obj.data.materials:
                        if mat:
                            box.label(text=f"  • {mat.name}")
            else:
                box.label(text="⚠ Нет материала!", icon='ERROR')
        else:
            box.label(text="⚠ Выберите mesh объект", icon='ERROR')

        layout.separator()

        layout.label(text="Экспорт:", icon='EXPORT')
        layout.prop(props, "export_path")

        layout.separator()

        layout.label(text="Разрешение:", icon='TEXTURE')
        layout.prop(props, "resolution_preset", text="")

        if props.resolution_preset == 'CUSTOM':
            box = layout.box()
            box.label(text="Индивидуальные разрешения:", icon='SETTINGS')

            row = box.row(align=True)
            row.prop(props, "bake_albedo", text="")
            row.label(text="Albedo:")
            row.prop(props, "albedo_resolution", text="")

            row = box.row(align=True)
            row.prop(props, "bake_normal", text="")
            row.label(text="Normal:")
            row.prop(props, "normal_resolution", text="")

            row = box.row(align=True)
            row.prop(props, "bake_mrao", text="")
            row.label(text="MRAO:")
            row.prop(props, "mrao_resolution", text="")
        else:
            box = layout.box()
            box.label(text="Выберите карты для запекания:", icon='CHECKMARK')
            box.prop(props, "bake_albedo")
            box.prop(props, "bake_normal")
            box.prop(props, "bake_mrao")

        layout.separator()

        layout.prop(props, "samples")

        layout.separator()

        row = layout.row()
        row.scale_y = 2.0

        maps_count = sum([props.bake_albedo, props.bake_normal, props.bake_mrao])
        if maps_count == 0:
            row.enabled = False
            row.operator("unity.bake_textures", text="Выберите хотя бы одну карту", icon='ERROR')
        else:
            row.operator("unity.bake_textures", text=f"Bake {maps_count} Map(s)", icon='RENDER_STILL')

        layout.separator()
        box = layout.box()
        box.label(text="Выходные файлы:", icon='FILE_IMAGE')

        if props.resolution_preset == 'CUSTOM':
            if props.bake_albedo:
                box.label(text=f"• Albedo.png ({props.albedo_resolution}x{props.albedo_resolution})")
            if props.bake_normal:
                box.label(text=f"• Normal.png ({props.normal_resolution}x{props.normal_resolution})")
            if props.bake_mrao:
                box.label(text=f"• MRAO.png ({props.mrao_resolution}x{props.mrao_resolution})")
        else:
            res = props.resolution_preset
            if props.bake_albedo:
                box.label(text=f"• Albedo.png ({res}x{res})")
            if props.bake_normal:
                box.label(text=f"• Normal.png ({res}x{res})")
            if props.bake_mrao:
                box.label(text=f"• MRAO.png ({res}x{res})")

        if maps_count == 0:
            box.label(text="Нет выбранных карт", icon='INFO')


classes = (
    UnityBakerProperties,
    UNITY_OT_BakeTextures,
    UNITY_PT_BakerPanel,
)


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