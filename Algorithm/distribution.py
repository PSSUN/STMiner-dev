import multiprocessing
import warnings

import anndata
import matplotlib.pyplot as plt
import scanpy as sc
import seaborn as sns
from numba import njit
from sklearn import mixture
from tqdm import tqdm

from Algorithm.algorithm import *
from Algorithm.distance import get_exp_array

# Ignore the unnecessary warnings
warnings.filterwarnings("ignore")


def get_gmm(matrix):
    arr = np.array(matrix, dtype=np.int32)
    result = _array_to_list(arr)
    gmm = mixture.GaussianMixture(n_components=10, max_iter=200).fit(result)
    return gmm


def fit_gmm_bic(adata: anndata,
                gene_name: str,
                min_n_comp: int = 2,
                max_n_comp: int = 10,
                max_iter: int = 200):
    """
    Representation of a Gaussian mixture model probability distribution.
    Estimate the parameters of a Gaussian mixture distribution.

    Estimate model parameters with the EM algorithm.
    :param max_n_comp:
    :type max_n_comp:
    :param adata: Anndata of spatial data
    :type adata: Anndata
    :param gene_name: The gene name to fit
    :type gene_name: str
    :param min_n_comp: The min number of mixture components.
    :type min_n_comp: int
    :param max_iter: The number of EM iterations to perform.
    :type max_iter: int
    :return: The number of components and the fitted mixture.
    :rtype: GaussianMixture
    """
    dense_array = get_exp_array(adata, gene_name)
    result = np.array(_array_to_list(dense_array))
    # Number of unique center must be larger than the number of components.
    if len(set(map(tuple, result))) > min_n_comp:
        bic_list = []
        gmm_list = []
        for i in range(min_n_comp, max_n_comp):
            gmm = mixture.GaussianMixture(n_components=i, max_iter=max_iter)
            gmm.fit(result)
            bic = gmm.bic(result)
            bic_list.append(bic)
            gmm_list.append(gmm)
            # print(str(i) + ": " + str(bic))
        index = bic_list.index(min(bic_list))
        n_comp = min_n_comp + index
        return n_comp, gmm_list[index]
    else:
        return None


def fit_gmm(adata: anndata,
            gene_name: str,
            n_comp: int = 2,
            cut: bool = False,
            binary: bool = False,
            threshold: int = 95,
            max_iter: int = 200,
            reg_covar=1e-3):
    """
    Representation of a Gaussian mixture model probability distribution.
    Estimate the parameters of a Gaussian mixture distribution.

    Estimate model parameters with the EM algorithm.

    :param cut:
    :type cut:
    :param threshold:
    :type threshold:
    :param binary:
    :type binary:
    :param reg_covar:
    :type reg_covar:
    :param adata: Anndata of spatial data
    :type adata: Anndata
    :param gene_name: The gene name to fit
    :type gene_name: str
    :param n_comp: The number of mixture components.
    :type n_comp: int
    :param max_iter: The number of EM iterations to perform.
    :type max_iter: int
    :return: The number of components and the fitted mixture.
    :rtype: GaussianMixture
    """
    dense_array = get_exp_array(adata, gene_name)
    if binary:
        if threshold > 100 | threshold < 0:
            print('Warning: the threshold is illegal, the value in [0, 100] is accepted.')
            threshold = 100
        binary_arr = np.where(dense_array > np.percentile(dense_array, threshold), 1, 0)
        result = _array_to_list(binary_arr)
    else:
        if cut:
            dense_array[dense_array < np.percentile(dense_array, threshold)] = 0
        result = _array_to_list(dense_array)
    # Number of unique center must be larger than the number of components.
    if len(set(map(tuple, result))) >= n_comp:
        gmm = mixture.GaussianMixture(n_components=n_comp, max_iter=max_iter, reg_covar=reg_covar)
        gmm.fit(result)
        return gmm
    else:
        return None


def fit_gmms(adata,
             gene_name_list,
             n_comp=5,
             binary=False,
             threshold=95,
             max_iter=100,
             reg_covar=1e-3):
    """
    Same as fit_gmm_bic, accepts a list of gene name.
    Representation of a Gaussian mixture model probability distribution.
    Estimate the parameters of a Gaussian mixture distribution.
    :param threshold:
    :type threshold:
    :param binary:
    :type binary:
    :param reg_covar:
    :type reg_covar:
    :param adata: Anndata of spatial data
    :type adata: Anndata
    :param gene_name_list: The python list, each element is a gene name in adata.
    :type gene_name_list: list
    :param n_comp: The number of mixture components.
    :type n_comp: int
    :param max_iter: The number of EM iterations to perform.
    :type max_iter: int
    :return: A Python dict of given genes list, key is gene name, value is GMM object.
    :return:
    :rtype: dict
    """
    gmm_dict = {}
    dropped_genes_count = 0
    for gene_id in tqdm(gene_name_list,
                        desc='Fitting...',
                        colour='green'):
        try:
            fit_result = fit_gmm(adata,
                                 gene_id,
                                 n_comp=n_comp,
                                 binary=binary,
                                 threshold=threshold,
                                 max_iter=max_iter,
                                 reg_covar=reg_covar)
            if fit_result is not None:
                gmm_dict[gene_id] = fit_result
            else:
                dropped_genes_count += 1
        except Exception as e:
            error_msg = str(e)
            raise ValueError("Gene id: " + gene_id + "\nError: " + error_msg)
    if dropped_genes_count > 0:
        print('Number of dropped genes: ' + str(dropped_genes_count))
    return gmm_dict


def fit_gmms_bic(adata,
                 gene_name_list: list,
                 min_n_comp: int = 5,
                 max_n_comp: int = 10,
                 max_iter: int = 100):
    """
    Same as fit_gmm_bic, accepts a list of gene name.
    Representation of a Gaussian mixture model probability distribution.
    Estimate the parameters of a Gaussian mixture distribution.
    :param max_n_comp:
    :type max_n_comp: int
    :param min_n_comp:
    :type min_n_comp: int
    :param adata: Anndata of spatial data
    :type adata: Anndata
    :param gene_name_list: The python list, each element is a gene name in adata.
    :type gene_name_list: list
    :param max_iter: The number of EM iterations to perform.
    :type max_iter: int
    :return: A Python dict of given genes list, key is gene name, value is GMM object.
    :return: gmm_dict and comp_dict
    :rtype: dict
    """
    gmm_dict = {}
    comp_dict = {}
    for gene_id in tqdm(gene_name_list, desc='Processing ...'):
        try:
            n_comp, fit_result = fit_gmm_bic(adata,
                                             gene_id,
                                             min_n_comp=min_n_comp,
                                             max_n_comp=max_n_comp,
                                             max_iter=max_iter)
            gmm_dict[gene_id] = fit_result
            if n_comp not in comp_dict.keys():
                comp_dict[n_comp] = []
                comp_dict[n_comp].append(gene_id)
            else:
                comp_dict[n_comp].append(gene_id)
        except Exception as e:
            error_msg = str(e)
            raise ValueError("Gene id: " + gene_id + "\nError: " + error_msg)
    return gmm_dict, comp_dict


def fit_gmms_multiprocessing(adata: anndata,
                             gene_name_list: list,
                             n_comp: int = 5,
                             max_iter: int = 1000,
                             thread: int = 4) -> dict:
    """
    Same as fit_gmm_bic, use multiple threads.
    Representation of a Gaussian mixture model probability distribution.
    Estimate the parameters of a Gaussian mixture distribution.

    Estimate model parameters with the EM algorithm.
    :param adata: Anndata of spatial data
    :type adata: Anndata
    :param gene_name_list: The genes list to fit
    :type gene_name_list: list
    :param n_comp: The number of mixture components.
    :type n_comp: int
    :param max_iter: The number of EM iterations to perform.
    :type max_iter: int
    :param thread: The number of threads to use, default:4
    :type thread: int
    :return: A Python dict of given genes list, key is gene name, value is GMM object.
    :rtype: dict
    """
    manager = multiprocessing.Manager()
    shared_dict = manager.dict()
    pool = multiprocessing.Pool(processes=thread)
    for i in gene_name_list:
        pool.apply_async(_fit_worker, args=(shared_dict, adata, i, n_comp, max_iter))
    pool.close()
    pool.join()
    normal_dict = dict(shared_dict)
    return normal_dict


def view_gmm(gmm, scope, cmap=None, bin_count=None):
    """
    View the fitted GMM model.
    :param cmap:
    :type cmap:
    :param bin_count:
    :type bin_count:
    :param scope:
    :type scope:
    :param gmm: fitted GMM model by sklearn.mixture.GaussianMixture
    :type gmm: sklearn.mixture.GaussianMixture
    """
    start = scope[0]
    end = scope[1]
    if bin_count is None:
        num = end - start
    else:
        num = bin_count
    x = np.linspace(start, end, num)
    y = np.linspace(start, end, num)
    x_range, y_range = np.meshgrid(x, y)
    x_y = np.column_stack([x_range.flat, y_range.flat])
    # calculate the density
    density = gmm.score_samples(x_y)
    density = density.reshape(x_range.shape)
    if cmap is not None:
        sns.heatmap(np.exp(density), cmap=cmap)
    else:
        sns.heatmap(np.exp(density))
    plt.show()


def view_pattern(adata, gene_list, size=6):
    """
    Plot expression pattern of given genes.
    :param adata:
    :type adata:
    :param gene_list:
    :type gene_list:
    :param size:
    :type size:
    """
    tmp = adata[:, gene_list]
    sc.pl.scatter(tmp,
                  x='x',
                  y='y',
                  color='log1p_n_genes_by_counts',
                  size=size)


@njit
def _mean_square_error(matrix1, matrix2):
    """

    :param matrix1:
    :type matrix1:
    :param matrix2:
    :type matrix2:
    :return:
    :rtype:
    """
    if matrix1.shape != matrix2.shape:
        raise ValueError("Dimension mismatch")
    diff = matrix1 - matrix2
    squared_diff = np.square(diff)
    mse = np.mean(squared_diff)
    return mse


def _fit_worker(shared_dict, adata, gene_name, n_comp, max_iter):
    shared_dict[gene_name] = fit_gmm_bic(adata, gene_name, n_comp, max_iter)


def _array_to_list(matrix) -> np.array:
    coords = np.column_stack(np.where(matrix > 0))
    counts = matrix[matrix > 0].flatten()
    result = np.repeat(coords, counts, axis=0)
    return result


class GMM:
    def __init__(self, n):
        self.means_ = np.zeros((n, 2))
        self.covariances_ = np.zeros((n, 2, 2))
        self.weights_ = np.zeros((n,))

    def set_mean(self, means):
        self.means_ = means

    def set_covariances(self, covariances):
        self.covariances_ = covariances

    def set_weights(self, weights):
        self.weights_ = weights
