from pathlib import Path
from PIL import Image
from tempfile import TemporaryDirectory

from ml_model.inference.validator import (
    ImageValidator,
    InvalidImageError,
)

with TemporaryDirectory() as temp_dir:
    p = Path(temp_dir)

    small = p / "small.jpg"
    exact = p / "exact.jpg"

    # 199x200: must be rejected by the 200x200 minimum.
    Image.new(
        "RGB",
        (199, 200),
        (120, 180, 80),
    ).save(small)

    # 200x200: meets the minimum dimension.
    Image.new(
        "RGB",
        (200, 200),
        (120, 180, 80),
    ).save(exact)

    try:
        ImageValidator.validate(str(small))
        result_small = "ACCEPTED (FAIL)"
    except InvalidImageError as error:
        result_small = f"REJECTED (PASS): {error}"

    try:
        ImageValidator.validate(str(exact))
        result_exact = "ACCEPTED (dimension PASS)"
    except InvalidImageError as error:
        result_exact = f"REJECTED: {error}"

    print("========================================")
    print("IMAGE DIMENSION BOUNDARY TEST")
    print("========================================")
    print()
    print("199x200:", result_small)
    print("200x200:", result_exact)
    print()
    print("Expected:")
    print("199x200 -> REJECTED")
    print("200x200 -> Dimension requirement satisfied")