def reference_scale(known_length_m: float, pixel_length: float)->float:
    if known_length_m <= 0 or pixel_length <= 0:
        raise ValueError("lengths must be positive")
    return pixel_length/known_length_m

def px_to_m(pixel_value: float, px_per_m:float) -> float:
    return pixel_value/px_per_m