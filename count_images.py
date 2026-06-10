# count_images.py

import os

dataset_path = "dataset"

for folder in os.listdir(dataset_path):
    path = os.path.join(dataset_path, folder)

    if os.path.isdir(path):
        print(folder, len(os.listdir(path)))