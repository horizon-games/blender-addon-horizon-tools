import bpy


class HORIZON_PT_SceneToolsUI(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Horizon Scene Tools"
    bl_idname = "horizon.scene_tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.scale_y = 2.0
        row.operator("horizon.export_custom_gltf")



def register():
    bpy.utils.register_class(HORIZON_PT_SceneToolsUI)


def unregister():
    bpy.utils.unregister_class(HORIZON_PT_SceneToolsUI)


if __name__ == "__main__":
    register()
