# AUTOGENERATED! DO NOT EDIT! File to edit: 03_rebuild.ipynb (unless otherwise specified).

__all__ = ['load_data', 'load_model', 'get_image', 'get_tfm', 'generate_pipeline', 'make_pipelines', 'Learner']

# Cell
import io, operator, pickle, torch

# Cell
from pathlib import Path
from numpy import ndarray
from fastcore.utils import _patched, store_attr

# Cell
from .transforms.vision import *
from .transforms.data import *
from .utils import to_device, tensor

# Cell
def load_data(path:Path=Path('.'), fn='data'):
    "Opens `pkl` file containing exported `Transform` information"
    if '.pkl' not in fn: fn += '.pkl'
    if not isinstance(path, Path): path = Path(path)
    with open(path/fn, 'rb') as handle:
        tfmd_dict = pickle.load(handle)
    return tfmd_dict

# Cell
def load_model(path:Path=Path('.'), fn='model', cpu=True):
    if '.pkl' not in fn: fn += '.pkl'
    if not isinstance(path, Path): path = Path(path)
    return torch.load(path/fn, map_location='cpu' if cpu else None)

# Cell
def get_image(fn, mode='RGB'): return PILBase.create(fn,mode=mode)

# Cell
def get_tfm(key, tfms):
    "Makes a transform from `key`. Class or function must be in global memory (imported)"
    args = tfms[key]
    return globals()[key](**args)

# Cell
def generate_pipeline(tfms, order=True) -> dict:
    "Generate `pipe` of transforms from dict and (potentially) sort them"
    pipe = []
    for key in tfms.keys():
        tfm = get_tfm(key, tfms)
        pipe.append(tfm)
    if order: pipe = sorted(pipe, key=operator.attrgetter('order'))
    return pipe

# Cell
def make_pipelines(tfms) -> dict:
    "Make `item` and `batch` transform pipelines"
    pipe, keys = {}, ['after_item', 'after_batch']
    for key in keys:
        pipe[key] = generate_pipeline(tfms[key], True)
    if not any(isinstance(x, ToTensor) for x in pipe['after_item']):
        pipe['after_item'].append(ToTensor(False))
    return pipe

# Cell
class Learner():
    """
    Similar to a `fastai` learner for inference

    Params:
      > `path`: The exact path to where your data and model is stored, relative to the `cwd`
      > `data_fn`: Filename of your pickled data
      > `model_fn`: Filename of your model
      > `data_func`: A function in which has the ability to grab your data based on some input.
                     The default grabs an image in a location and opens it with Pillow
      > `bs`: The batch size you are wanting to use per inference (this can be tweaked later)
      > `cpu`: Whether to use the CPU or GPU

    Example use:

    learn = Learner('models/data', 'models/model', data_func=image_getter, bs=4, cpu=True)
    """
    def __init__(self, path = Path('.'), data_fn='data', model_fn='model', data_func=None, bs=16, cpu=False):
        data = load_data(path, data_fn)
        self.n_inp = data['n_inp']
        self.pipelines = make_pipelines(data)
        self.after_item = self.pipelines['after_item']
        self.after_batch = self.pipelines['after_batch']
        self.tfm_y = generate_pipeline(data['tfms'], order=False)
        self.model = load_model(path, model_fn, cpu)
        self.device = 'cpu' if cpu else 'cuda'
        store_attr(self, 'data_func,bs')
        self.decode_func = None

    def _make_data(self, data):
        "Passes `data` through `after_item` and `after_batch`, splitting into batches"
        self.n_batches = len(data) // self.bs + (0 if len(data)%self.bs == 0 else 1)
        batch,batches = [],[]
        for d in data:
            d = self.data_func(d)
            for tfm in self.after_item: d = tfm(d)
            batch.append(d)
            if len(batch) == self.bs or (len(batches) == self.n_batches - 1 and len(batch) == len(data)):
                batch = torch.stack(batch, dim=0)
                batch = to_device(batch, self.device)
                for tfm in self.after_batch:
                    batch = tfm(batch)
                batches.append(batch)
                batch = []
        return batches

    def _decode_inputs(self, inps, outs):
        "Decodes images through `after_batch`"
        for tfm in self.after_batch[::-1]:
            if hasattr(tfm, 'can_decode'):
                inps = to_device(tfm(inps, decode=True))
        outs.insert(len(outs), inps)
        return outs

    def get_preds(self, data, raw_outs=False, decode_func=None, with_input=False):
        """
        Gather predictions on `data` with possible decoding.

        Params:
          > `data`: Incoming data formatted to what `self.data_func`is expecting
          > `raw_outs`: Whether to return the raw outputs
          > `decode_func`: A function to use for decoding potential outputs.
                           While the default is `None`, see `decode_cel` for an example
          > `with_input`: Whether to return a decoded input up to what the model was passed
        """
        inps, outs, dec_out, raw = [],[],[],[]
        batches = self._make_data(data)
        if self.n_inp > 1:
            [inps.append([]) for _ in range(n_inp)]
        with torch.no_grad():
            for batch in batches:
                if with_input:
                    if self.n_inp > 1:
                        for i in range(self.n_inp):
                            inps[i].append(batch[i].cpu())
                        else:
                            inps.append(batch[0].cpu())
                self.model.eval()
                out = self.model(batch[:self.n_inp])
            raw.append(out)
            if self.decode_func is not None: dec_out.append(decode_func(out))
        raw = torch.cat(raw, dim=0).cpu().numpy()
        if self.decode_func is not None: dec_out = torch.cat(dec_out, dim=0)
        if self.decode_func is None or raw_outs: outs.insert(0, raw)
        else: outs.insert(0, raw)

        if with_input: outs = self._decode_inputs(inps, outs)
        return outs