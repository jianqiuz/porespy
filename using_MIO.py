# %% Import necessary packages and functions
import porespy as ps
import numpy as np
import matplotlib.pyplot as plt
from edt import edt
plt.rcParams['figure.facecolor'] = "#FFFFFF"  # "#002b36"

# %%  Generate or load a test image
np.random.seed(10)
im = ps.generators.blobs(shape=[750, 750], porosity=0.6, blobiness=2)
pad = 60
im = np.pad(im, pad_width=[[0, 0], [pad, 0]], mode='edge')
# Generate border
bd = np.zeros_like(im, dtype=bool)
bd[:, :2] = 1
bd *= im
im = ps.filters.trim_disconnected_blobs(im=im, inlets=bd)
dt = edt(im)

# %% Apply IP on image in single pass
inv_seq, inv_size = ps.filters.invade_region(im=im, bd=bd, thickness=3,
                                             return_sizes=True, max_iter=15000)
inv_seq = inv_seq[:, pad:]
inv_size = inv_size[:, pad:]
# Do some post-processing
# inv_seq_trapping = ps.filters.find_trapped_regions(seq=inv_seq, bins=None,
#                                                    return_mask=False)
# inv_satn = ps.tools.seq_to_satn(seq=inv_seq_trapping)
inv_satn = ps.tools.seq_to_satn(seq=inv_seq)

# %%
sizes = np.arange(int(dt.max())+1, 0, -1)
mio = ps.filters.porosimetry(im=im, inlets=bd, sizes=sizes, mode='dt')[:, pad:]
im = im[:, pad:]
mio_satn = ps.tools.size_to_satn(size=mio, im=im)
mio_seq = ps.tools.size_to_seq(mio)
mio_seq[im*(mio_seq == 0)] = -1  # Adjust to set uninvaded to -1
mio_satn_2 = ps.tools.seq_to_satn(mio_seq)
# np.all(mio_satn == mio_satn_2)  # Use this as a test

# %%
d = ps.metrics.pc_curve_from_ibip(im, inv_size, inv_seq, voxel_size=1e-5)
e = ps.metrics.pc_curve_from_mio(im=im, sizes=mio, voxel_size=1e-5, stepped=True)

# %%
fig, ax = plt.subplots()
ax.semilogx(np.array(d.pc), d.snwp, 'g-', linewidth=2.0)
ax.semilogx(np.array(e.pc), e.snwp, 'r--', markersize=20, linewidth=5, alpha=0.6)
ax.xaxis.grid(True, which='both')
