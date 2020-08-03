# AUTOGENERATED! DO NOT EDIT! File to edit: 01a_transforms.vision.ipynb (unless otherwise specified).

__all__ = ['load_image', 'PILBase', 'CropPad', 'RandomCrop', 'OldRandomCrop', 'Resize', 'RandomResizedCrop',
           'RatioResize', 'image2tensor', 'ToTensor', 'Normalize', 'IntToFloatTensor']

# Cell
from ..utils import *

# Cell
from torch import Tensor, stack, zeros_like as t0, ones_like as t1
from torch.distributions.bernoulli import Bernoulli

from PIL import Image
from numpy import ndarray

import operator, math, io

# Cell
from fastcore.utils import mk_class
from fastcore.transform import BypassNewMeta
from fastcore.dispatch import patch, Tuple, retain_type

# Cell
def load_image(fn, mode=None, **kwargs):
    "Open and load a `PIL.Image` and convert it to `mode`"
    im = Image.open(fn, **kwargs)
    im.load()
    im = im._new(im.im)
    return im.convert(mode) if mode else im

# Cell
class PILBase(Image.Image, metaclass=BypassNewMeta):
    _bypass_type=Image.Image
    @classmethod
    def create(cls, fn, mode='RGB')->None:
        "Open an `Image` from path `fn`"
        if isinstance(fn,ndarray): return cls(Image.fromarray(fn))
        if isinstance(fn, bytes): fn = io.BytesIO(fn)
        return cls(load_image(fn, mode))

# Cell
from torchvision.transforms.functional import pad as tvpad

# Cell
mk_class('PadMode', **{o:o.lower() for o in ['Zeros', 'Border', 'Reflection']},
         doc="All possible padding mode as attributes to get tab-completion and typo-proofing")

@patch
def _do_crop_pad(x:Image.Image, sz, tl, orig_sz,
                 pad_mode=PadMode.Zeros, resize_mode=Image.BILINEAR, resize_to=None):
    if any(tl.ge(0)):
        # At least one dim is inside the image, so needs to be cropped
        c = tl.max(0)
        x = x.crop((*c, *c.add(sz).min(orig_sz)))
    if any(tl.lt(0)):
        # At least one dim is outside the image, so needs to be padded
        p = (-tl).max(0)
        f = (sz-orig_sz-p).max(0)
        x = tvpad(x, (*p, *f), padding_mode=_pad_modes[pad_mode])
    if resize_to is not None: x = x.resize(resize_to, resize_mode)
    return x

@patch
def crop_pad(x:Image.Image, sz, tl=None, orig_sz=None, pad_mode=PadMode.Zeros, resize_mode=Image.BILINEAR, resize_to=None):
    if isinstance(sz,int): sz = (sz,sz)
    orig_sz = Tuple(_get_sz(x) if orig_sz is None else orig_sz)
    sz,tl = Tuple(sz),Tuple(((_get_sz(x)-sz)//2) if tl is None else tl)
    return x._do_crop_pad(sz, tl, orig_sz=orig_sz, pad_mode=pad_mode, resize_mode=resize_mode, resize_to=resize_to)

# Cell
def _process_sz(size):
    "Ensures that `size` will be a `Tuple`"
    if isinstance(size,int): size=(size,size)
    return Tuple(size[1],size[0])

def _get_sz(x):
    "Returns the current size of `x` as a `Tuple`"
    if isinstance(x, tuple): x = x[0]
    if not isinstance(x, Tensor): return Tuple(x.size)
    return im.size

# Cell
class CropPad():
    "Center crop or pad an image to `size`"
    order=0
    def __init__(self, size, pad_mode=PadMode.Zeros):
        self.size,self.pad_mode = _process_sz(size),pad_mode
    def __call__(self, x):
        orig_sz = _get_sz(x)
        tl = (orig_sz-self.size)//2
        return x.crop_pad(self.size,tl,orig_sz=orig_sz,pad_mode=self.pad_mode)

# Cell
RandomCrop = CropPad
OldRandomCrop = RandomCrop

# Cell
mk_class('ResizeMethod', **{o:o.lower() for o in ['Squish', 'Crop', 'Pad']},
         doc="All possible resize method as attributes to get tab-completion and typo-proofing")

# Cell
class Resize():
    "Resizes an image based on `method` with `pad_mode` and `resample`"
    order = 1
    def __init__(self, size, method=ResizeMethod.Crop, pad_mode=PadMode.Reflection,
                resample=Image.BILINEAR):
        self.size,self.pad_mode,self.method = _process_sz(size),pad_mode,method
        self.mode = resample

    def __call__(self, x):
        orig_sz = _get_sz(x)
        if self.method==ResizeMethod.Squish:
            return x.crop_pad(orig_sz, Tuple(0,0), orig_sz=orig_sz, pad_mode=self.pad_mode,
                             resize_method=self.resample, resize_to=self.size)
        w,h = orig_sz
        op = (operator.lt,operator.gt)[self.method==ResizeMethod.Pad]
        m = w/self.size[0] if op(w/self.size[0],h/self.size[1]) else h/self.size[1]
        cp_sz = (int(m*self.size[0]),int(m*self.size[1]))
        tl = Tuple(int(.5*(w-cp_sz[0])), int(.5*(h-cp_sz[1])))
        return x.crop_pad(cp_sz, tl, orig_sz=orig_sz, pad_mode=self.pad_mode,
                         resize_mode=self.mode, resize_to=self.size)

# Cell
class RandomResizedCrop():
    "Resizes an image randomly to `size` based on `min_scale`, `ratio`, `resample`, and `val_xtra`"
    order = 1
    def __init__(self, size, min_scale=0.08, ratio=(3/4,4/3), resample=Image.BILINEAR,
                val_xtra=0.14):
        size = _process_sz(size)
        self.size,self.min_scale,self.ratio,self.val_xtra = size,min_scale,ratio,val_xtra
        self.mode = resample

    def __call__(self, x):
        w,h = self.orig_sz = _get_sz(x)
        xtra = math.ceil(max(*self.size[:2])*self.val_xtra/8)*8
        final_size = (self.size[0]+xtra, self.size[1]+xtra)
        tl = (0,0)
        res = x.crop_pad(self.orig_sz, tl, orig_sz = self.orig_sz,
                        resize_mode=self.mode, resize_to=final_size)
        if final_size != self.size: res = res.crop_pad(self.size)
        return res

# Cell
class RatioResize():
    "Resizes while maintaining the aspect ratio"
    order = 1
    def __init__(self, max_sz, resample=Image.BILINEAR):
        self.max_sz,self.resample = max_sz, resample

    def __call__(self, x):
        w,h = _get_sz(x)
        if w >= h: nw,nh = self.max_sz, h*self.max_sz/w
        else:      nw,nh = w *self.max_sz/h,self.max_sz
        return Resize(size=(int(nh),int(nw)),resample=self.resample)(x)

# Cell
def image2tensor(img):
    "Transform image to byte tensor in `c*h*w` dim order."
    res = tensor(img)
    if res.dim()==2: res = res.unsqueeze(-1)
    return res.permute(2,0,1)

# Cell
class ToTensor():
    "Turn an input into a `Tensor`"
    order = 40
    def __init__(self, is_image=False):
        self.is_image = is_image
    def __call__(self, x):
        if self.is_image: return image2tensor(x)
        else: return tensor(x)

# Cell
class Normalize():
    "Normalize based on `mean` and `std` on `axes`"
    order,can_decode=99,True
    def __init__(self, mean=None, std=None, axes=(0,2,3)):
        self.mean,self.std,self.axes = tensor(mean),tensor(std),axes

    def __call__(self, x:Tensor, decode=False):
        std = to_device(self.std, x.device.type)
        mean = to_device(self.mean, x.device.type)
        if not decode: return (x-mean)/std
        else: return (x*std + mean)

# Cell
class IntToFloatTensor():
    "Converts integer to float"
    order,can_decode = 10,True
    def __init__(self, div=255., div_mask=0.):
        self.div = div
        # we do not store `div_mask`, this is what fastai2 exports
    def __call__(self, x:Tensor, decode=False):
        if decode == False: return x.float().div_(self.div)
        elif decode: return ((x.clamp(0.,1.)*self.div).long()) if self.div else o