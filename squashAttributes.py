import sys
import bpy
import numpy as np
from bpy.types import Operator
import traceback
import mathutils
import time

def clamp(value, minVal, maxVal):
    return min(maxVal, max(minVal, value))

def squashAttributes(context):
    def print(data):
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == 'CONSOLE':
                    override = {'window': window, 'screen': screen, 'area': area}
                    bpy.ops.console.scrollback_append(override, text=str(data), type="OUTPUT")

    ob = bpy.context.active_object

    timeStart = time.time()

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

    def getInputColor(tree, node, identifier):
        link = getInputLink(tree, node, identifier, True)
        
        if(link):
            pr('  link: ' + getLinkDetails(link))

        if(link):
            resolveAnyNodeForLoop = resolveAnyNode(tree, link.from_node, link)
            def getInputColorForLoop(attrLoop):
                return coerceColor(resolveAnyNodeForLoop(attrLoop))
            return getInputColorForLoop
        else:
            c = getInput(node, identifier).default_value
            pr('-----' + str(c))
            c = gammaCorrect(coerceColor(c), 0.4545)
            return lambda _: list(c)

    def getInputValue(tree, node, identifier):
        link = getInputLink(tree, node, identifier, True)
        
        if(link):
            pr('  link: ' + getLinkDetails(link))

        if(link):
            resolveAnyNodeForLoop = resolveAnyNode(tree, link.from_node, link)
            def getInputColorForLoop(attrLoop):
                return coerceColor(resolveAnyNodeForLoop(attrLoop))
            return getInputColorForLoop
        else:
            c = getInput(node, identifier).default_value
            pr('-----' + str(c))
            c = coerceColor(c)
            return lambda _: list(c)

    def describeInputs(node):
        pr('  ' + node.name + ' inputs:')
        for i in node.inputs:
            pr('    ' + i.name + ' ' + i.bl_idname + ' ' + i.identifier)

    def describeLink(link):
        pr('link: ' + getLinkDetails(link))


    def resolveShaderNodeMixRGB(tree, node, downLink):
        g = 2.2
        ig = 1.0 / g
        mode = node.blend_type
        link3 = getInputLink(tree, node, 'Fac', True)
        if(link3):
            facForLoop = resolveAnyNode(tree, link3.from_node, link3)
        else:
            facDefault = getInput(node, 'Fac').default_value
            facForLoop = lambda _: facDefault
        getInputColor1ForLoop = getInputColor(tree, node, 'Color1')
        getInputColor2ForLoop = getInputColor(tree, node, 'Color2')

        if(mode == 'ADD'):
            op = lambda color1, color2: gammaCorrect(np.add(color1, color2), ig)
        elif(mode == 'MULTIPLY'):
            op = lambda color1, color2: gammaCorrect(np.multiply(color1, color2), ig)
        elif(mode == 'DIVIDE'):
            op = lambda color1, color2: gammaCorrect(np.divide(color1, color2), ig)
        elif(mode == 'MIX'):
            op = lambda color1, color2: gammaCorrect(color2.copy(), 0.5)
        elif(mode == 'LIGHTEN'):
            op = lambda color1, color2: np.maximum(color1, color2)
        elif(mode == 'DARKEN'):
            op = lambda color1, color2: np.minimum(color1, color2)
        else:
            op = lambda color1, color2: color1
            pr('/!\ unsupported mix mode: ' + mode + '. returning color1')

        def resolveShaderNodeMixRGBForLoop(attrLoop):
            color1 = getInputColor1ForLoop(attrLoop)
            color2 = getInputColor2ForLoop(attrLoop)
            
            if(isinstance(color1, float)):
                color1 = [color1, color1, color1, 1.0]
                
            color1 = gammaCorrect(color1, g)
            color2 = gammaCorrect(color2, g)
            colorFinal = op(color1, color2)

            gammaCorrect(color1, ig)
            gammaCorrect(color2, ig)

            fac = facForLoop(attrLoop)
            # pr('  link3: ' + getLinkDetails(link3))
            pr('  color1: ' + str(color1))
            pr('  colorFinal: ' + str(colorFinal))
            return lerp(color1, colorFinal, fac)
        return resolveShaderNodeMixRGBForLoop



    def resolveShaderNodeRGB(tree, node, downLink):
        color = list(node.outputs[0].default_value)
        color = gammaCorrect(color, 0.4545)
        return lambda _: color

    def resolveShaderNodeInvert(tree, node, downLink):
        link = getInputLink(tree, node, 'Color')
        resolveAnyNodeForLoop = resolveAnyNode(tree, link.from_node, link)
        link2 = getInputLink(tree, node, 'Fac', True)
        if(link2):
            facForLoop = resolveAnyNode(tree, link2.from_node, link2)
        else:
            facDefault = getInput(node, 'Fac').default_value
            facForLoop = lambda _: facDefault

        def resolveShaderNodeInvertForLoop(attrLoop):
            colorIn = coerceColor(resolveAnyNodeForLoop(attrLoop))
            gammaCorrect(colorIn, 2.2)
            if(len(colorIn) == 3):
                colorFinal = np.subtract([1.0, 1.0, 1.0], colorIn)
            else:
                colorFinal = np.subtract([1.0, 1.0, 1.0, 1.0], colorIn)
                
            fac = facForLoop(attrLoop)
            return lerp(colorIn, colorFinal, fac)

            gammaCorrect(colorFinal, 0.4545)
            return colorFinal
        return resolveShaderNodeInvertForLoop


    def resolveShaderNodeMapRange(tree, node, downLink):
        valLink = getInputLink(tree, node, 'Value')
        resolveAnyNodeForLoop = resolveAnyNode(tree, valLink.from_node, valLink)
        fromMin = getInput(node, 'From Min').default_value
        fromMax = getInput(node, 'From Max').default_value
        toMin = getInput(node, 'To Min').default_value
        toMax = getInput(node, 'To Max').default_value
        def resolveShaderNodeMapRangeForLoop(attrLoop):
            value = clamp(coerceFac(resolveAnyNodeForLoop(attrLoop)), 0.0, 1.0)
            value = pow(value, 2.2)
            mix = (value - fromMin) / (fromMax - fromMin)
            final = toMin + (toMax - toMin) * mix
            final = pow(final, 0.4545)
            return [final, final, final, 1.0]
        return resolveShaderNodeMapRangeForLoop

    def resolveShaderNodeVectorMath(tree, node, downLink):
        link1 = getInputLink(tree, node, 'Vector')
        link2 = getInputLink(tree, node, 'Vector_001', True)
        resolveAnyNodeForLoop1 = resolveAnyNode(tree, link1.from_node, link1)
        if(link2):
            getInput2Value = resolveAnyNode(tree, link2.from_node, link2)
        else:
            defaultValue = list(getInput(node, 'Vector_001').default_value)
            def getInput2Value(attrLoop):
                return defaultValue

        op = node.operation
        if(op == 'DOT_PRODUCT'):
            def resolveShaderNodeVectorDotProductForLoop(attrLoop):
                vec1 = resolveAnyNodeForLoop1(attrLoop)
                vec2 = getInput2Value(attrLoop)
                val = float(np.dot(vec1, vec2))
                val = max(0.0, val)
                # describeThing(val)
                color = [val, val, val, 1.0]
                # describeThing(color)
                gammaCorrect(color, 0.4545)
                return color
            return resolveShaderNodeVectorDotProductForLoop
        elif(op == 'ADD'):
            def resolveShaderNodeVectorAddForLoop(attrLoop):
                vec1 = resolveAnyNodeForLoop1(attrLoop)
                vec2 = getInput2Value(attrLoop)
                return np.add(vec1, vec2)
            return resolveShaderNodeVectorAddForLoop
        elif(op == 'SUBTRACT'):
            def resolveShaderNodeVectorSubtractForLoop(attrLoop):
                vec1 = resolveAnyNodeForLoop1(attrLoop)
                vec2 = getInput2Value(attrLoop)
                # describeThing(vec1)
                # describeThing(vec2)
                final = np.subtract(vec1, vec2)
                # describeThing(final)
                return final
            return resolveShaderNodeVectorSubtractForLoop
        elif(op == 'MULTIPLY'):
            def resolveShaderNodeVectorMultiplyForLoop(attrLoop):
                vec1 = resolveAnyNodeForLoop1(attrLoop)
                vec2 = getInput2Value(attrLoop)
                # describeThing(vec1)
                # describeThing(vec2)
                final = np.multiply(vec1, vec2)
                # describeThing(final)
                return final
            return resolveShaderNodeVectorMultiplyForLoop
        elif(op == 'ABSOLUTE'):
            def resolveShaderNodeVectorAbsoluteForLoop(attrLoop):
                vec1 = resolveAnyNodeForLoop1(attrLoop)
                # describeThing(vec1)
                # describeThing(vec2)
                final = np.absolute(vec1)
                # describeThing(final)
                return final
            return resolveShaderNodeVectorAbsoluteForLoop
        else:
            pr('/!\ unsupported node type: ' + op + '. returning white')
            return lambda _: [1.0, 1.0, 1.0, 1.0]

    def resolveShaderNodeVectorTransform(tree, node, downLink):
        describeInputs(node)
        link = getInputLink(tree, node, 'Vector')
        
        type = node.vector_type
        convertFrom = node.convert_from
        convertTo = node.convert_to
        
        if(type == 'NORMAL'):
            if(convertFrom == 'WORLD' and convertTo == 'OBJECT'):
                mx_inv = ob.matrix_world.inverted()
                mx_norm = mx_inv.transposed().to_3x3()
                resolveAnyNodeForLoop = resolveAnyNode(tree, link.from_node, link)
                def resolveShaderNodeVectorTransformForLoop(attrLoop):
                    vec = resolveAnyNodeForLoop(attrLoop)
                    normal = mx_norm @ mathutils.Vector(vec[1:4])
                    return normal
                return resolveShaderNodeVectorTransformForLoop
            else:
                pr('/!\ unsupported NORMAL transform from ' + convertFrom + ' to ' + convertTo + '. returning white')
                return lambda _: [1.0, 1.0, 1.0, 1.0]
        else:
            pr('/!\ unsupported transform type: ' + type + '. returning white')
            return lambda _: [1.0, 1.0, 1.0, 1.0]

    def resolveShaderNodeGeometry(tree, node, downLink):
        describeInputs(node)
        propName = downLink.from_socket.identifier
        if(propName == 'Normal'):
            def resolveShaderNodeGeometryForLoop(attrLoop):
                loop = ob.data.loops[attrLoop]
                vec = loop.normal
        #        vec = list(vec[:])
        #        vec.append(1.0)
                return vec
            return resolveShaderNodeGeometryForLoop
        elif(propName == 'Position'):
            def resolveShaderNodeGeometryForLoop(attrLoop):
                loop = ob.data.loops[attrLoop]
                vecIndex = loop.vertex_index
                vec = ob.data.vertices[vecIndex].co
        #        vec = list(vec[:])
        #        vec.append(1.0)
                return vec
            return resolveShaderNodeGeometryForLoop
        else:
            pr('/!\ unsupported transform type: ' + propName + '. returning magenta')
            return lambda _: [1.0, 0.0, 1.0, 1.0]

    def resolveShaderNodeAttribute(tree, node, downLink):
        data = ob.data.vertex_colors[node.attribute_name].data
        def resolveShaderNodeAttributeForLoop(attrLoop):
            color = data[attrLoop].color
            color = list(color) #copy, do not modify color in-place
        #    gammaCorrect(color, 0.4545)
            return color
        return resolveShaderNodeAttributeForLoop

    def resolveNodeReroute(tree, node, downLink):
        link = getInputLink(tree, node, 'input.001', True)
        if(link):
            return resolveAnyNode(tree, link.from_node, link)
        link = getInputLink(tree, node, 'input')
        if(link):
            return resolveAnyNode(tree, link.from_node, link)

    def resolveShaderNodeUVMap(tree, node, downLink):
        data = ob.data.uv_layers[node.uv_map].data
        def resolveShaderNodeUVMapForLoop(attrLoop):
            uv = data[attrLoop].uv
            uv = list(uv)
            uv.append(0.0)
            uv.append(0.0)
            return uv
        return resolveShaderNodeUVMapForLoop

    def resolveShaderNodeSeparateRGB(tree, node, downLink):
        channel = downLink.from_socket.identifier
        if(channel == 'R'):
            getInputImageForLoop = getInputColor(tree, node, 'Image')
            def resolveShaderNodeSeparateR(attrLoop):
                c = getInputImageForLoop(attrLoop)
                return [c[0], c[0], c[0], 1.0]
            return resolveShaderNodeSeparateR
        elif(channel == 'G'):
            getInputImageForLoop = getInputColor(tree, node, 'Image')
            def resolveShaderNodeSeparateG(attrLoop):
                c = getInputImageForLoop(attrLoop)
                return [c[1], c[1], c[1], 1.0]
            return resolveShaderNodeSeparateG
        elif(channel == 'B'):
            getInputImageForLoop = getInputColor(tree, node, 'Image')
            def resolveShaderNodeSeparateB(attrLoop):
                c = getInputImageForLoop(attrLoop)
                return [c[2], c[2], c[2], 1.0]
            return resolveShaderNodeSeparateB
        else:
            return lambda _: [1.0, 1.0, 1.0, 1.0]

    def resolveShaderNodeCombineRGB(tree, node, downLink):
        getInputRForLoop = getInputColor(tree, node, 'R')
        getInputGForLoop = getInputColor(tree, node, 'G')
        getInputBForLoop = getInputColor(tree, node, 'B')
        def resolveShaderNodeCombineRGBForLoop(attrLoop):
            r = coerceFac(getInputRForLoop(attrLoop))
            g = coerceFac(getInputGForLoop(attrLoop))
            b = coerceFac(getInputBForLoop(attrLoop))
            return [r, g, b, 1.0]
        return resolveShaderNodeCombineRGBForLoop

    def resolveShaderNodeSeparateXYZ(tree, node, downLink):
        channel = downLink.from_socket.identifier
        if(channel == 'X'):
            getInputImageForLoop = getInputValue(tree, node, 'Vector')
            def resolveShaderNodeSeparateX(attrLoop):
                c = getInputImageForLoop(attrLoop)
                return [c[0], c[0], c[0], 1.0]
            return resolveShaderNodeSeparateX
        elif(channel == 'Y'):
            getInputImageForLoop = getInputValue(tree, node, 'Vector')
            def resolveShaderNodeSeparateY(attrLoop):
                c = getInputImageForLoop(attrLoop)
                return [c[1], c[1], c[1], 1.0]
            return resolveShaderNodeSeparateY
        elif(channel == 'Z'):
            getInputImageForLoop = getInputValue(tree, node, 'Vector')
            def resolveShaderNodeSeparateZ(attrLoop):
                c = getInputImageForLoop(attrLoop)
                return [c[2], c[2], c[2], 1.0]
            return resolveShaderNodeSeparateZ
        else:
            return lambda _: [1.0, 0.0, 1.0, 1.0]

    def resolveShaderNodeGamma(tree, node, downLink):
        getInputColorForLoop = getInputColor(tree, node, 'Color')
        getInputGammaForLoop = getInputColor(tree, node, 'Gamma')
        def resolveShaderNodeGammaForLoop(attrLoop):
            color = getInputColorForLoop(attrLoop)
            gamma = coerceFac(getInputGammaForLoop(attrLoop))
            gamma = pow(gamma, 2.2)
            gammaCorrect(color, gamma)
            return color
        return resolveShaderNodeGammaForLoop

    def resolveShaderNodeMath(tree, node, downLink):
        op = node.operation
        getInputValueForLoop = getInputColor(tree, node, 'Value')
        if(op == 'ADD'):
            getInputValue_001ForLoop = getInputColor(tree, node, 'Value_001')
            def resolveShaderNodeAddForLoop(attrLoop):
                val1 = coerceFac(getInputValueForLoop(attrLoop))
                val2 = coerceFac(getInputValue_001ForLoop(attrLoop))
                val1 = pow(val1, 2.2)
                val2 = pow(val2, 2.2)
                valFinal = val1 + val2
                valFinal = pow(valFinal, 0.4545)
                return valFinal
            return resolveShaderNodeAddForLoop
        elif(op == 'SUBTRACT'):
            getInputValue_001ForLoop = getInputColor(tree, node, 'Value_001')
            def resolveShaderNodeSubtractForLoop(attrLoop):
                val1 = coerceFac(getInputValueForLoop(attrLoop))
                val2 = coerceFac(getInputValue_001ForLoop(attrLoop))
                val1 = pow(val1, 2.2)
                val2 = pow(val2, 2.2)
                valFinal = val1 - val2
                valFinal = pow(valFinal, 0.4545)
                return valFinal
            return resolveShaderNodeSubtractForLoop
        elif(op == 'MULTIPLY'):
            getInputValue_001ForLoop = getInputColor(tree, node, 'Value_001')
            def resolveShaderNodeMultiplyForLoop(attrLoop):
                val1 = coerceFac(getInputValueForLoop(attrLoop))
                val2 = coerceFac(getInputValue_001ForLoop(attrLoop))
                val1 = pow(val1, 2.2)
                val2 = pow(val2, 2.2)
                valFinal = val1 * val2
                valFinal = pow(valFinal, 0.4545)
                return valFinal
            return resolveShaderNodeMultiplyForLoop
        elif(op == 'MAXIMUM'):
            getInputValue_001ForLoop = getInputColor(tree, node, 'Value_001')
            def resolveShaderNodeMaximumForLoop(attrLoop):
                val1 = coerceFac(getInputValueForLoop(attrLoop))
                val2 = coerceFac(getInputValue_001ForLoop(attrLoop))
                val1 = pow(val1, 2.2)
                val2 = pow(val2, 2.2)
                valFinal = max(val1, val2)
                valFinal = pow(valFinal, 0.4545)
                return valFinal
            return resolveShaderNodeMaximumForLoop
        elif(op == 'MINIMUM'):
            getInputValue_001ForLoop = getInputColor(tree, node, 'Value_001')
            def resolveShaderNodeMinimumForLoop(attrLoop):
                val1 = coerceFac(getInputValueForLoop(attrLoop))
                val2 = coerceFac(getInputValue_001ForLoop(attrLoop))
                val1 = pow(val1, 2.2)
                val2 = pow(val2, 2.2)
                valFinal = min(val1, val2)
                valFinal = pow(valFinal, 0.4545)
                return valFinal
            return resolveShaderNodeMinimumForLoop
        elif(op == 'GREATER_THAN'):
            getInputValue_001ForLoop = getInputColor(tree, node, 'Value_001')
            def resolveShaderNodeGreaterThanForLoop(attrLoop):
                val1 = coerceFac(getInputValueForLoop(attrLoop))
                val2 = coerceFac(getInputValue_001ForLoop(attrLoop))
                val1 = pow(val1, 2.2)
                val2 = pow(val2, 2.2)
                if(val1 > val2):
                    valFinal = 1.0
                else:
                    valFinal = 0.0
                valFinal = pow(valFinal, 0.4545)
                return valFinal
            return resolveShaderNodeGreaterThanForLoop
        else:
            pr('/!\ unsupported operation: ' + op + '. returning va11')
            def resolveShaderNodeUnsupportedForLoop(attrLoop):
                val1 = coerceFac(getInputValueForLoop(attrLoop))
                val1 = pow(val1, 2.2)
                valFinal = val1
                valFinal = pow(valFinal, 0.4545)
                return valFinal
            return resolveShaderNodeUnsupportedForLoop


    def resolveShaderNodeClamp(tree, node, downLink):
        valLink = getInputLink(tree, node, 'Value')
        resolveAnyNodeForLoop = resolveAnyNode(tree, valLink.from_node, valLink)
        minVal = getInput(node, 'Min').default_value
        maxVal = getInput(node, 'Max').default_value
        def resolveShaderNodeClampForLoop(attrLoop):
            value = coerceFac(resolveAnyNodeForLoop(attrLoop))
            return min(maxVal, max(minVal, value))
        return resolveShaderNodeClampForLoop

    def resolveShaderNodeValue(tree, node, downLink):
        describeThing(node)
        value = getInput(node, 'Value').default_value
        return lambda _: list(value)


    def resolveShaderNodeGroup(tree, node, downLink):
        gNodes = node.node_tree.nodes
        outNode = gNodes.get("Group Output")
        describeInputs(outNode)
        describeThing(outNode)
        describeLink(downLink)
        return solveInput(node.node_tree, getInput(outNode, downLink.from_socket.identifier), outNode)


    def resolveAnyNode(tree, node, link):
        pr('resolving ' + node.name + ' <' + node.bl_idname + '> (' + link.from_socket.identifier + ')' )
        describeInputs(node)
        nodeType = node.bl_idname
        
        if(nodeType == 'ShaderNodeMixRGB'):
            return resolveShaderNodeMixRGB(tree, node, link)
        elif(nodeType == 'ShaderNodeRGB'):
            return resolveShaderNodeRGB(tree, node, link)
        elif(nodeType == 'ShaderNodeInvert'):
            return resolveShaderNodeInvert(tree, node, link)
        elif(nodeType == 'ShaderNodeMapRange'):
            return resolveShaderNodeMapRange(tree, node, link)
        elif(nodeType == 'ShaderNodeVectorMath'):
            return resolveShaderNodeVectorMath(tree, node, link)
        elif(nodeType == 'ShaderNodeVectorTransform'):
            return resolveShaderNodeVectorTransform(tree, node, link)
        elif(nodeType == 'ShaderNodeNewGeometry'):
            return resolveShaderNodeGeometry(tree, node, link)
        elif(nodeType == 'ShaderNodeAttribute'):
            return resolveShaderNodeAttribute(tree, node, link)
        elif(nodeType == 'NodeReroute'):
            return resolveNodeReroute(tree, node, link)
        elif(nodeType == 'ShaderNodeUVMap'):
            return resolveShaderNodeUVMap(tree, node, link)
        elif(nodeType == 'ShaderNodeCombineRGB'):
            return resolveShaderNodeCombineRGB(tree, node, link)
        elif(nodeType == 'ShaderNodeSeparateRGB'):
            return resolveShaderNodeSeparateRGB(tree, node, link)
        elif(nodeType == 'ShaderNodeSeparateXYZ'):
            return resolveShaderNodeSeparateXYZ(tree, node, link)
        elif(nodeType == 'ShaderNodeGamma'):
            return resolveShaderNodeGamma(tree, node, link)
        elif(nodeType == 'ShaderNodeMath'):
            return resolveShaderNodeMath(tree, node, link)
        elif(nodeType == 'ShaderNodeClamp'):
            return resolveShaderNodeClamp(tree, node, link)
        elif(nodeType == 'ShaderNodeGroup'):
            return resolveShaderNodeGroup(tree, node, link)
        # elif(nodeType == 'ShaderNodeValue'):
        #     return resolveShaderNodeValue(tree, node, link)
        else:
            pr('/!\ unsupported node type: ' + nodeType + '. returning white')
            return lambda _: [1.0, 1.0, 1.0, 1.0]


    def solveInput(tree, input, node):
        try:
            pr('input: ' + input.name)
            link = next((l for l in tree.links if isSameNode(l.to_node, node) and isSameSocket(l.to_socket, input)), None)
            if(link):
                pr('output: ' + link.from_node.name)
                resolveAnyNodeForLoop = resolveAnyNode(tree, link.from_node, link)
                def solveInputForLoop(attrLoop):
                    return coerceColor(resolveAnyNodeForLoop(attrLoop))
                return solveInputForLoop
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
            color = resolveAnyNode(baseTree, link.from_node, link)(0)
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
            solveInputForLoop = solveInput(baseTree, getInput(matNode, srcName), matNode)
            for l in range(loops):
                # if((l % 100) < 50):
                #     continue
                cSrc = solveInputForLoop(l)
                cSrc = gammaCorrect(cSrc, 0.4545)
                cDst = dst.data[l].color
                # describeThing(cSrc)
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
            solveInputForLoop = solveInput(baseTree, getInput(matNode, srcName), matNode)
            for l in range(loops):
                cSrc = solveInputForLoop(l)
                # cSrc = gammaCorrect(cSrc, 2.2)
                # cSrc = gammaCorrect(cSrc, 2.2)
                # cSrc = gammaCorrect(cSrc, 2.2)
                cDst = dst.data[l].uv
                # describeThing(cSrc)
                if(singleChannel == None):
                    # cSrc = coerceColor(cSrc)
                    cDst[0] = cSrc[0]
                    cDst[1] = cSrc[1]
                    # cDst[0] = 0.5
                    # cDst[1] = 0.5
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

    
    duration = time.time() - timeStart
    print('time to complete: ' + str(duration) + ' seconds')




class HORIZON_OT_SquashAttributes(Operator):
    bl_idname = "horizon.squash_attributes"
    bl_label = "Squash Attributes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        squashAttributes(context)
        return {'FINISHED'}

def register():
    bpy.utils.register_class(HORIZON_OT_SquashAttributes)

def unregister():
    bpy.utils.unregister_class(HORIZON_OT_SquashAttributes)

if __name__ == "__main__":
    register()
