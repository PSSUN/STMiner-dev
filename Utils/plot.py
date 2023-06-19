import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from Algorithm.distribution import get_exp_array


def plot_heatmap(result,
                 adata,
                 label,
                 cmap=None,
                 num_cols=5,
                 vmax=99,
                 vmin=0):
    """

    :param cmap:
    :type cmap:
    :param result:
    :type result:
    :param adata:
    :type adata:
    :param label:
    :type label:
    :param num_cols:
    :type num_cols:
    :param vmax:
    :type vmax:
    :param vmin:
    :type vmin:
    """
    gene_list = list(result[result['labels'] == label]['gene_id'])
    if cmap is not None:
        new_cmap = cmap
    else:
        new_colors = ['lightgrey', 'lightblue', '#00FF00', '#FFFF00', '#FFA500', '#FF0000']
        new_cmap = colors.ListedColormap(new_colors)
    num_plots = len(gene_list)
    num_cols = num_cols
    num_rows = (num_plots + num_cols - 1) // num_cols
    fig, axes = plt.subplots(num_rows, num_cols, figsize=(12, 3 * num_rows))
    fig.subplots_adjust(hspace=0.5)
    for i, heatmap in enumerate(gene_list):
        row = i // num_cols
        col = i % num_cols
        ax = axes[row, col]
        arr = get_exp_array(adata, heatmap)
        sns.heatmap(arr,
                    cbar=False,
                    ax=ax,
                    cmap=new_cmap,
                    vmax=np.percentile(arr, vmax),
                    vmin=np.percentile(arr, vmin)
                    )
        ax.axis('off')
        ax.set_title(heatmap)
    plt.tight_layout()
    plt.show()


def plot_pattern(result, adata, label, cmap=None, vmax=99):
    li = list(result[result['labels'] == label]['gene_id'])
    total = np.zeros(get_exp_array(adata, li[0]).shape)
    for i in li:
        total += get_exp_array(adata, i)
    if cmap is not None:
        sns.heatmap(total, cmap=cmap, vmax=vmax)
    else:
        sns.heatmap(total, vmax=vmax)
