import importlib
from types import ModuleType
from typing import Optional


def import_module_safe( module_name : str ) -> Optional[ModuleType]:
    """
    Imports a module if it exists, else returns None. Will raise an
    exception if the module exists, but there is a problem loading it.
    """
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        if module_name.startswith( e.name ):
            return None
        else:
            raise
