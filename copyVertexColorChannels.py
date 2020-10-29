import sys
import bpy
import numpy as np
from bpy.types import Operator
import traceback
import mathutils

channelDict = {
  "R": 0,
  "G": 1,
  "B": 2,
  "A": 3
}

class InterfaceCopyVertexColorChannelsVars(bpy.types.PropertyGroup):
    nameSrc: bpy.props.StringProperty(name="Src",
                                        description="Some elaborate description",
                                        default="",
                                        maxlen=256,
                                        subtype="NONE")

    nameDst: bpy.props.StringProperty(name="Dst",
                                        description="Some elaborate description",
                                        default="",
                                        maxlen=256,
                                        subtype="NONE")

    channelsSrc = bpy.props.EnumProperty(
        items=[
            ('R', 'R', 'R', '', 0),
            ('G', 'G', 'G', '', 1),
            ('B', 'B', 'B', '', 2),
            ('A', 'A', 'A', '', 3)
        ],
        default='R'
    )

    channelsDst = bpy.props.EnumProperty(
        items=[
            ('R', 'R', 'R', '', 0),
            ('G', 'G', 'G', '', 1),
            ('B', 'B', 'B', '', 2),
            ('A', 'A', 'A', '', 3)
        ],
        default='R'
    )


def copyVertexColorChannels(context):
    def print(data):
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'CONSOLE':
                    override = {'window': window, 'screen': screen, 'area': area}
                    bpy.ops.console.scrollback_append(override, text=str(data), type="OUTPUT")

    ob = bpy.context.active_object

    print('---')
    # get the material
    # mat = bpy.data.materials['surface']
    slot = ob.material_slots[0]
    mat = slot.material
    # get the nodes
    nodes = mat.node_tree.nodes

    # get the links
    links = mat.node_tree.links

    # get some specific node:
    # returns None if the node does not exist
    exporterMatNode = nodes.get("exporter")

    verbose = True

    def describeThing(thing):
        pr('describing thing:')
        pr('  str:'+str(thing))
        pr('  type: ' + str(type(thing)))

    def gammaCorrect(color, gamma):
        if(not isinstance(color, list)):
            pr('??'+str(color))
    #        color = list(color)
    #    color = coerceColor(color)
        color[0] = pow(color[0], gamma)
        color[1] = pow(color[1], gamma)
        color[2] = pow(color[2], gamma)
        return color


    def coerceColor(val):
        if(isinstance(val, float)):
            return [val, val, val, 1.0]
        else:
            c = list(val)
            if(len(c) == 3):
                c.append(1.0)
            str('-------'+str(c))
            return c

    def coerceFac(val):
        fac = 0.0
        if(not isinstance(val, float)):
    #        describeThing(val)
            for i in range(3):
                fac += val[i]
            fac /= 3.0
        else:
            fac = val
        return fac

    def lerp(vals1, vals2, amt):
        if(isinstance(vals1, np.float64)):
            vals1 = [vals1, vals1, vals1, 1.0]
        if(isinstance(vals2, np.float64)):
            vals2 = [vals2, vals2, vals2, 1.0]
        while(len(vals1) < len(vals2)):
            vals1 = np.append(vals1, 1.0)
        while(len(vals1) > len(vals2)):
            vals2 = np.append(vals2, 1.0)
            
        amt = coerceFac(amt)
            
        result = []
        for i in range(3):
            result.append(vals1[i] * (1.0-amt) + vals2[i] * amt)
        return result

    def pr(msg):
        if(verbose):
            print(msg)

    def err(msg):
        pr('ERROR: ' + msg)
        raise Exception(msg)

    def dataTransferColor(loops, dstName, srcName, singleChannelDst = None, singleChannelSrc = None):
        dst = ob.data.vertex_colors[dstName]
        src = ob.data.vertex_colors[srcName]
        
        for l in range(loops):
            cSrc = src.data[l].color
    #        cSrc = gammaCorrect(cSrc, 0.4545)
            cDst = dst.data[l].color
            describeThing(cSrc)
            if(singleChannelDst == None):
                cDst[0] = cSrc[0]
                cDst[1] = cSrc[1]
                cDst[2] = cSrc[2]
            else:
                if(singleChannelSrc == None):
                    fac = coerceFac(cSrc)
                    cDst[singleChannelDst] = fac
                else:
                    cDst[singleChannelDst] = cSrc[singleChannelSrc]
                
    # def dataTransferUv(loops, dstName, srcName, singleChannel = None):
    #     dst = ob.data.uv_layers[dstName]
    #     src = ob.data.uv_layers[srcName]
    #     for l in range(loops):
    #         cSrc = src.data[l].uv
    #         cDst = dst.data[l].uv
    #         describeThing(cSrc)
    #         if(singleChannel == None):
    #             cDst[0] = cSrc[0]
    #             cDst[1] = cSrc[1]
    #         else:
    #             fac = coerceFac(cSrc)
    #             cDst[singleChannel] = fac
                


    #vertex colors are in fact stored per loop-vertex -&gt; MeshLoopColorLayer
    if ob.type == 'MESH':
        
        #how many loops do we have ?
        loops = len(ob.data.loops)
        print(str(loops))
    
        #go through each vertex color layer
        for vcol in ob.data.vertex_colors:
            print('vertex color channel: ' + vcol.name)
        
        var_group = context.scene.copy_vertex_color_channels_vars

        dataTransferColor(loops, var_group.nameDst, var_group.nameSrc, channelDict[var_group.channelsDst], channelDict[var_group.channelsSrc])



class HORIZON_OT_CopyVertexColorChannels(Operator):
    bl_idname = "horizon.copy_vertex_color_channels"
    bl_label = "Copy Vertex Color Channels"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        copyVertexColorChannels(context)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(InterfaceCopyVertexColorChannelsVars)
    bpy.types.Scene.copy_vertex_color_channels_vars = bpy.props.PointerProperty(type=InterfaceCopyVertexColorChannelsVars)
    bpy.utils.register_class(HORIZON_OT_CopyVertexColorChannels)

def unregister():
    del bpy.types.Scene.copy_vertex_color_channels_vars
    bpy.utils.unregister_class(InterfaceCopyVertexColorChannelsVars)
    bpy.utils.unregister_class(HORIZON_OT_CopyVertexColorChannels)

if __name__ == "__main__":
    register()
