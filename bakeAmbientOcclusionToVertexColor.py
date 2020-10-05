import math
import sys
import bpy
from bpy.types import Operator
import numpy as np
import traceback
import mathutils
from mathutils.bvhtree import BVHTree
# from .printutils import *


class InterfaceBakeAOVars(bpy.types.PropertyGroup):
    nameSrc: bpy.props.StringProperty(name="Src",
                                        description="Some elaborate description",
                                        default="",
                                        maxlen=256,
                                        subtype="NONE")



def bakeSelected(context):
    ob = context.active_object
    if(context.scene.bake_ao_vars.nameSrc):
        obCaster = bpy.data.objects[context.scene.bake_ao_vars.nameSrc]
    else:
        obCaster = ob
    # get the material
    mat = bpy.data.materials['surface']
    # get the nodes
    nodes = mat.node_tree.nodes

    # get the links
    links = mat.node_tree.links

    # get some specific node:
    # returns None if the node does not exist
    exporterMatNode = nodes.get("exporter")

    def gammaCorrect(color, gamma):
        # if(not isinstance(color, list)):
            # print('??'+str(color))
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
            return c

    def coerceFac(val):
        fac = 0.0
        if(not isinstance(val, float)):
        #    describeThing(val)
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

    gr=(math.sqrt(5.0) + 1.0) / 2.0;  # golden ratio = 1.6180339887498948482
    ga=(2.0 - gr) * 6.2831853072;  # golden angle = 2.39996322972865332

    def fibonacci_spiral_sphere(i, num_points):
        lat = math.asin(-1.0 + 2.0 * i / (num_points+1.0))
        lon = ga * i

        x = math.cos(lon)*math.cos(lat)
        y = math.sin(lon)*math.cos(lat)
        z = math.sin(lat)
        return [x, y, z]

    def mix(a, b, amt):
        return np.add(np.multiply(b, amt), np.multiply(a, (1.0 - amt)))


    tree = BVHTree.FromObject(obCaster, context.evaluated_depsgraph_get())
    verts = ob.data.vertices
    def shadow(attrLoop):
        loop = ob.data.loops[attrLoop]
        dir = list(loop.normal)
        dirEul = mathutils.Euler(dir, 'XYZ')
        averageNormal = list(verts[loop.vertex_index].normal)
        pos = list(verts[loop.vertex_index].co)
        offsetNormal = mix(averageNormal, dir, 1.0)
        offset = np.multiply(offsetNormal, 0.001)
        pos = np.add(pos, offset)
        shade = 0.0
        for i in range(200):
            fuzzyEul = mathutils.Euler(fibonacci_spiral_sphere(i, 200), 'XYZ')
            fuzzyQuat = fuzzyEul.to_quaternion()
            dirQuat = dirEul.to_quaternion()
            dirQuat.rotate(fuzzyQuat)
            dirQuat.rotate(fuzzyQuat)
            # finalDir = dirQuat.to_euler('XYZ')
            finalDir = fuzzyEul
            hit, normal, index, distance = tree.ray_cast(pos, finalDir, 1.5)
            if(not hit == None):
                shade += 1.0
            
        light = 1.0 - shade / 200.0
    #    return dir
        return [light, light, light, 1,0]


    # print('vertex color channel: ' + exporterMatNode.name)


    def dataTransferColor(loops, dstName, singleChannel = None):
        dst = ob.data.vertex_colors[dstName]
        
        for l in range(loops):
            cSrc = shadow(l)
    #        cSrc = gammaCorrect(cSrc, 0.4545)
            cDst = dst.data[l].color
            # describeThing(cSrc)
            if(singleChannel == None):
                cDst[0] = cSrc[0]
                cDst[1] = cSrc[1]
                cDst[2] = cSrc[2]
            else:
                fac = coerceFac(cSrc)
                cDst[singleChannel] = fac
                
    if ob.type == 'MESH':
        
        ob.data.calc_normals_split()
        
        #how many loops do we have ?
        loops = len(ob.data.loops)
        # print(str(loops))
    
        #go through each vertex color layer
        # for vcol in ob.data.vertex_colors:
            # print('vertex color channel: ' + vcol.name)
        
        
        dataTransferColor(loops, 'shadows')
    #    dataTransferColor(loops, 'exportChannel1', 'color1RGB')
    #    dataTransferColor(loops, 'exportChannel1', 'color1A', 3)
    #    dataTransferColor(loops, 'exportChannel2', 'color2RGB')
    #    dataTransferColor(loops, 'exportChannel2', 'color2A', 3)




class HORIZON_OT_BakeAmbientOcclusionToVertexColor(Operator):
    bl_idname = "horizon.bake_ambient_occlusion_to_vertex_color"
    bl_label = "Bake AO To Vertex Colors"

    def execute(self, context):
        bakeSelected(context)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(InterfaceBakeAOVars)
    bpy.types.Scene.bake_ao_vars = bpy.props.PointerProperty(type=InterfaceBakeAOVars)
    bpy.utils.register_class(HORIZON_OT_BakeAmbientOcclusionToVertexColor)

def unregister():
    del bpy.types.Scene.bake_ao_vars
    bpy.utils.unregister_class(InterfaceBakeAOVars)
    bpy.utils.unregister_class(HORIZON_OT_BakeAmbientOcclusionToVertexColor)

if __name__ == "__main__":
    register()
