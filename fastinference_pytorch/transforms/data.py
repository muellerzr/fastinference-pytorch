# AUTOGENERATED! DO NOT EDIT! File to edit: 01b_transforms.data.ipynb (unless otherwise specified).

__all__ = ['Categorize']

# Cell
from fastcore.utils import L

# Cell
class Categorize():
    "Stores vocab and stores traversable list in `i2n` (index to name)"
    def __init__(self, vocab=[], add_na=False):
        self.vocab = vocab
        self.i2n = dict(zip(vocab,range(len(vocab))))