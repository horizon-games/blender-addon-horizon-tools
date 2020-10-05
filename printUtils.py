import bpy

def print(data):
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'CONSOLE':
                override = {'window': window, 'screen': screen, 'area': area}
                bpy.ops.console.scrollback_append(override, text=str(data), type="OUTPUT")


def describeThing(thing):
    pr('describing thing:')
    pr('  str:'+str(thing))
    pr('  type: ' + str(type(thing)))

def err(msg):
    pr('ERROR: ' + msg)
    raise Exception(msg)

