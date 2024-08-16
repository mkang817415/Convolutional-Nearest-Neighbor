'''Nearest Neighbor Tensor (NNT) Class'''

import torch 
import torch.nn as nn 
from functorch import vmap

class NNT: # Nearest Neighbor  
    def __init__(self, matrix, num_nearest_neighbors):
        self.matrix = matrix.to(torch.float32) 
        
        self.num_nearest_neighbors = int(num_nearest_neighbors)
        
        self.dist_matrix_vectorized = self.matrix
                
        self.prime_vmap_2d = self.prime_vmap_2d()
        
        # self.prime_vmap_3d = self.prime_vmap_3d()
        
    '''Getters for the NNT object'''
    @property
    def matrix(self): 
        '''Returns the matrix of the NNT object'''
        return self._matrix
    @property
    def num_nearest_neighbors(self): 
        '''Returns the number of nearest neighbors to be used in the convolution matrix'''
        return self._num_nearest_neighbors

    @property 
    def dist_matrix_vectorized(self): 
        '''Returns the distance matrix (vectorized)of the NNT object'''
        return self._dist_matrix_vectorized

    
    @property 
    def prime_vmap_2d(self): 
        '''Returns the convolution matrix of the NNT object'''
        return self._prime_vmap
    
    # @property
    # def prime_vmap_3d(self): 
    #     '''Returns the convolution matrix of the NNT object'''
    #     return self._prime_vmap_3d    
    
    '''Setters for the NNT object'''
    @matrix.setter
    def matrix(self, value): 
        # Check if the matrix is a torch.Tensor
        if not isinstance(value, torch.Tensor): 
            raise ValueError("Matrix must be a torch.Tensor")
        self._matrix = value
        
    @num_nearest_neighbors.setter
    def num_nearest_neighbors(self, value): 
        # Check if the number of nearest neighbors is an integer
        if not isinstance(value, int): 
            raise ValueError("Number of nearest neighbors must be an integer")
        self._num_nearest_neighbors = value
        
    @dist_matrix_vectorized.setter
    def dist_matrix_vectorized(self, matrix):
        '''Set the distance matrix of the NNT object'''
        self._dist_matrix_vectorized = self.calculate_distance_matrix(matrix)

        
    def prime_vmap_2d(self): 
        # Vectorization / Vmap Implementation
        batched_process = torch.vmap(self.process_batch, in_dims=(0, 0, None), out_dims=0)
        
        prime = batched_process(self.matrix, self.dist_matrix_vectorized, self.num_nearest_neighbors, flatten=True)
        return prime

    # def prime_vmap_3d(self): 
    #     # Vectorization / Vmap Implementation
    #     batched_process = torch.vmap(self.process_batch, in_dims=(0, 0, None), out_dims=0)
        
    #     prime = batched_process(self.matrix, self.dist_matrix_vectorized, self.num_nearest_neighbors, flatten=False)
    #     return prime

    
    '''Utility Functions for the NNT object'''
    @staticmethod
    def process_batch(matrix, dist_matrix, num_nearest_neighbors, flatten=True): 
        '''Process the batch of matrices'''
        ind = torch.topk(dist_matrix, num_nearest_neighbors, largest=False).indices
        neigh = matrix[:, ind]
        if flatten:
            reshape = torch.flatten(neigh, start_dim=1)
            return reshape
        else: 
            return neigh
    
    @staticmethod
    def calculate_dot_product(matrix): 
        '''Calculate the dot product of the matrix'''
        return torch.bmm(matrix.transpose(2, 1), matrix)
    

    def calculate_distance_matrix(self, matrix): 
        norm_squared = torch.sum(matrix ** 2, dim=1, keepdim=True)
        dot_product = self.calculate_dot_product(matrix)   
        dist_matrix = norm_squared + norm_squared.transpose(2, 1) - 2 * dot_product
        return torch.sqrt(dist_matrix)
        
    
        
        
        
'''EXAMPLE USAGE'''
# ex = torch.rand(32, 3, 40) # 3 samples, 2 channels, 10 tokens
#                           # 3 batches, 2 sentences, 10 words
# closest_neighbors = 3 # 3 closest neighbors
# nnt = NNT(ex, closest_neighbors) 
# print(nnt.dist_matrix_vectorized.shape)
# print("-"*50)
# print(nnt.prime_vmap_2d.shape)
# print("-"*50)
