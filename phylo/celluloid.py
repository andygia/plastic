"""
For more informations on the contents of this module:
- help(celluloid.GenotypeMatrix)
- help(celluloid.cluster_mutations)

--------

Module that exposes the clustering algorithm presented in the celluloid
research paper. Here's an example workflow.

from phylo import celluloid as cl

to_cluster = cl.GenotypeMatrix.from_files('to_cluster.txt', mutations_file = 'mutations.txt')
# Reduce the size of the input down to 50 to speed up some complex computation
# (for instance SASC tree inference)
clustered = cl.cluster_mutations(to_cluster, k = 50)

# Get the clustered mutations as comma separated lists of simple mutations
muts = clustered.mutations()

# Save the matrix or use it for some intensive computation
"""


from .core.genotypematrix import GenotypeMatrix
import numpy as np
from kmodes.kmodes import KModes
from collections import defaultdict


def _conflict_dissim(a, b, **_) :
    v = np.vectorize(lambda ai, bi : ai != 2 and bi != 2 and ai != bi)
    return np.sum(v(a,b), axis = 1)

def cluster_mutations(
    genotype_matrix,
    k,
    number_of_iterations = 10,
    verbose = False
):
    """
    Clusters the mutations in a genotype matrix by applying kmodes

    Parameters:
        genotype_matrix(GenotypeMatrix):
            A matrix representing the results of single-cell sequencing.
        k(int):
            The number of clustered mutations in the output matrix.
            Note that empty clusters will be discarded after clustering.
        number_of_iterations(int):
            The number of iterations in the clustering process.
        verbose (bool)

    Returns:
        GenotypeMatrix:
            The result of the clustering process. Each column in the matrix
            will be the centroid of a non-empty cluster, and will be labeled with
            a comma-separated list of the labels of the mutations within the cluster.
            Cell labels are left unaltered.
    """

    if int(k) != k or k < 1:
        raise ValueError(f'the number of clusters must be a positive integer, but {k} is not.')
    if int(number_of_iterations) != number_of_iterations or number_of_iterations < 1:
        raise ValueError(f'the number of iterations must be a positive integer, but {number_of_iterations} is not.')

    mutations_as_points = np.array(genotype_matrix.matrix(), dtype = 'int').transpose()
    mutation_labels = genotype_matrix.mutation_labels
    
    km = KModes(
            n_clusters = k,
            cat_dissim = _conflict_dissim,
            init = 'huang',
            n_init = number_of_iterations,
            verbose = 1 if verbose else 0
        )

    clusters = km.fit_predict(mutations_as_points)

    # Each cluster will be labeled with the labels of its components.
    clusters_of_mutations = km.labels_
    clustered_mutation_labels = defaultdict(list)
    for mutation_label, mutation_cluster in zip(mutation_labels, clusters_of_mutations):
        clustered_mutation_labels[mutation_cluster].append(mutation_label)

    nonempty_clusters = clustered_mutation_labels.keys()

    # build the output matrix and the mutation labels as strings
    cluster_centroids = km.cluster_centroids_
    clustered_mutation_labels_strings = [','.join(clustered_mutation_labels[cluster_id]) for cluster_id in sorted(nonempty_clusters)]
    out_matrix = [cluster_centroids[cluster_id] for cluster_id in sorted(nonempty_clusters)]
    
    # the matrix needs to be transposed back to its original orientation
    out_matrix = np.array(out_matrix).transpose()

    return GenotypeMatrix(out_matrix, cell_labels = genotype_matrix.cell_labels, mutation_labels = clustered_mutation_labels_strings)
