from utils.freespace_generation_new import generate_free_space
import numpy as np
import torch
import argparse
import os
import pandas as pd
from plyfile import PlyData
from tqdm import tqdm
from utils.ground_plane import ransac_1d

def generate_free_space_all_scenes(dataset_dir, floor_height):

    datasets = ['ARKitScenes', 'Scannet', 'HM3D', 'Matterport', '3RScan', 'Unity']
    for dataset in datasets:
        pbar = tqdm(os.listdir(os.path.join(dataset_dir, dataset)))
        for scene in pbar:
            pbar.set_description(scene)
            scene_path = os.path.join(dataset_dir, dataset, scene)

            object_result = pd.read_csv(os.path.join(scene_path, f'{scene}_object_result.csv'))
            region_result = pd.read_csv(os.path.join(scene_path, f'{scene}_region_result.csv'))

            object_split = np.load(os.path.join(scene_path, f'{scene}_object_split.npy'))
            region_ids_and_split = np.load(os.path.join(scene_path, f'{scene}_region_split.npy'))

            pcd_file = PlyData.read(os.path.join(scene_path, f'{scene}_pc_result.ply'))

            points = np.vstack([pcd_file['vertex'].data[prop] for prop in ['x', 'y', 'z']]).T
            rgb = np.vstack([pcd_file['vertex'].data[prop] for prop in ['red', 'green', 'blue']]).T

            region_split = region_ids_and_split[:-1, 1]
            region_ids = region_ids_and_split[:, 0]

            region_pc_split = np.split(points, region_split)

            region_pc_dict = {region_id: pc for region_id, pc in zip(region_ids, region_pc_split)}

            if dataset == 'ARKitScenes':

                floor_sizes = []

                for i, row in region_result.iterrows():

                    candidate_points_filter = points[:, 2] < (row['region_bbox_cz'] - row['region_bbox_zlength'] / 4)
                    candidate_points_z = points[candidate_points_filter, 2]

                    floor_cz, inliers = ransac_1d(candidate_points_z, 0.1, 100)

                    print(floor_cz, row['region_bbox_cz'] - row['region_bbox_zlength'] / 2)

                    floor_sizes.append([
                        row['region_bbox_cx'],
                        row['region_bbox_cy'],
                        floor_cz,
                        row['region_bbox_xlength'],
                        row['region_bbox_ylength'],
                        floor_height,
                        row['region_bbox_heading'],
                        row['region_id'],
                        ])
            elif dataset == 'Unity':

                floor_sizes = []

                for i, row in region_result.iterrows():

                    # Option 1: Cropping everything in region box, then RANSAC
                    # Option 2: Checking which floors lie in which region box
                    candidate_points_filter = points[:, 0] < (row['region_bbox_cx'] + row['region_bbox_xlength'] / 2)
                    candidate_points_filter &= points[:, 0] > (row['region_bbox_cx'] - row['region_bbox_xlength'] / 2)
                    candidate_points_filter &= points[:, 1] < (row['region_bbox_cy'] + row['region_bbox_ylength'] / 2)
                    candidate_points_filter &= points[:, 1] > (row['region_bbox_cy'] - row['region_bbox_ylength'] / 2)
                    candidate_points_filter &= points[:, 2] < (row['region_bbox_cz'] + row['region_bbox_zlength'] / 2 - floor_height)
                    candidate_points_filter &= points[:, 2] > (row['region_bbox_cz'] - row['region_bbox_zlength'] / 2 - floor_height)

                    candidate_points_z = points[candidate_points_filter, 2]

                    floor_cz, inliers = ransac_1d(candidate_points_z, 0.1, 100)

                    print(floor_cz, row['region_id'])

                    floor_sizes.append([
                        row['region_bbox_cx'],
                        row['region_bbox_cy'],
                        floor_cz,
                        row['region_bbox_xlength'],
                        row['region_bbox_ylength'],
                        floor_height,
                        row['region_bbox_heading'],
                        row['region_id'],
                        ])
            else:
                floors_df = object_result[object_result['nyu_label'] == 'floor']

                floor_sizes = [[
                    row['object_bbox_cx'],
                    row['object_bbox_cy'],
                    row['object_bbox_cz'],
                    row['object_bbox_xlength'],
                    row['object_bbox_ylength'],
                    floor_height,
                    row['object_bbox_heading'],
                    row['region_id'],
                    ] for i, row in floors_df.iterrows()]
                
                print(floor_sizes)

            generate_free_space(scene_path, scene, region_ids, region_pc_dict, floor_sizes)
                

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset_dir', default="/home/navigation/Dataset/VLA_Dataset")
    parser.add_argument('--floor_height', default=0.1)

    args = parser.parse_args()
    
    generate_free_space_all_scenes(
        args.dataset_dir,
        args.floor_height
    )