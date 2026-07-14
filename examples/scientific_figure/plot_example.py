#!/usr/bin/env python3
"""Synthetic demonstration only; no experimental claim is made."""
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
x=np.linspace(0,100,101); rng=np.random.default_rng(7); y=1.2+0.04*np.log1p(x)+rng.normal(0,0.01,len(x))
fig,ax=plt.subplots(figsize=(6.4,4.0)); ax.plot(x,y,label='Synthetic demonstration')
ax.set(xlabel='Time (ns)',ylabel='Response (a.u.)',xlim=(0,100)); ax.grid(False); ax.legend(frameon=False)
fig.tight_layout(); out=Path(__file__).resolve().parent
fig.savefig(out/'synthetic-demo.png',dpi=450); fig.savefig(out/'synthetic-demo.svg')
