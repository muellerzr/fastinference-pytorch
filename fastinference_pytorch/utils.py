# AUTOGENERATED! DO NOT EDIT! File to edit: 04_utils.ipynb (unless otherwise specified).

__all__ = ['noop', 'apply', 'to_device']

# Cell
import torch
import numpy as np
from torch import Tensor
from fastcore.utils import is_listy, is_iter

# Cell
def noop(x=None, *args,**kwargs):
    "Do nothing"
    return x

# Cell
def apply(func, x, *args, **kwargs):
    "Apply `func` recursively to `x`, passing on args"
    if is_listy(x): return type(x)([apply(func, o, *args, **kwargs) for o in x])
    if isinstance(x,dict):  return {k: apply(func, v, *args, **kwargs) for k,v in x.items()}
    res = func(x, *args, **kwargs)
    return res if x is None else retain_type(res, x)

# Cell
def to_device(b, device='cpu'):
    "Recursively put `b` on `device`."
    def _inner(o): return o.to(device, non_blocking=True) if isinstance(o,Tensor) else o.to_device(device) if hasattr(o, "to_device") else o
    return apply(_inner, b)

# Cell
def _array2tensor(x):
    if x.dtype==np.uint16: x.astype(np.float32)
    return torch.from_numpy(x)