from __future__ import annotations

import math


def chainage_from_meters(meters: int) -> str:
    """Format integer meters into chainage like 0+000, 1+250."""
    if meters < 0:
        raise ValueError("meters must be >= 0")
    km = meters // 1000
    m = meters % 1000
    return f"{km}+{m:03d}"


def generate_stretch_segments(
    *,
    total_length_m: int,
    number_of_stretches: int | None = None,
    stretch_length_m: int | None = None,
) -> list[dict]:
    """Generate sequential, non-overlapping stretch segments.

    Rules:
    - Either number_of_stretches OR stretch_length_m must be provided
    - Last stretch auto-adjusts for remainder
    """
    if total_length_m <= 0:
        raise ValueError("total_length_m must be > 0")

    if (number_of_stretches is None) == (stretch_length_m is None):
        raise ValueError("Provide exactly one of number_of_stretches or stretch_length_m")

    segments: list[tuple[int, int]] = []

    if number_of_stretches is not None:
        if number_of_stretches <= 0:
            raise ValueError("number_of_stretches must be > 0")
        base_len = total_length_m // number_of_stretches
        if base_len <= 0:
            raise ValueError("Too many stretches for given total length")
        remainder = total_length_m % number_of_stretches

        start = 0
        for idx in range(1, number_of_stretches + 1):
            length = base_len
            if idx == number_of_stretches:
                length += remainder
            end = start + length
            segments.append((start, end))
            start = end

    if stretch_length_m is not None:
        if stretch_length_m <= 0:
            raise ValueError("stretch_length_m must be > 0")
        count = int(math.ceil(total_length_m / stretch_length_m))

        start = 0
        for idx in range(1, count + 1):
            end = min(total_length_m, start + stretch_length_m)
            segments.append((start, end))
            start = end

    result: list[dict] = []
    for i, (start_m, end_m) in enumerate(segments, start=1):
        length_m = end_m - start_m
        start_ch = chainage_from_meters(start_m)
        end_ch = chainage_from_meters(end_m)
        code = f"ST-{i:03d}"
        name = f"Stretch {start_ch} to {end_ch}"
        result.append(
            {
                "sequence_no": i,
                "stretch_code": code,
                "stretch_name": name,
                "start_chainage": start_ch,
                "end_chainage": end_ch,
                "length_m": int(length_m),
                "start_m": int(start_m),
                "end_m": int(end_m),
            }
        )

    if not result or result[-1]["end_m"] != total_length_m:
        raise ValueError("Generated stretches do not match total length")

    return result
