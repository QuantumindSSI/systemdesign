"""Reference implementations for the AI Engineering from Scratch series.

Every module here is standard library only, deterministic, and written to
be read line by line in an article. Nothing in this package depends on a
third-party numeric stack, so any reader with Python 3.8 or newer can run
every artifact in this repository with no install step.

Modules:
    linalg     dense matrix operations with a numerically stable softmax
    bpe        byte-level byte pair encoding: train, encode, decode
    attention  scaled dot-product attention and multi-head self-attention
"""

__all__ = ["attention", "bpe", "linalg"]
