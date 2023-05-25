import anndata
import multiprocessing

import seaborn as sns
import matplotlib.pyplot as plt

from numba import njit
from scipy import sparse
from sklearn import mixture
from util import array_to_list
from Algorithm.Algorithm import *


def distribution_distance(gmm1, gmm2, method='hellinger'):
    """
    Calculates the distance between gmm1 and gmm2
    :param method:
    :type method:
    :param gmm1: first GMM model
    :type gmm1:
    :param gmm2: second GMM model
    :type gmm2:
    :return: Distance between gmm1 and gmm2
    :rtype:
    """
    gmm1_weights = gmm1.weights_
    gmm1_means = gmm1.means_
    gmm1_covs = gmm1.covariances_
    gmm2_weights = gmm2.weights_
    gmm2_means = gmm2.means_
    gmm2_covs = gmm2.covariances_
    n_components = gmm1_weights.size
    # calculate the distance
    distance_array = np.zeros((n_components, n_components))
    # TODO: other distance metrics
    if method == 'hellinger':
        for i in range(n_components):
            for j in range(n_components):
                distance_array[i, j] = get_hellinger_distance(gmm1_covs[i], gmm1_means[i], gmm2_covs[j], gmm2_means[j])
        distance = linear_sum(distance_array)
    return distance


def get_bh_distance(gmm1_covs, gmm1_means, gmm2_covs, gmm2_means):
    mean_cov = (gmm1_covs + gmm2_covs) / 2
    mean_cov_det = np.linalg.det(mean_cov)
    mean_cov_inv = np.linalg.inv(mean_cov)
    means_diff = gmm1_means - gmm2_means
    first_term = (means_diff.T @ mean_cov_inv @ means_diff) / 8
    second_term = np.log(mean_cov_det / (np.sqrt(np.linalg.det(gmm1_covs) * np.linalg.det(gmm2_covs)))) / 2
    result = first_term + second_term
    return result


@njit
def get_hellinger_distance(gmm1_covs, gmm1_means, gmm2_covs, gmm2_means):
    """
    Calculates the distance between two GMM models by hellinger distance.

    **Hellinger distance** (closely related to, although different from, the Bhattacharyya distance) is used to quantify
    the similarity between two probability distributions.

    Ref:
     - https://en.wikipedia.org/wiki/Hellinger_distance
    :param gmm1_covs: first gmm covariances
    :type gmm1_covs: np.Array_
    :param gmm1_means: first gmm means
    :type gmm1_means: Array
    :param gmm2_covs: second gmm covariances
    :type gmm2_covs: Array
    :param gmm2_means: second gmm means
    :type gmm2_means: Array
    :return: distance between two GMM models
    :rtype: np.float
    """
    mean_cov = (gmm1_covs + gmm2_covs) / 2
    mean_cov_det = np.linalg.det(mean_cov)
    mean_cov_inv = np.linalg.inv(mean_cov)
    gmm1_cov_det = np.linalg.det(gmm1_covs)
    gmm2_cov_det = np.linalg.det(gmm2_covs)
    means_diff = gmm1_means - gmm2_means
    first_term = np.exp(-(means_diff.T @ mean_cov_inv @ means_diff) / 8)
    second_term = ((np.power(gmm1_cov_det, 0.25)) * np.power(gmm2_cov_det, 0.25)) / np.sqrt(mean_cov_det)
    hellinger_distance = np.sqrt(np.abs(1 - first_term * second_term))
    return hellinger_distance


def fit_gmm(adata: anndata,
            gene_name: str,
            n_comp: int = 5,
            max_iter: int = 1000) -> mixture.GaussianMixture:
    """
    Representation of a Gaussian mixture model probability distribution.
    Estimate the parameters of a Gaussian mixture distribution.

    Estimate model parameters with the EM algorithm.
    :param adata: Anndata of spatial data
    :type adata: Anndata
    :param gene_name: The gene name to fit
    :type gene_name: str
    :param n_comp: The number of mixture components.
    :type n_comp: int
    :param max_iter: The number of EM iterations to perform.
    :type max_iter: int
    :return: The fitted mixture.
    :rtype: GaussianMixture
    """
    data = np.array(adata[:, adata.var_names == gene_name].X.todense())
    sparse_matrix = sparse.coo_matrix((data[:, 0], (np.array(adata.obs['fig_x']), np.array(adata.obs['fig_y']))))
    arr = np.array(sparse_matrix.todense(), dtype=np.int32)
    result = array_to_list(arr)
    gmm = mixture.GaussianMixture(n_components=10, max_iter=200)
    gmm.fit(result)


def fit_gmms(adata: anndata,
             gene_name_list: list,
             n_comp: int = 5,
             max_iter: int = 1000,
             thread: int = 4) -> dict:
    """
    Same as fit_gmm, use multiple threads.
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


def _fit_worker(shared_dict, adata, gene_name, n_comp, max_iter):
    shared_dict[gene_name] = fit_gmm(adata, gene_name, n_comp, max_iter)


def view_gmm(gmm, plot_type: str = '3d'):
    """
    View the fitted GMM model.
    :param gmm: fitted GMM model by sklearn.mixture.GaussianMixture
    :type gmm: sklearn.mixture.GaussianMixture
    :param plot_type: 3d or 2d are accepted
    :type plot_type: str
    """
    x = np.linspace(0, 30000, 100)
    y = np.linspace(0, 30000, 100)
    x_range, y_range = np.meshgrid(x, y)
    x_y = np.column_stack([x_range.flat, y_range.flat])
    # calculate the density
    density = gmm.score_samples(x_y)
    density = density.reshape(x_range.shape)
    if plot_type == '3d':
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(x_range, y_range, density, cmap='viridis')
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('pdf')
        ax.set_box_aspect([2, 2, 1])
        ax.set_title('Probability Density Function Surface')
        # ax.grid(False)
        ax.view_init(elev=30, azim=235)
        plt.show()
    if plot_type == '2d':
        sns.heatmap(np.exp(density))
        plt.show()


def get_pattern():
    pass
