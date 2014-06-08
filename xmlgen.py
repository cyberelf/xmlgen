#!/usr/bin/env python

# Generate xml from XSD file
# 1. use pyxbgen to generate a xsd binding 
# 2. call genXML on the root element

import inspect
import test
import pyxb
import random
SIMPLE_TYPE = pyxb.binding.basis.simpleTypeDefinition
ENUM_TYPE = pyxb.binding.basis.enumeration_mixin

def genXML(element):
    """iterate all sub elements and attributes
        @element the element to be scanned
    """
    name = str(element.name())
    cls = element.typeDefinition()
    rslt = {}
    attrs = {}
    # Attribtues first,  
    for atr in cls._AttributeMap.itervalues():
        attrs.update({str(atr.name()): genVal(atr.dataType())})
    rslt = {"__attributes": attrs}
    if isSimpleType(cls):
        rslt.update({name: genVal(cls)})
    else:
        # Atomaton iterative
        for e in traverseAutomaton(cls._Automaton):
            ecls = e.typeDefinition()
            if isSimpleType(ecls):
                rslt.update({str(e.name()): genVal(ecls)})
            else:
                rslt.update({str(e.name()): genXML(e)})
    return rslt

def traverseAutomaton(atm, manner="first"):
    """traverse the automaton and return a list of subelements, 
        manners supported: first, shortest, longest"""
    # TODO: Add support for other manner other than the first
    # make a copy of the set
    #states = set(atm.states.copy())
    # state : weight 
    MAX_WEIGHT = 10
    states = dict(zip(atm.states, [0]*len(atm.states)))
    # Empty atomaton
    if len(states)==0:
        return []
    rslt = []
    tanspath = []
    transet = atm.initialTransitions
    while True:
        # pick the state with the lowest weight
        min_weight = MAX_WEIGHT
        best_state = None
        for t in transet:
            state = t.destination
            # compare state weight
            if states[state] < min_weight:
                min_weight = states[state]
                best_state = state
        if best_state is not None:
            states[best_state] += 1
            rslt.append(best_state.symbol.elementBinding())
            transet = best_state.transitionSet
            # Return on the first found final state
            if best_state.finalUpdate is not None:
                break
        else:
            raise(Exception("Max retry reached for all nodes!"))
    return rslt

def isSimpleType(cls):
    if SIMPLE_TYPE in inspect.getmro(cls):
        return True
    else:
        return False

def isENM(cls):
    if ENUM_TYPE in inspect.getmro(cls):
        return True
    else:
        return False

def genVal(cls, manner="first"):
    """Genrates value from a simple type class"""
    if isSimpleType(cls):
        gen = getgenerator(cls)
        return gen.generate(manner)
    else:
        raise(Exception("Cannot genrate value from complex type"))

def getgenerator(cls):
    """Get a proper generator by class"""
    GMAP={
        pyxb.binding.datatypes.string: StringGenerator,
        pyxb.binding.datatypes.int: IntGenerator,
        pyxb.binding.datatypes.unsignedLong: UintGenerator,
        pyxb.binding.datatypes.integer: IntegerGenerator
    }
    for c in GMAP.keys():
        if c in inspect.getmro(cls):
            return GMAP[c](cls)     
    # String as default
    print "WARNING: No proper generator found for %s, use string as default" % cls
    return StringGenerator(cls)

class ValGenerator:
    """The class used to generate values from an object according to type and constraints"""
    BASE = ""
    def __init__(self, cls):
        self.fromcls = cls
        self.vallist = None

    def generate(self, manner="first"):
        """Generate a value in the following manners: 
            first     :return the first or smallest value 
            last      :return the last or largest value 
            random    :return a random value 
            overflow  :return a value larger than the last
            underflow :return a value smaller than the first
        """
        values = self.getvallist()
        # choose one if enum
        if isENM(self.fromcls):
            if random:
                return random.choice(self.fromcls.values())
            else:
                return self.fromcls.values()[0]

        # Template process for data types
        manner = manner.lower()
        if manner == "first":
            return self.getfirst()
        elif manner == "last":
            return self.getlast()
        elif manner == "random":
            return self.getrandom()
        elif manner == "overflow":
            return self.getoverflow()
        elif manner == "underflow":
            return self.getunderflow()
        else:
            raise(Exception("No such value-getting manner %s" % manner)) 

    def _enum(self):
        """whether an enum"""
        if hasattr(self.fromcls, '_CF_enumeration'):
            vals = self.fromcls._CF_enumeration.values()
            if len(vals) > 0:
                return vals
        return False

    def getvallist(self):
        """Get a list of value"""
        e = self._enum()
        if e:
            return e
        return self._getbarevallist()

    def _getbarevallist(self):
        """Get value list other than enum"""
        pass

    def getfirst(self):
        """Get the maximun of a value type"""
        return self.getvallist()[0]

    def getlast(self):
        """Get the minimun of a value type"""
        return self.getvallist()[-1]

    def getunderflow(self):
        """Get the min-1 of a value type"""
        return self._minusone(self.getfirst())

    def getoverflow(self):
        """Get the max+1 of a value type"""
        self._plusone(self.getlast())

    def getrandom(self):
        """Get the a random value type from the valuelist"""
        return random.choice(self.getvallist())

    def _plusone(self, val):
        """Add "one" to the value"""
        pass

    def _minusone(self, val):
        """Minus "one" from the value"""
        pass



class StringGenerator(ValGenerator):

    def _getbarevallist(self):
        """Get value list other than enum, possible constrains:
            datatypes.string._CF_minLength = CF_minLength()
            datatypes.string._CF_maxLength = CF_maxLength()
            datatypes.string._CF_enumeration = CF_enumeration(value_datatype=datatypes.string)
            datatypes.string._CF_pattern = CF_pattern()
            datatypes.string._CF_whiteSpace = CF_whiteSpace(value=_WhiteSpace_enum.preserve)
            datatypes.string._CF_length = CF_length()
        """
        if self.vallist:
            return self.vallist
        minlen = 1
        maxlen = 255
        if self.fromcls._CF_minLength.value():
            minlen = int(self.fromcls._CF_minLength.value())
        if self.fromcls._CF_maxLength.value():
            maxlen = int(self.fromcls._CF_maxLength.value())
        if self.fromcls._CF_length.value() is not None:
            minlen = maxlen = self.fromcls._CF_length.value()
        # TODO: add pattern support
        # TODO: add whitespace check: ._CF_whiteSpace.normalizeString("asd")
        self.vallist = ['a'*minlen, 'm'*((minlen+maxlen)/2), 'z'*maxlen]
        return self.vallist

    def _minusone(self, val):
        """Return a string shorter"""
        if len(val) == 0:
            raise(Exception("No string shorter than empty string!"))
        # Not considering pattern here
        return val[0:-1]

    def _plusone(self, val):
        """Return a string longer than val"""
        # Not considering pattern here
        return val+val[-1]

class IntGenerator(ValGenerator):
    """Generator for signed int types including:
        int, long, short
        value returned are always string
    """
    def _getbarevallist(self):
        """Get value list other than enum, possible constrains:
            datatypes.int._CF_minInclusive = CF_minInclusive(value_datatype=datatypes.int, value=datatypes.anySimpleType(u'-2147483648'))
            datatypes.int._CF_maxInclusive = CF_maxInclusive(value_datatype=datatypes.int, value=datatypes.anySimpleType(u'2147483647'))
        """
        if self.vallist:
            return self.vallist
        minv = self.fromcls._CF_minInclusive.value()
        maxv = self.fromcls._CF_maxInclusive.value()
        self.vallist = [minv, self._plusone(minv), maxv]
        return self.vallist

    def _minusone(self, val):
        """Return a smaller integer"""
        # Not consider long type overflow here
        return str(long(val)-1)

    def _plusone(self, val):
        """Return a larger integer"""
        # Not consider long type overflow here
        return str(long(val)+1)

class UintGenerator(ValGenerator):
    """Generator for unsigned int types including:
        unsignedByte, unsignedInt, unsignedLong, unsignedShort
        value returned are always string
    """
    def _getbarevallist(self):
        """Get value list other than enum, possible constrains:
            datatypes.unsignedLong._CF_maxInclusive = CF_maxInclusive(value_datatype=datatypes.unsignedLong, value=datatypes.anySimpleType(u'18446744073709551615'))
        """
        if self.vallist:
            return self.vallist
        minv = u"0"
        maxv = self.fromcls._CF_maxInclusive.value()
        self.vallist = [minv, self._plusone(minv), maxv]
        return self.vallist

    def _minusone(self, val):
        """Return a smaller integer"""
        # Not consider long type overflow here
        return str(long(val)-1)

    def _plusone(self, val):
        """Return a larger integer"""
        # Not consider long type overflow here
        return str(long(val)+1)        

class IntegerGenerator(ValGenerator):
    """Generator for integer types including:
        integer
        value returned are always string
    """
    def _getbarevallist(self):
        """Get value list other than enum, possible constrains:
            datatypes.integer._CF_pattern = CF_pattern()
            datatypes.integer._CF_pattern.addPattern(pattern=u'[\\-+]?[0-9]+')
        """
        if self.vallist:
            return self.vallist
        # just a stub here, TBR
        minv = "0"
        maxv = "65535"
        self.vallist = [minv, "1", maxv]
        return self.vallist

    def _minusone(self, val):
        """Return a smaller integer"""
        # Not consider long type overflow here
        return str(long(val)-1)

    def _plusone(self, val):
        """Return a larger integer"""
        # Not consider long type overflow here
        return str(long(val)+1)  

def testgen():
    po=test.purchaseOrder
    return genXML(po)

if __name__ == '__main__':
    print "Testing"
    print testgen()
