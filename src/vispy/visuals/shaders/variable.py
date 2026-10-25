# -*- coding: utf-8 -*-
# Copyright (c) Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
import re

import numpy as np
from .shader_object import ShaderObject

VARIABLE_TYPES = ('const', 'uniform', 'attribute', 'varying', 'inout')


class Variable(ShaderObject):
    """Representation of global shader variable

    Parameters
    ----------
    name : str
        the name of the variable. This string can also contain the full
        definition of the variable, e.g. 'uniform vec2 foo'. Explicit arrays
        use literal dimensions, e.g. 'uniform vec3 samples[2][3]'. Array
        values have shape (2, 3, 3), with packed components on the last axis.
        Multidimensional scalar arrays may omit a final singleton component axis.
    value : {float, int, tuple, GLObject}
        If given, vtype and dtype are determined automatically. If a
        float/int/tuple is given, the variable is a uniform. If a gloo
        object is given that has a glsl_type property, the variable is
        an attribute and
    vtype : {'const', 'uniform', 'attribute', 'varying', 'inout'}
        The type of variable.
    dtype : str
        The data type of the variable, e.g. 'float', 'vec4', 'mat', etc.
    """

    _vtype_32_conversion = {'in': 'attribute', 'out': 'varying'}
    _vtype_23_conversion = {'attribute': 'in', 'varying': 'out'}

    def __init__(self, name, value=None, vtype=None, dtype=None):
        super(Variable, self).__init__()

        # allow full definition in first argument
        if ' ' in name:
            fields = name.split(' ')
            if len(fields) == 3:
                vtype, dtype, name = fields
            elif len(fields) == 4 and fields[0] == 'const':
                vtype, dtype, name, value = fields
            else:
                raise ValueError('Variable specifications given by string must'
                                 ' be of the form "vtype dtype name" or '
                                 '"const dtype name value".')

        if not (isinstance(name, str) or name is None):
            raise TypeError("Variable name must be string or None.")

        self._array_shape = ()
        if name is not None and '[' in name:
            declaration = re.fullmatch(r'([A-Za-z_]\w*)\s*((?:\[\s*\d+\s*\]\s*)+)', name)
            if declaration is None:
                raise ValueError('Array name must contain positive literal dimensions.')
            self._array_shape = tuple(map(int, re.findall(r'\d+', declaration.group(2))))
            if not all(dimension > 0 for dimension in self._array_shape):
                raise ValueError('Array dimensions must be positive.')
            name = declaration.group(1)

        self._state_counter = 0
        self._name = name
        self._vtype = self._vtype_32_conversion.get(vtype, vtype)
        self._dtype = dtype
        self._value = None

        # If vtype/dtype were given at init, then we will never
        # try to set these values automatically.
        self._type_locked = self._vtype is not None and self._dtype is not None

        if value is not None:
            self.value = value

        if self._vtype and self._vtype not in VARIABLE_TYPES:
            raise ValueError('Not a valid vtype: %r' % self._vtype)

    @property
    def name(self):
        """The name of this variable."""
        return self._name

    @name.setter
    def name(self, n):
        # Settable mostly to allow automatic setting of varying names
        # See ShaderObject.create()
        if self._name != n:
            self._name = n
            self.changed(code_changed=True)

    @property
    def vtype(self):
        """The type of variable (const, uniform, attribute, or varying).

        For in/out variables (GLSL 150+), vtype is 'varying'.
        """
        return self._vtype

    @property
    def dtype(self):
        """The type of data (float, int, vec, mat, ...)."""
        return self._dtype

    @property
    def array_shape(self):
        """Ordered array dimensions from the declaration, excluding components."""
        return self._array_shape

    @property
    def value(self):
        """The value associated with this variable."""
        return self._value

    @value.setter
    def value(self, value):
        if self._array_shape:
            # An explicit declaration disambiguates arrays from the legacy
            # vector/matrix inference. Match Program's public upload contract.
            from ...gloo.program import Program
            if self.vtype != 'uniform' or not self._type_locked or 'sampler' in self.dtype:
                raise TypeError('Array values require an explicit non-sampler uniform type.')
            if self.dtype not in Program._gtypes:
                raise TypeError('Unsupported uniform array type %r.' % self.dtype)
            dtype, components = Program._gtypes[self.dtype]
            data = np.asarray(value, dtype=dtype)
            expected = self._array_shape + (components,)
            if (len(self._array_shape) > 1 and components == 1 and
                    data.shape == self._array_shape):
                data = data.reshape(expected)
            if data.shape != expected:
                raise ValueError('Uniform array %r needs shape %s not %s.'
                                 % (self.name, expected, data.shape))
            # Rejection must leave both the old value and cache identity intact.
            self._value = data
            self._state_counter += 1
            return
        if isinstance(value, (tuple, list)) and 1 < len(value) < 5:
            vtype = 'uniform'
            dtype = 'vec%d' % len(value)
        elif isinstance(value, np.ndarray):
            if value.ndim == 1 and (1 < len(value) < 5):
                vtype = 'uniform'
                dtype = 'vec%d' % len(value)
            elif value.ndim == 2 and value.shape in ((2, 2), (3, 3), (4, 4)):
                vtype = 'uniform'
                dtype = 'mat%d' % value.shape[0]
            else:
                raise ValueError("Cannot make uniform value for %s from array "
                                 "of shape %s." % (self.name, value.shape))
        elif np.isscalar(value):
            vtype = 'uniform'
            if isinstance(value, (float, np.floating)):
                dtype = 'float'
            elif isinstance(value, (int, np.integer)):
                dtype = 'int'
            else:
                raise TypeError("Unknown data type %r for variable %r" %
                                (type(value), self))
        elif getattr(value, 'glsl_type', None) is not None:
            # Note: hasattr() is broken by design--swallows all exceptions!
            vtype, dtype = value.glsl_type
        else:
            raise TypeError("Unknown data type %r for variable %r" %
                            (type(value), self))

        self._value = value
        self._state_counter += 1

        if self._type_locked:
            if dtype != self._dtype or vtype != self._vtype:
                raise TypeError('Variable is type "%s"; cannot assign value '
                                '%r.' % (self.dtype, value))
            return

        # update vtype/dtype and emit changed event if necessary
        changed = False
        if self._dtype != dtype:
            self._dtype = dtype
            changed = True
        if self._vtype != vtype:
            self._vtype = vtype
            changed = True
        if changed:
            self.changed(code_changed=True, value_changed=True)

    @property
    def state_id(self):
        """Return a unique ID that changes whenever the state of the Variable
        has changed. This allows ModularProgram to quickly determine whether
        the value has changed since it was last used.
        """
        return id(self), self._state_counter

    def __repr__(self):
        return ("<%s \"%s %s %s\" at 0x%x>" % (self.__class__.__name__,
                                               self._vtype, self._dtype,
                                               self.name, id(self)))

    def expression(self, names):
        return names[self]

    def _vtype_for_version(self, version):
        """Return the vtype for this variable, converted based on the GLSL version."""
        vtype = self.vtype
        if version is None or version[0] == 120:
            return self._vtype_32_conversion.get(vtype, vtype)
        else:
            return self._vtype_23_conversion.get(vtype, vtype)

    def definition(self, names, version, shader):
        if self.vtype is None:
            raise RuntimeError("Variable has no vtype: %r" % self)
        if self.dtype is None:
            raise RuntimeError("Variable has no dtype: %r" % self)

        name = names[self] + ''.join('[%d]' % size for size in self._array_shape)
        vtype = self._vtype_for_version(version)
        if vtype == 'const':
            return '%s %s %s = %s;' % (vtype, self.dtype, name, self.value)
        else:
            return '%s %s %s;' % (vtype, self.dtype, name)


class Varying(Variable):
    """Representation of a varying (variables passed from one shader to the
    next).

    Varyings can inherit their dtype from another Variable, allowing for
    more flexibility in composing shaders.
    """

    def __init__(self, name, dtype=None):
        self._link = None
        self._src_func = None
        self._dst_func = None
        Variable.__init__(self, name, vtype='varying', dtype=dtype)

    @property
    def value(self):
        """The value associated with this variable."""
        return self._value

    @value.setter
    def value(self, value):
        if value is not None:
            raise TypeError("Cannot assign value directly to varying.")

    @property
    def dtype(self):
        if self._dtype is None:
            if self._link is None:
                return None
            else:
                return self._link.dtype
        else:
            return self._dtype

    def link(self, var):
        """Link this Varying to another object from which it will derive its
        dtype.

        This method is used internally when assigning an attribute to
        a varying using syntax ``function[varying] = attr``.
        """
        assert self._dtype is not None or hasattr(var, 'dtype')
        self._link = var
        self.changed()

    def invar(self, array=False):
        """Return a varying that defines itself using the same name as this,
        but as an `in` variable instead of `out`.
        """
        return InVar(self, array=array)


class InVar(Variable):
    def __init__(self, var, array=False):
        self._var = var
        self._array = array
        Variable.__init__(self, var.name)

    @property
    def value(self):
        """The value associated with this variable."""
        return self._var.value

    @value.setter
    def value(self, value):
        if value is not None:
            raise TypeError("Cannot assign value directly to varying.")

    @property
    def dtype(self):
        return self._var.dtype

    @property
    def array_shape(self):
        return self._var.array_shape

    def definition(self, names, version, shader):
        # inherit name from source variable
        name = names[self._var]
        dtype = self._var.dtype
        shape = ''.join('[%d]' % dimension for dimension in self.array_shape)

        if version[0] <= 120:
            return "varying %s %s%s;" % (dtype, name, shape)
        else:
            if self._array:
                return "in %s %s[]%s;" % (dtype, name, shape)
            else:
                return "in %s %s%s;" % (dtype, name, shape)

    def expression(self, names):
        return names[self._var]
