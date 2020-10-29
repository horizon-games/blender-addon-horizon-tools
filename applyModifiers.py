import bpy
from bpy.types import Operator

def print(data):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'CONSOLE':
                override = {'window': window, 'screen': screen, 'area': area}
                bpy.ops.console.scrollback_append(override, text=str(data), type="OUTPUT")

def pr(msg):
    print(msg)

def err(msg):
    pr('ERROR: ' + msg)
    raise Exception(msg)

def describeThing(thing):
    pr('describing thing:')
    pr('  str:'+str(thing))
    pr('  type: ' + str(type(thing)))


def applyModifiersToSelected(context):
    selection = list(bpy.context.selected_objects)
    for obj in selection:
        bpy.context.view_layer.objects.active = obj
        for modifier in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=modifier.name)


class HORIZON_OT_ApplyModifiersToSelected(Operator):
    bl_idname = "horizon.apply_modifiers_to_selected"
    bl_label = "Apply Modifiers To Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        applyModifiersToSelected(context)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(HORIZON_OT_ApplyModifiersToSelected)

def unregister():
    bpy.utils.unregister_class(HORIZON_OT_ApplyModifiersToSelected)

if __name__ == "__main__":
    register()
