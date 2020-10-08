import sys
import bpy
import numpy as np
from bpy.types import Operator
import traceback
import mathutils

def squashAttributes(context):
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
    baseTree = mat.node_tree
    nodes = baseTree.nodes

    # get the links
    links = baseTree.links

    # get some specific node:
    # returns None if the node does not exist
    exporterMatNode = nodes.get("exporter")
    mixerMatNode = nodes.get("mixer")

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

    def isSameSocket(socket1, socket2):
        return socket1.identifier == socket2.identifier

    def isSameNode(node1, node2):
        return node1.location == node2.location

    def getLinkDetails(link):
        return link.from_node.name + '.' + link.from_socket.identifier + ' -> ' + link.to_node.name + '.' + link.to_socket.identifier

    def getInput(node, identifier):
        input = next((i for i in node.inputs if i.identifier == identifier), None)
        if(input):
            return input
        else:
            err('no input named ' + name)
            
    def getInputLink(tree, node, identifier, failSafe = False):
        link = next((l for l in tree.links if isSameNode(l.to_node, node) and l.to_socket.identifier == identifier), None)
        if(link):
            return link
        elif failSafe:
            return None
        else:
            err('no input link named ' + identifier + ' on ' + node.name)

    def getInputColor(tree, node, identifier, attrLoop):
        link = getInputLink(tree, node, identifier, True)
        
        if(link):
            pr('  link: ' + getLinkDetails(link))

        if(link):
            return coerceColor(resolveAnyNode(tree, link.from_node, link, attrLoop))
        else:
            c = getInput(node, identifier).default_value
            pr('-----' + str(c))
            return gammaCorrect(coerceColor(c), 0.4545)

    def describeInputs(node):
        pr('  ' + node.name + ' inputs:')
        for i in node.inputs:
            pr('    ' + i.name + ' ' + i.bl_idname + ' ' + i.identifier)

    def describeLink(link):
        pr('link: ' + getLinkDetails(link))


    def resolveShaderNodeMixRGB(tree, node, downLink, attrLoop):
        color1 = getInputColor(tree, node, 'Color1', attrLoop)
        color2 = getInputColor(tree, node, 'Color2', attrLoop)
        
        mode = node.blend_type
        link3 = getInputLink(tree, node, 'Fac', True)
        
        if(isinstance(color1, float)):
            color1 = [color1, color1, color1, 1.0]
            
        g = 2.2
        ig = 1.0 / g
        color1 = gammaCorrect(color1, g)
        color2 = gammaCorrect(color2, g)
        
        if(mode == 'ADD'):
            colorFinal = np.add(color1, color2)
            gammaCorrect(colorFinal, ig)
        elif(mode == 'MULTIPLY'):
            colorFinal = np.multiply(color1, color2)
            gammaCorrect(colorFinal, ig)
        elif(mode == 'MIX'):
            colorFinal = gammaCorrect(color2.copy(), 0.5)
        elif(mode == 'LIGHTEN'):
            colorFinal = np.maximum(color1, color2)
        elif(mode == 'DARKEN'):
            colorFinal = np.minimum(color1, color2)
        else:
            pr('/!\ unsupported mix mode: ' + mode + '. returning color1')
            colorFinal = color1
            
        gammaCorrect(color1, ig)
        gammaCorrect(color2, ig)
        if(link3):
            fac = resolveAnyNode(tree, link3.from_node, link3, attrLoop)
            pr('  link3: ' + getLinkDetails(link3))
            pr('  color1: ' + str(color1))
            pr('  colorFinal: ' + str(colorFinal))
            return lerp(color1, colorFinal, fac)
        else:
            return lerp(color1, colorFinal, getInput(node, 'Fac').default_value)



    def resolveShaderNodeRGB(tree, node, downLink, attrLoop):
        color = list(node.outputs[0].default_value)
        color = gammaCorrect(color, 0.4545)
        return color

    def resolveShaderNodeInvert(tree, node, downLink, attrLoop):
        link = getInputLink(tree, node, 'Color')
        colorIn = coerceColor(resolveAnyNode(tree, link.from_node, link, attrLoop))
        gammaCorrect(colorIn, 2.2)
        if(len(colorIn) == 3):
            colorFinal = np.subtract([1.0, 1.0, 1.0], colorIn)
        else:
            colorFinal = np.subtract([1.0, 1.0, 1.0, 1.0], colorIn)
            
        link2 = getInputLink(tree, node, 'Fac', True)
        if(link2):
            fac = resolveAnyNode(tree, link2.from_node, link2, attrLoop)
            return lerp(colorIn, colorFinal, fac)
        else:
            return lerp(colorIn, colorFinal, getInput(node, 'Fac').default_value)

        gammaCorrect(colorFinal, 0.4545)
        return colorFinal


    def resolveShaderNodeMapRange(tree, node, downLink, attrLoop):
        valLink = getInputLink(tree, node, 'Value')
        value = coerceFac(resolveAnyNode(tree, valLink.from_node, valLink, attrLoop))
        value = pow(value, 2.2)
        fromMin = getInput(node, 'From Min').default_value
        fromMax = getInput(node, 'From Max').default_value
        mix = (value - fromMin) / (fromMax - fromMin)
        toMin = getInput(node, 'To Min').default_value
        toMax = getInput(node, 'To Max').default_value
        final = toMin + (toMax - toMin) * mix
        final = pow(final, 0.4545)
        return [final, final, final, 1.0]

    def resolveShaderNodeVectorMath(tree, node, downLink, attrLoop):
        link1 = getInputLink(tree, node, 'Vector')
        link2 = getInputLink(tree, node, 'Vector_001', True)
        
        vec1 = resolveAnyNode(tree, link1.from_node, link1, attrLoop)
        if(link2):
            vec2 = resolveAnyNode(tree, link2.from_node, link2, attrLoop)
        else:
            vec2 = list(getInput(node, 'Vector_001').default_value)
            
        op = node.operation
        
        
        if(op == 'DOT_PRODUCT'):
            val = float(np.dot(vec1, vec2))
            val = max(0.0, val)
            describeThing(val)
            color = [val, val, val, 1.0]
            describeThing(color)
            gammaCorrect(color, 0.4545)
            return color
        elif(op == 'ADD'):
            return np.add(vec1, vec2)
        elif(op == 'SUBTRACT'):
            describeThing(vec1)
            describeThing(vec2)
            final = np.subtract(vec1, vec2)
            describeThing(final)
            return final
        elif(op == 'MULTIPLY'):
            describeThing(vec1)
            describeThing(vec2)
            final = np.multiply(vec1, vec2)
            describeThing(final)
            return final
        else:
            pr('/!\ unsupported node type: ' + op + '. returning white')
            return [1.0, 1.0, 1.0, 1.0]

    def resolveShaderNodeVectorTransform(tree, node, downLink, attrLoop):
        describeInputs(node)
        link = getInputLink(tree, node, 'Vector')
        
        vec = resolveAnyNode(tree, link.from_node, link, attrLoop)
        
        type = node.vector_type
        convertFrom = node.convert_from
        convertTo = node.convert_to
        
        if(type == 'NORMAL'):
            if(convertFrom == 'WORLD' and convertTo == 'OBJECT'):
                mx_inv = ob.matrix_world.inverted()
                mx_norm = mx_inv.transposed().to_3x3()
                normal = mx_norm @ mathutils.Vector(vec[1:4])
                return normal
            else:
                pr('/!\ unsupported NORMAL transform from ' + convertFrom + ' to ' + convertTo + '. returning white')
                return [1.0, 1.0, 1.0, 1.0]
        else:
            pr('/!\ unsupported transform type: ' + type + '. returning white')
            return [1.0, 1.0, 1.0, 1.0]

    def resolveShaderNodeNewGeometry(tree, node, downLink, attrLoop):
        describeInputs(node)
        propName = downLink.from_socket.identifier
        if(propName == 'Normal'):
            loop = ob.data.loops[attrLoop]
            vec = loop.normal
    #        vec = list(vec[:])
    #        vec.append(1.0)
            return vec
        else:
            pr('/!\ unsupported transform type: ' + type + '. returning white')
            return [1.0, 1.0, 1.0, 1.0]

    def resolveShaderNodeAttribute(tree, node, downLink, attrLoop):
        color = ob.data.vertex_colors[node.attribute_name].data[attrLoop].color
        color = list(color) #copy, do not modify color in-place
    #    gammaCorrect(color, 0.4545)
        return color

    def resolveNodeReroute(tree, node, downLink, attrLoop):
        link = getInputLink(tree, node, 'input.001', True)
        if(link):
            return resolveAnyNode(tree, link.from_node, link, attrLoop)
        link = getInputLink(tree, node, 'input')
        if(link):
            return resolveAnyNode(tree, link.from_node, link, attrLoop)

    def resolveShaderNodeUVMap(tree, node, downLink, attrLoop):
        uv = ob.data.uv_layers[node.uv_map].data[attrLoop].uv
        uv = list(uv)
        uv.append(0.0)
        return uv

    def resolveShaderNodeSeparateRGB(tree, node, downLink, attrLoop):
        channel = downLink.from_socket.identifier
        c = getInputColor(tree, node, 'Image', attrLoop)

        if(channel == 'R'):
            v = c[0]
        elif(channel == 'G'):
            v = c[1]
        elif(channel == 'B'):
            v = c[2]
        else:
            v = 1.0
        return [v, v, v, 1.0]

    def resolveShaderNodeCombineRGB(tree, node, downLink, attrLoop):
        r = coerceFac(getInputColor(tree, node, 'R', attrLoop))
        g = coerceFac(getInputColor(tree, node, 'G', attrLoop))
        b = coerceFac(getInputColor(tree, node, 'B', attrLoop))
        return [r, g, b, 1.0]

    def resolveShaderNodeGamma(tree, node, downLink, attrLoop):
        color = getInputColor(tree, node, 'Color', attrLoop)
        gamma = coerceFac(getInputColor(tree, node, 'Gamma', attrLoop))
        gamma = pow(gamma, 2.2)
        gammaCorrect(color, gamma)
        return color

    def resolveShaderNodeMath(tree, node, downLink, attrLoop):
        val1 = coerceFac(getInputColor(tree, node, 'Value', attrLoop))
        val2 = coerceFac(getInputColor(tree, node, 'Value_001', attrLoop))
        val1 = pow(val1, 2.2)
        val2 = pow(val2, 2.2)
        op = node.operation
            
        if(op == 'ADD'):
            valFinal = val1 + val2
        elif(op == 'SUBTRACT'):
            valFinal = val1 - val2
        elif(op == 'MULTIPLY'):
            valFinal = val1 * val2
        elif(op == 'MAXIMUM'):
            valFinal = max(val1, val2)
        elif(op == 'MINIMUM'):
            valFinal = min(val1, val2)
        elif(op == 'GREATER_THAN'):
            if(val1 > val2):
                valFinal = 1.0
            else:
                valFinal = 0.0
        else:
            pr('/!\ unsupported operation: ' + op + '. returning va11')
            valFinal = val1
            
        valFinal = pow(valFinal, 0.4545)

        return valFinal


    def resolveShaderNodeClamp(tree, node, downLink, attrLoop):
        valLink = getInputLink(tree, node, 'Value')
        value = coerceFac(resolveAnyNode(tree, valLink.from_node, valLink, attrLoop))
        minVal = getInput(node, 'Min').default_value
        maxVal = getInput(node, 'Max').default_value
        return min(maxVal, max(minVal, value))


    def resolveShaderNodeGroup(tree, node, downLink, attrLoop):
        gNodes = node.node_tree.nodes
        outNode = gNodes.get("Group Output")
        describeInputs(outNode)
        describeThing(outNode)
        describeLink(downLink)
        c = solveInput(node.node_tree, getInput(outNode, downLink.from_socket.identifier), outNode, attrLoop)
        return c


    def resolveAnyNode(tree, node, link, attrLoop):
        pr('resolving ' + node.name + ' <' + node.bl_idname + '> (' + link.from_socket.identifier + ')' )
        describeInputs(node)
        nodeType = node.bl_idname
        
        if(nodeType == 'ShaderNodeMixRGB'):
            return resolveShaderNodeMixRGB(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeRGB'):
            return resolveShaderNodeRGB(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeInvert'):
            return resolveShaderNodeInvert(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeMapRange'):
            return resolveShaderNodeMapRange(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeVectorMath'):
            return resolveShaderNodeVectorMath(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeVectorTransform'):
            return resolveShaderNodeVectorTransform(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeNewGeometry'):
            return resolveShaderNodeNewGeometry(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeAttribute'):
            return resolveShaderNodeAttribute(tree, node, link, attrLoop)
        elif(nodeType == 'NodeReroute'):
            return resolveNodeReroute(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeUVMap'):
            return resolveShaderNodeUVMap(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeCombineRGB'):
            return resolveShaderNodeCombineRGB(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeSeparateRGB'):
            return resolveShaderNodeSeparateRGB(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeGamma'):
            return resolveShaderNodeGamma(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeMath'):
            return resolveShaderNodeMath(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeClamp'):
            return resolveShaderNodeClamp(tree, node, link, attrLoop)
        elif(nodeType == 'ShaderNodeGroup'):
            return resolveShaderNodeGroup(tree, node, link, attrLoop)
        else:
            pr('/!\ unsupported node type: ' + nodeType + '. returning white')
            return [1.0, 1.0, 1.0, 1.0]


    def solveInput(tree, input, node, attrLoop):
        try:
            pr('input: ' + input.name)
            link = next((l for l in tree.links if isSameNode(l.to_node, node) and isSameSocket(l.to_socket, input)), None)
            if(link):
                pr('output: ' + link.from_node.name)
                return coerceColor(resolveAnyNode(tree, link.from_node, link, attrLoop))
            else:
                err('no link found on ' + input.name)
                # return input.default_value
        except Exception as e: 
            traceback.print_exc()
            # print(e)
            # print("/!\ Unexpected error:")
            # print(str(sys.exc_info()[0]))
            # print(str(sys.exc_info()[1]))
            # print(str(sys.exc_info()[2]))
            raise

    #    return link.from_node

    def testChannel(matNode, name):
        link = getInputLink(baseTree, matNode, name, True)
        if(link):
            color = resolveAnyNode(baseTree, link.from_node, link, 0)
            print(name + ': ' + str(color))
        else:
            print(name + ': no link')
            

    if(exporterMatNode):
        testChannel(exporterMatNode, 'color1RGB')
        # testChannel(exporterMatNode, 'color1A')
        # testChannel(exporterMatNode, 'color2RGB')
        # testChannel(exporterMatNode, 'color2A')
        # testChannel(exporterMatNode, 'uv1')
        # testChannel(exporterMatNode, 'uv2')

    if(mixerMatNode):
        testChannel(mixerMatNode, 'color1RGB')
        # testChannel(mixerMatNode, 'color1A')


    test = 0.5
    test2 = 0.5 ** 0.5
    pr('test:' + str(test2))

    print('vertex color channel: ' + exporterMatNode.name)


    def dataTransferColor(matNode, loops, dstName, srcName, singleChannel = None):
        input = getInputLink(baseTree, matNode, srcName, True)
        if(input):
            dst = ob.data.vertex_colors[dstName]
            for l in range(loops):
                cSrc = solveInput(baseTree, getInput(matNode, srcName), matNode, l)
        #        cSrc = gammaCorrect(cSrc, 0.4545)
                cDst = dst.data[l].color
                describeThing(cSrc)
                if(singleChannel == None):
                    cDst[0] = cSrc[0]
                    cDst[1] = cSrc[1]
                    cDst[2] = cSrc[2]
                else:
                    fac = coerceFac(cSrc)
                    cDst[singleChannel] = fac
                
    def dataTransferUv(matNode, loops, dstName, srcName, singleChannel = None):
        input = getInputLink(baseTree, matNode, srcName, True)
        if(input):
            dst = ob.data.uv_layers[dstName]
            for l in range(loops):
                cSrc = solveInput(baseTree, getInput(matNode, srcName), matNode, l)
        #        cSrc = gammaCorrect(cSrc, 0.4545)
                cDst = dst.data[l].uv
                describeThing(cSrc)
                if(singleChannel == None):
                    cDst[0] = cSrc[0]
                    cDst[1] = cSrc[1]
                else:
                    fac = coerceFac(cSrc)
                    cDst[singleChannel] = fac
                


    #vertex colors are in fact stored per loop-vertex -&gt; MeshLoopColorLayer
    if ob.type == 'MESH':
        
        #how many loops do we have ?
        loops = len(ob.data.loops)
        print(str(loops))
    
        #go through each vertex color layer
        for vcol in ob.data.vertex_colors:
            print('vertex color channel: ' + vcol.name)
        
        if(exporterMatNode):
            print('exporter material node')
            verbose = False
            dataTransferColor(exporterMatNode, loops, 'exportChannel1', 'color1RGB')
            dataTransferColor(exporterMatNode, loops, 'exportChannel1', 'color1A', 3)
            dataTransferColor(exporterMatNode, loops, 'exportChannel2', 'color2RGB')
            dataTransferColor(exporterMatNode, loops, 'exportChannel2', 'color2A', 3)
            dataTransferUv(exporterMatNode, loops, 'exportUV1', 'uv1')
            dataTransferUv(exporterMatNode, loops, 'exportUV2', 'uv2')
            verbose = True
        if(mixerMatNode):
            print('mixer material node')
            verbose = False
            vertexColorDstName = getInput(mixerMatNode, 'vertexColorDstName').default_value
            dataTransferColor(mixerMatNode, loops, vertexColorDstName, 'color1RGB')
            dataTransferColor(mixerMatNode, loops, vertexColorDstName, 'color1A', 3)
            verbose = True




class HORIZON_OT_SquashAttributes(Operator):
    bl_idname = "horizon.squash_attributes"
    bl_label = "Squash Attributes"

    def execute(self, context):
        squashAttributes(context)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(HORIZON_OT_SquashAttributes)

def unregister():
    bpy.utils.unregister_class(HORIZON_OT_SquashAttributes)

if __name__ == "__main__":
    register()
