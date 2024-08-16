'''Convolution 1D Nearest Neighbor Layer for spatially located'''

'''
Features: 
    - For K nearest neighbors, K must be same as stride
    - Calculate Distance/Similarity Matrix with matrix and matrix2 
    - Pixel Shuffle/Unshuffle Layer with Scale Factor
    - Conv1d Layer with Kernel Size, Stride, Padding
'''

import torch 
import torch.nn as nn
import torch.nn.functional as F
from pixelshuffle import PixelShuffle1D, PixelUnshuffle1D
import faiss


class Conv1d_NN_spatial(nn.Module): 
    def __init__(self, in_channels, out_channels, K=3, stride=3, padding=0, 
                 shuffle_pattern='N/A', shuffle_scale=2, 
                 samples='all', 
                 magnitude_type='distance'): 
        
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.K = K
        self.stride = stride 
        self.padding = padding
        self.shuffle_pattern = shuffle_pattern 
        self.shuffle_scale = shuffle_scale
        
        self.samples = int(samples) if samples != 'all' else samples # Number of samples to consider
        self.magnitude_type = magnitude_type # Nearest Neighbor based on Distance or Similarity 
        self.maximum = True if self.magnitude_type == 'similarity' else False # Minimum or Maximum for Distance or Similarity
        
        # Unshuffle layer 
        self.unshuffle_layer = PixelUnshuffle1D(downscale_factor=self.shuffle_scale)
        
        # Shuffle Layer 
        self.shuffle_layer = PixelShuffle1D(upscale_factor=self.shuffle_scale)
                
        # Conv1d Layer
        self.in_channels = in_channels * shuffle_scale if self.shuffle_pattern in ["BA", "B"] else in_channels
        self.out_channels = out_channels * shuffle_scale if self.shuffle_pattern in ["BA", "A"] else out_channels

        # Conv1d Layer 
        self.conv1d_layer = nn.Conv1d(in_channels=self.in_channels, 
                                      out_channels=self.out_channels, 
                                      kernel_size=self.K, 
                                      stride=self.stride, 
                                      padding=self.padding)

        self.relu = nn.ReLU()

    def forward(self, x, y): 

        # Unshuffle Layer 
        if self.shuffle_pattern in ["B", "BA"]:
            x1 = self.unshuffle_layer(x)
        else:
            x1 = x
            
        if self.magnitude_type == 'distance':
            matrix_magnitude = self.calculate_distance_matrix_N(x1, y)
        elif self.magnitude_type == 'similarity':
            matrix_magnitude = self.calculate_similarity_matrix_N(x1, y)        
        
        prime = self.prime_vmap_2d_N(x1, matrix_magnitude, self.K, self.maximum)
        
        # Conv1d Layer
        x2 = self.conv1d_layer(prime)
        
        # ReLU Activation
        x3 = self.relu(x2)
        
        # Shuffle Layer
        if self.shuffle_pattern in ["A", "BA"]:
            x4 = self.shuffle_layer(x3)
        else:
            x4 = x3
        
        return x4
        
    ### N Samples ### 
    '''Distance Matrix Calculations for N Sample'''
    @staticmethod 
    def calculate_distance_matrix_N(matrix, matrix_sample):
        '''Calculate distance matrix between two input matrices''' 
        norm_squared = torch.sum(matrix ** 2, dim=1, keepdim=True).permute(0, 2, 1)
        norm_squared_sample = torch.sum(matrix_sample ** 2, dim=1, keepdim=True).transpose(2, 1).permute(0, 2, 1)
        dot_product = torch.bmm(matrix.transpose(2, 1), matrix_sample)
        dist_matrix = norm_squared + norm_squared_sample - 2 * dot_product
        return torch.sqrt(dist_matrix)
        
    '''Similarity Matrix Calculations for N Sample'''
    @staticmethod
    def calculate_similarity_matrix_N(matrix, matrix_sample): 
        normalized_matrix = F.normalize(matrix, p=2, dim=1) # p=2 (L2 Norm - Euclidean Distance), dim=1 (across the channels)
        normalized_matrix_sample = F.normalize(matrix_sample, p=2, dim=1)
        similarity_matrix = dot_product = torch.bmm(normalized_matrix.transpose(2, 1), normalized_matrix_sample)
        return similarity_matrix

    '''N Sample Methods'''
    @staticmethod
    def prime_vmap_2d_N(matrix, magnitude_matrix, num_nearest_neighbors, maximum): 
        '''Vectorization / Vmap Implementation for Nearest Neighbor Tensor 2D'''
        batched_process = torch.vmap(Conv1d_NN_spatial.process_batch_N, in_dims=(0, 0, None), out_dims=0)
        prime = batched_process(matrix, magnitude_matrix, num_nearest_neighbors, flatten=True, maximum=maximum)
        return prime 
    
    @staticmethod
    def prime_vmap_3d_N(matrix, magnitude_matrix, num_nearest_neighbors, maximum): 
        '''Vectorization / Vmap Implementation for Nearest Neighbor Tensor 3D'''
        batched_process = torch.vmap(Conv1d_NN_spatial.process_batch_N, in_dims=(0, 0, None), out_dims=0)
        prime = batched_process(matrix, magnitude_matrix, num_nearest_neighbors, flatten=False, maximum=maximum)
        return prime
    
    @staticmethod 
    def process_batch_N(matrix, magnitude_matrix, num_nearest_neighbors, flatten, maximum): 
        # Process the batch of matrices
        ind = torch.topk(magnitude_matrix, num_nearest_neighbors, largest=maximum).indices 
        neigh = matrix[:, ind]
        if flatten: 
            reshape = torch.flatten(neigh, start_dim=1)
            return reshape
        return neigh
    
