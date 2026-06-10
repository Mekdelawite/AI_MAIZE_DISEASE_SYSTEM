import os

for split in ["train", "validation", "test"]:
    print(f"\n{split.upper()}")

    path = f"dataset/{split}"

    for cls in os.listdir(path):
        count = len(os.listdir(os.path.join(path, cls)))
        print(f"{cls}: {count}")