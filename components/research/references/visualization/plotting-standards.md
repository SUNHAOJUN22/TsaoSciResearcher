# Plotting standards

Default backend: Python with Matplotlib. Use R/ggplot2 when explicitly requested or when the workflow is already R-native. Default raster preview is 450 DPI. Produce SVG or PDF for vector-suitable figures and TIFF when a journal requires it.

Use restrained colors, readable typography, consistent panel labels, explicit units and uncertainty. Avoid decorative 3D charts, rainbow color maps and unnecessary grids. Begin time at zero when the measurement logically starts there. Begin other axes at zero only when zero has interpretive meaning; otherwise disclose the range and avoid exaggeration.

Retain the raw data, transformed table, code, environment information and final exports. Visually inspect at the final physical size.
Supported families include line/scatter/bar/box/violin plots; heat maps and clustered matrices; PCA/UMAP/t-SNE; volcano/forest/funnel plots; Sankey/network/knowledge-graph views; spectroscopy, chromatography, XRD/XPS/NMR/FTIR/Raman; DSC/TGA/rheology/mechanics; RMSD/RMSF/Rg/hydrogen-bond/PCA/FEL/DCCM; band/DOS/PDOS/phonon/free-energy and reaction-path plots; polymer distributions/kinetics; FEM/CFD/process fields; multi-panel figures, mechanism diagrams, routes and graphical abstracts. Availability depends on real input data and host plotting tools.
