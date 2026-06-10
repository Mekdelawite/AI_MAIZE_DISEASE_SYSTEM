import os

for split in ["train", "validation", "test"]:
    print(f"\n{split.upper()}")

    split_path = f"dataset/{split}"

    for cls in os.listdir(split_path):
        count = len(
            os.listdir(
                os.path.join(split_path, cls)
            )
        )

        print(cls, count)