import bpy


def write_some_data(context, filepath, use_some_setting):
    print("running write_some_data...")
    f = open(filepath, 'w', encoding='utf-8')
    f.write("Hello World %s" % use_some_setting)
    f.close()

    return {'FINISHED'}


# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class HORIZON_OT_ExportCustomGLTF(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "horizon.export_custom_gltf"
    bl_label = "Export Custom GLTF"

    # ExportHelper mixin class uses this
    filename_ext = ".gltf"

    filter_glob: StringProperty(
        default="*.gltf",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        context.area.type = 'VIEW_3D'
        for obj in context.scene.objects: 
            context.view_layer.objects.active = obj
            if obj.data.shape_keys:
                print(obj.name, obj, obj.type)

                # remove all shape keys
                shapeKeys = obj.data.shape_keys.key_blocks
                while len(shapeKeys) > 1:
                    obj.active_shape_key_index = 1
                    bpy.ops.object.shape_key_remove(all=False) #shapekeys removed backwards to Basis on original object
                obj.active_shape_key_index = 0
                bpy.ops.object.shape_key_remove(all=False)

                modifier = obj.modifiers.new(name='EdgeSplit', type='EDGE_SPLIT')
                modifier.use_edge_angle = False
                bpy.ops.object.modifier_apply(modifier=modifier.name)
                # bpy.ops.horizon.generate_centroid_shape_keys()

        bpy.ops.export_scene.gltf(
            filepath = self.filepath,
            use_selection = True,
            export_selected = True,
            export_format = 'GLTF_SEPARATE',
            export_colors = True,
            export_morph = True,
            export_morph_normal = False
        )
        context.area.type = 'PROPERTIES'
        return {'FINISHED'}
        # return write_some_data(context, self.filepath, self.use_setting)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(HORIZON_OT_ExportCustomGLTF.bl_idname, text="Horizon Custom GLTF Export Operator")


def register():
    bpy.utils.register_class(HORIZON_OT_ExportCustomGLTF)
    # bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(HORIZON_OT_ExportCustomGLTF)
    # bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
