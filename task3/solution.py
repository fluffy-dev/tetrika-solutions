from typing import List, Dict, Tuple

def _parse_timestamps_to_intervals(timestamps: List[int]) -> List[Tuple[int, int]]:
    """
Converts a flat list of timestamps [s1, e1, s2, e2,...] into a list of
interval tuples [(s1,e1), (s2,e2),...].
Invalid intervals (e.g., start >= end or odd number of timestamps) are skipped.
    """
    intervals = []
    for i in range(0, len(timestamps), 2):
        if i + 1 < len(timestamps):
            start, end = timestamps[i], timestamps[i+1]
            if start < end:
                intervals.append((start, end))
    return intervals

def _clip_intervals_to_lesson(
        intervals: List[Tuple[int, int]],
        lesson_start: int,
        lesson_end: int
) -> List[Tuple[int, int]]:
    """
Clips a list of time intervals to be within the lesson boundaries.
Only valid intervals (start < end after clipping) are kept.
    """
    clipped_intervals = []
    for start, end in intervals:
        effective_start = max(start, lesson_start)
        effective_end = min(end, lesson_end)
        if effective_start < effective_end:
            clipped_intervals.append((effective_start, effective_end))
    return clipped_intervals

def _calculate_overlap_duration(
        intervals1: List[Tuple[int, int]],
        intervals2: List[Tuple[int, int]]
) -> int:
    """
Calculates the total duration of overlap between two lists of time intervals.
Overlapping segments are merged before summing their durations.
    """
    common_segments = []
    for r1_start, r1_end in intervals1:
        for r2_start, r2_end in intervals2:
            overlap_start = max(r1_start, r2_start)
            overlap_end = min(r1_end, r2_end)
            if overlap_start < overlap_end:
                common_segments.append((overlap_start, overlap_end))

    if not common_segments:
        return 0

    common_segments.sort(key=lambda x: x[0])

    merged_segments = []
    current_merged_start, current_merged_end = common_segments[0]

    for i in range(1, len(common_segments)):
        next_start, next_end = common_segments[i]
        if next_start < current_merged_end:
            current_merged_end = max(current_merged_end, next_end)
        else:
            merged_segments.append((current_merged_start, current_merged_end))
            current_merged_start, current_merged_end = next_start, next_end
    merged_segments.append((current_merged_start, current_merged_end))

    total_duration = 0
    for start, end in merged_segments:
        total_duration += (end - start)
    return total_duration

def appearance(intervals_data: Dict[str, List[int]]) -> int:
    """
Calculates the total time (in seconds) of common presence of a pupil
and a tutor during a lesson.

The input is a dictionary containing 'lesson', 'pupil', and 'tutor' keys,
each mapping to a list of timestamps representing entry and exit times.
For example, [start1, end1, start2, end2, ...].

Args:
intervals_data: A dictionary with 'lesson', 'pupil', and 'tutor'
timestamp lists.

Returns:
The total common presence time in seconds.
    """
    lesson_times = intervals_data.get('lesson', [])
    pupil_times = intervals_data.get('pupil', [])
    tutor_times = intervals_data.get('tutor', [])

    if not lesson_times or len(lesson_times) < 2:
        return 0
    lesson_start, lesson_end = lesson_times[0], lesson_times[1]
    if lesson_start >= lesson_end: # Invalid lesson interval
        return 0

    pupil_intervals_raw = _parse_timestamps_to_intervals(pupil_times)
    tutor_intervals_raw = _parse_timestamps_to_intervals(tutor_times)

    pupil_effective_intervals = _clip_intervals_to_lesson(pupil_intervals_raw, lesson_start, lesson_end)
    tutor_effective_intervals = _clip_intervals_to_lesson(tutor_intervals_raw, lesson_start, lesson_end)

    if not pupil_effective_intervals or not tutor_effective_intervals:
        return 0

    return _calculate_overlap_duration(pupil_effective_intervals, tutor_effective_intervals)
