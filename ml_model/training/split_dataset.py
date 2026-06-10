import os
import shutil
import random
from pathlib import Path

SOURCE_DIR = "../dataset"

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

for class_name in os.listdir(SOURCE_DIR):

    class_path = os.path.join(SOURCE_DIR, class_name)

    if not os.path.isdir(class_path):
        continue

    images = os.listdir(class_path)
    random.shuffle(images)

    total = len(images)

    train_count = int(total * TRAIN_RATIO)
    val_count = int(total * VAL_RATIO)

    train_images = images[:train_count]
    val_images = images[train_count:train_count + val_count]
    test_images = images[train_count + val_count:]

    for split_name, split_images in {
        "train": train_images,
        "validation": val_images,
        "test": test_images
    }.items():

        dest_folder = os.path.join(
            SOURCE_DIR,
            split_name,
            class_name
        )

        Path(dest_folder).mkdir(
            parents=True,
            exist_ok=True
        )

        for image in split_images:

            src = os.path.join(class_path, image)
            dst = os.path.join(dest_folder, image)

            shutil.copy2(src, dst)

print("Dataset split completed!")