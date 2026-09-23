"""Reference implementations for the AI Engineering from Scratch series.

Every module here is standard library only, deterministic, and written to
be read line by line in an article. Nothing in this package depends on a
third-party numeric stack, so any reader with Python 3.8 or newer can run
every artifact in this repository with no install step.

Modules:
    linalg            dense matrix operations, a stable softmax, rank and
                      null space by Gauss-Jordan elimination
    bpe               byte-level byte pair encoding: train, encode, decode
    embedding         token and position embedding tables
    attention         scaled dot-product attention and multi-head attention
    rope              rotary position embedding
    layernorm         layer normalization and the pre/post-norm block
    residual          the residual stream, recorded write by write
    feedforward       feed-forward sublayers, gated and ungated
    gqa               grouped-query and multi-query attention
    mla               multi-head latent attention and the absorption fold
    sparse_attention  sliding windows, attention sinks, learned selection
    consistent_hashing  the hash ring from the system-design weeks
"""

__all__ = [
    "attention",
    "bpe",
    "consistent_hashing",
    "embedding",
    "feedforward",
    "gqa",
    "layernorm",
    "linalg",
    "mla",
    "residual",
    "rope",
    "sparse_attention",
]
