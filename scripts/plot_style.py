"""Universal matplotlib style configuration for publication-quality Autumn Coin paper figures."""

import matplotlib as mpl

mpl.rcParams.update({
    'font.family': 'STIXGeneral',
    'mathtext.fontset': 'stix',
    'font.size': 9,
    'axes.labelsize': 9,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': False,
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'text.color': '#111111',
    'axes.labelcolor': '#111111',
    'xtick.color': '#111111',
    'ytick.color': '#111111',
    'axes.edgecolor': '#111111',
    'lines.linewidth': 1.3,
    'lines.markersize': 5,
    'legend.frameon': False,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05
})

# Universal colour-blind safe palette (Okabe-Ito inspired)
REGIME_COLORS = {
    "steady": "#009E73",        # bluish green
    "fluttering": "#0072B2",    # blue
    "tumbling": "#D55E00",      # vermillion / red-orange
    "mixed": "#E69F00",         # amber / orange
    "undetermined": "#7f7f7f",  # grey
}

REGIME_MARKERS = {
    "steady": "o",
    "fluttering": "^",
    "tumbling": "D",
    "mixed": "s",
    "undetermined": "X"
}

REGIME_ORDER = ["steady", "fluttering", "tumbling", "mixed", "undetermined"]
