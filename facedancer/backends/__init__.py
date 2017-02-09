
__all__ = []

# Import the GreatDancer code, but only if we have its
# dependencies. This isn't the most elegant way to do this--
# we'll have to generalize eventually!
try:
    import greatfet
    __all__.append("GreatDancerApp")
except ImportError:
    pass

__all__.extend(["GoodFETMaxUSBApp", "MAXUSBApp"])
