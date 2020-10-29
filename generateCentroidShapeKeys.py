import bpy, bmesh
import math
import sys
import numpy as np
import traceback
import mathutils
from mathutils.bvhtree import BVHTree
from collections import defaultdict
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


def generateCentroidShapeKeys(context):
    previousAreaType = context.area.type
    context.area.type = 'VIEW_3D'

    # Assuming our object is active and in edit mode
    ob = context.object
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh( ob.data )

    islands = []
    visitedVertIndices = set([])

    verts = ob.data.vertices

    if not ob.data.shape_keys:
        ob.shape_key_add(name='Basis')

    def getCentroid(vertIndices):
        cursor = mathutils.Vector((0.0, 0.0, 0.0))
        for index in vertIndices:
            cursor += verts[index].co
        cursor /= len(vertIndices)
        return cursor


    def getPivot(centroid):
        cursor = mathutils.Vector(centroid)
    #    a = math.atan2(cursor.z, cursor.x)
    #    d = math.sqrt(cursor.x*cursor.x+cursor.z*cursor.z) * 0.33
    #    cursor.z = math.sin(a) * d
    #    cursor.x = math.cos(a) * d
        cursor *= 0.33
        return cursor

    def getBounds(vertIndices):
        v = verts[list(vertIndices)[0]].co
        vMin = mathutils.Vector((v.x, v.y, v.z))
        vMax = mathutils.Vector((v.x, v.y, v.z))
        for index in vertIndices:
            v = verts[index].co
            vMin.x = min(vMin.x, v.x)
            vMin.y = min(vMin.y, v.y)
            vMin.z = min(vMin.z, v.z)
            vMax.x = max(vMax.x, v.x)
            vMax.y = max(vMax.y, v.y)
            vMax.z = max(vMax.z, v.z)
        cursor = vMax - vMin
        return cursor

    def getBoundSize(bounds):
        return bounds.x + bounds.y + bounds.z

    def crawlVerts(vert, islandIndices):
        if vert.index in visitedVertIndices:
            return
        visitedVertIndices.add(vert.index)
        islandIndices.add(vert.index)
        for edge in vert.link_edges:
            crawlVerts(edge.verts[0], islandIndices)
            crawlVerts(edge.verts[1], islandIndices)
            
    for v in bm.verts:
        if v.index not in visitedVertIndices:
            island = set([])
            islands.append(island)
            crawlVerts(v, island)

    print('verts: ' + str(len(bm.verts)))
    print('islands: ' + str(len(islands)))

    bpy.ops.object.mode_set(mode='OBJECT')

    centroids = list(map(getCentroid, islands))
    pivots = list(map(getPivot, centroids))
    bounds = list(map(getBounds, islands))
    boundSizes = list(map(getBoundSize, bounds))
    #for v in islands[0]:
    #    pr(v)

    polygons = ob.data.polygons

    #describeThing(centroids[0])

    vertex_map = defaultdict(list)

    for poly in polygons:
        for v_ix, l_ix in zip(poly.vertices, poly.loop_indices):
            vertex_map[v_ix].append(l_ix)

    def indexOfIslandWithvertIndex(index):
        for i, s in enumerate(islands):
            if index in s:
                return i
        return -1

    loops = len(ob.data.loops)
    #dst = ob.data.vertex_colors['centroids']
    #for v_ix, l_ixs in vertex_map.items():
    #    cSrc = centroids[indexOfIslandWithvertIndex(v_ix)]
    #    for l_ix in l_ixs:
    #        cDst = dst.data[l_ix].color
    #        cDst[0] = cSrc[0]
    #        cDst[1] = cSrc[1]
    #        cDst[2] = cSrc[2]
    #        

    if 'centroids' not in ob.data.shape_keys.key_blocks:
        ob.shape_key_add(name='centroids')

    shape = next(s for s in ob.data.shape_keys.key_blocks if s.name == 'centroids')

    for vi in range(len(ob.data.vertices)):
        vd = shape.data[vi]
        vs = centroids[indexOfIslandWithvertIndex(vi)]
        # vs2 = ob.data.vertices[vi].co
        vd.co.x = vs.x # + vs2.x
        vd.co.y = vs.y # + vs2.y
        vd.co.z = vs.z # + vs2.z

    if 'relpos' not in ob.data.shape_keys.key_blocks:
        ob.shape_key_add(name='relpos')

    shape = next(s for s in ob.data.shape_keys.key_blocks if s.name == 'relpos')

    for vi in range(len(ob.data.vertices)):
        vd = shape.data[vi]
        vsCent = pivots[indexOfIslandWithvertIndex(vi)]
        # vs2 = ob.data.vertices[vi].co
        vd.co.x = vsCent.x # - vs2.x
        vd.co.y = vsCent.y # - vs2.y
        vd.co.z = vsCent.z # - vs2.z

    if 'timeData' not in ob.data.shape_keys.key_blocks:
        ob.shape_key_add(name='timeData')

    shape = next(s for s in ob.data.shape_keys.key_blocks if s.name == 'timeData')

    smallest = 10000.0
    biggest = 0.0
    for bs in boundSizes:
        smallest = min(smallest, bs)
        biggest = max(biggest, bs)

    sizeRange = biggest - smallest
        
    for vi in range(len(ob.data.vertices)):
        vd = shape.data[vi]
        vsBounds = bounds[indexOfIslandWithvertIndex(vi)]
        boundSize = boundSizes[indexOfIslandWithvertIndex(vi)]
        vs2 = ob.data.vertices[vi].co
        pivot = pivots[indexOfIslandWithvertIndex(vi)]
        # rigid
        sizeInfluence = (boundSize - smallest) / sizeRange
        distToCenterInfluence =  - (pivot.length * 8.0) + 0.5
        vd.co.x = (sizeInfluence * 0.0) + (distToCenterInfluence * 0.25) + vs2.x
        # soft
        # vd.co.x = ((boundSize - smallest) / sizeRange - (pivot.length * 16.0) + 0.5 + vs2.x + ((pivot - vs2).length * -5.0)) * 0.25 + 1.6
        
    # if bpy.context.object.data.use_auto_smooth:
    #     bpy.context.object.data.use_auto_smooth = False

    context.area.type = previousAreaType

    #describeThing(ob.data.vertices[0].co)


class HORIZON_OT_GenerateCentroidShapeKeys(Operator):
    bl_idname = "horizon.generate_centroid_shape_keys"
    bl_label = "Generate Centroid Shape Keys"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        generateCentroidShapeKeys(context)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(HORIZON_OT_GenerateCentroidShapeKeys)

def unregister():
    bpy.utils.unregister_class(HORIZON_OT_GenerateCentroidShapeKeys)

if __name__ == "__main__":
    register()
