#from .frame_check import FrameCheck
# framecheck/__init__.py

from framecheck.frame_check import FrameCheck
from framecheck.function_registry import register_check_function

# Expose only what you want to be part of the public API
__all__ = ['FrameCheck', 'register_check_function']