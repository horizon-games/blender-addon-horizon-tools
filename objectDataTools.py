import bpy


class HORIZON_PT_ObjectDataToolsUI(bpy.types.Panel):
    """Creates a Panel in the object data context of the properties editor"""
    bl_label = "Horizon Object Data Tools"
    bl_idname = "horizon.object_data_tools"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "data"

    def draw(self, context):
        layout = self.layout
        scn = context.scene

        row = layout.row()
        if scn.show_options_01:
            row.prop(scn, "show_options_01", icon="DOWNARROW_HLT", text="", emboss=False)
        else:
            row.prop(scn, "show_options_01", icon="RIGHTARROW", text="", emboss=False)

        row.label(text='Copy Vertex Color Channels')
        if scn.show_options_01:
            var_group = scn.copy_vertex_color_channels_vars
            row = layout.row()
            row.prop(var_group, 'nameSrc', expand=True)
            row = layout.row()
            row.prop(var_group, 'channelsSrc', expand=True)
            row = layout.row()
            row.prop(var_group, 'nameDst', expand=True)
            row = layout.row()
            row.prop(var_group, 'channelsDst', expand=True)
            row = layout.row()
            row.operator("horizon.copy_vertex_color_channels")

        row = layout.row()
        if scn.show_options_02:
            row.prop(scn, "show_options_02", icon="DOWNARROW_HLT", text="", emboss=False)
        else:
            row.prop(scn, "show_options_02", icon="RIGHTARROW", text="", emboss=False)

        row.label(text='AO Vertex Color Baker')
        if scn.show_options_02:
            var_group = scn.bake_ao_vars
            # row = layout.row()
            # row.prop(var_group, 'nameSrc', expand=True)
            row = layout.row()
            # row.prop_search(scn, "theChosenObject", scn, "objects")
            row.prop_search(var_group, "nameSrc", scn, "objects", icon='OBJECT_DATA')
            row = layout.row()
            row.operator("horizon.bake_ambient_occlusion_to_vertex_color")

        row = layout.row()
        if scn.show_options_03:
            row.prop(scn, "show_options_03", icon="DOWNARROW_HLT", text="", emboss=False)
        else:
            row.prop(scn, "show_options_03", icon="RIGHTARROW", text="", emboss=False)

        row.label(text='Misc.')
        if scn.show_options_03:
            row = layout.row()
            row.operator("horizon.squash_attributes")
            row = layout.row()
            row.operator("horizon.generate_centroid_shape_keys")
            row = layout.row()
            row.operator("horizon.apply_modifiers_to_selected")


def register():
    bpy.types.Scene.show_options_01 = bpy.props.BoolProperty(name='Copy Vertex Color Channels', default=False)
    bpy.types.Scene.show_options_02 = bpy.props.BoolProperty(name='AO Vertex Color Baker', default=False)
    bpy.types.Scene.show_options_03 = bpy.props.BoolProperty(name='Show Misc.', default=False)
    bpy.utils.register_class(HORIZON_PT_ObjectDataToolsUI)


def unregister():
    del bpy.types.Scene.show_options_01
    del bpy.types.Scene.show_options_02
    del bpy.types.Scene.show_options_03
    bpy.utils.unregister_class(HORIZON_PT_ObjectDataToolsUI)


if __name__ == "__main__":
    register()
