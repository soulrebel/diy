r"""
Do It yourself Dependency Injection
***********************************

A minimal but working dependency injector that works transparently, leveraging
metaclasses.

Not yet validated by production usage, it is mostly proposed as an educational
proof of concept.

Usage
+++++

Define an interface and an implementation as usual:

>>> class Interface(object):
...     def imethod(self):
...         raise NotImplementedError()

>>> class Implementation(Interface):
...     def __init__(self):
...         self.value = 'Implementation'
...     def imethod(self):
...         return self.value

Make Implementation the provider of Interface objects, by registering on the
*injector*:

>>> injector.provide(Interface, Implementation)

In a dependent class request injection of an object implementing Interface
for the **keyword** parameter named 'interface':

>>> @inject(interface=Interface)
... class Dependent(object):
...     def __init__(self, interface):
...         self.interface = interface

Instantiate object omitting the parameter 'interface':

>>> Dependent().interface.imethod()
'Implementation'

If you need to use the object with a custom parameter you can do it manually
using a **keyword** parameter:

>>> Dependent(interface='parameter').interface
'parameter'

It is also possible to set up multiple *named* implementations and/or use
custom singleton instances for an interface:

>>> instance = Implementation()
>>> instance.value = 'instance'
>>> injector.provide_instance(Interface, instance, name='name')

Just request them using named() in the decorator:

>>> @inject(interface=named('name', Interface))
... class NamedDependent(object):
...     def __init__(self, interface):
...         self.interface = interface

>>> NamedDependent().interface.imethod()
'instance'

But you can also turn classes into singletons with injected parameters with an
annotation:

>>> @singleton()
... class SomeSingleton(object):
...     pass

>>> SomeSingleton() is SomeSingleton()
True

And of course you can also inject classes, without the need for defining and
interface and registering an implementation:

>>> @inject(singleton=SomeSingleton)
... class SingletonDependent(object):
...     def __init__(self, singleton):
...         self.singleton = singleton

>>> SingletonDependent().singleton is SomeSingleton()
True

Other tests
+++++++++++

Class with custom metaclasses are supported:

>>> class Meta(type):
...     pass
>>> @inject(interface=Interface)
... class MetaDependent(object):
...     __metaclass__ = Meta
...     def __init__(self, interface):
...         self.interface = interface

>>> MetaDependent().interface.imethod()
'Implementation'

Derived classes get inject as well, but remember to call super!:

>>> class Derived(Dependent):
...     def __init__(self, extra, interface):
...         super(Derived, self).__init__(interface)
...         self.extra = extra

>>> Derived('extra').interface.imethod()
'Implementation'
"""


class Injector(object):

    def __init__(self):
        self._providers = {None: {}}

    def provide(self, iface, cls, name=None):
        "Bind an interface to a class"
        assert issubclass(cls, iface)
        self._providers.setdefault(name, {})[iface] = cls

    def provide_instance(self, iface, obj, name=None):
        "Bind an interface to an object"
        self._providers.setdefault(name, {})[iface] = lambda: obj

    def get_instance(self, iface_or_cls, name=None):
        "Get an object implementing an interface"
        provider = self._providers[name].get(iface_or_cls, iface_or_cls)
        return provider()


injector = Injector()
"Import this and provide your implementations"


class Injectable(type):
    "Metaclass to implements dependency injection"

    def __call__(cls, *args, **kwargs):
        for k, c in cls.__dependencies__.items():
            if not k in kwargs:
                kwargs[k] = injector.get_instance(c)
        r = super(Injectable, type(cls)).__call__(cls, *args, **kwargs)
        return r


class Singleton(type):
    "Metaclass to implement instance reuse"

    def __call__(cls, *args, **kwargs):
        r = getattr(cls, '__instance__', None)
        if r is None:
            r = super(Singleton, type(cls)).__call__(cls, *args, **kwargs)
            setattr(cls, '__instance__', r)
        return r


def _with_meta(new_meta, cls):
    meta = type(cls)
    if not issubclass(meta, new_meta):
        # class has a custom metaclass, we extend it on the fly
        name = new_meta.__name__ + meta.__name__
        meta = type(name, (new_meta,) + meta.__bases__, {})
        # rebuild the class
        return meta(cls.__name__, cls.__bases__, dict(cls.__dict__))
    else:
        return cls


def _inject(_injectable_type, **dependencies):
    def annotate(cls):
        cls = _with_meta(_injectable_type, cls)
        setattr(cls, '__dependencies__', dependencies)
        return cls
    return annotate


def inject(**dependencies):
    "Bind constructor arguments to implementations"
    return _inject(Injectable, **dependencies)


def singleton(**dependencies):
    "Make the class a singleton, accepts the same parameters as inject()"
    return _inject(Singleton, **dependencies)


class Named(type):

    def __call__(cls):
        return injector.get_instance(cls.iface, name=cls.name)


def named(name, iface):
        return Named('%s<%s>' % (iface.__name__, name), (object,),
                     {'iface': iface, 'name': name})

__all__ = ['injector', 'inject', 'singleton', 'named']
