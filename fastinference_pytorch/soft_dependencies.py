# AUTOGENERATED! DO NOT EDIT! File to edit: 00_soft_dependencies.ipynb (unless otherwise specified).

__all__ = ['soft_import', 'soft_imports', 'SoftDependencies']

# Cell
from importlib import import_module
from typing import *

# Cell
def soft_import(name:str):
    "Tries to import a module"
    try:
        import_module(name)
        return True
    except ModuleNotFoundError as e:
        if str(e) != f"No module named '{name}'": raise e
        return False

# Cell
def soft_imports(names:list):
    "Tries to import a list of modules"
    for name in names:
        o = soft_import(name)
        if not o: return False
    return True

# Cell
class _SoftDependencies:
    "A class which checks what dependencies can be loaded"
    def __init__(self):
        self.all = soft_imports(['PIL', 'pandas', 'torchvision', 'spacy'])
        self.vision = soft_import('torchvision')
        self.text = soft_import('spacy')
        self.tab = soft_import('pandas')

    def check(self) -> Dict[str, bool]: return self.__dict__.copy()

# Cell
SoftDependencies = _SoftDependencies()