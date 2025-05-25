import pytest
from task3.solution import appearance, _parse_timestamps_to_intervals, _clip_intervals_to_lesson, _calculate_overlap_duration


# --- Test cases for the main appearance function ---
appearance_test_cases = [
    # Provided examples
    pytest.param(
        {'lesson': [1594663200, 1594666800],
         'pupil': [1594663340, 1594663389, 1594663390, 1594663395, 1594663396, 1594666472],
         'tutor': [1594663290, 1594663430, 1594663443, 1594666473]},
        3117, id="provided_1"
    ),
    pytest.param(
        {'lesson': [1594702800, 1594706400],
         'pupil': [1594702789, 1594704500, 1594702807, 1594704542, 1594704512, 1594704513, 1594704564, 1594705150, 1594704581, 1594704582, 1594704734, 1594705009, 1594705095, 1594705096, 1594705106, 1594706480, 1594705158, 1594705773, 1594705849, 1594706480, 1594706500, 1594706875, 1594706502, 1594706503, 1594706524, 1594706524, 1594706579, 1594706641],
         'tutor': [1594700035, 1594700364, 1594702749, 1594705148, 1594705149, 1594706463]},
        3577, id="provided_2"
    ),
    pytest.param(
        {'lesson': [1594692000, 1594695600],
         'pupil': [1594692033, 1594696347],
         'tutor': [1594692017, 1594692066, 1594692068, 1594696341]},
        3565, id="provided_3"
    ),
    # Custom test cases
    pytest.param({'lesson': [0, 100], 'pupil': [10, 20], 'tutor': [30, 40]}, 0, id="no_overlap"),
    pytest.param({'lesson': [0, 100], 'pupil': [], 'tutor': [0, 100]}, 0, id="empty_pupil"),
    pytest.param({'lesson': [], 'pupil': [0, 100], 'tutor': [0, 100]}, 0, id="empty_lesson"),
    pytest.param({'lesson': [10, 20], 'pupil': [0, 30], 'tutor': [5, 25]}, 10, id="full_overlap_within_clipped_lesson"),
    pytest.param({'lesson': [0, 100], 'pupil': [10, 50], 'tutor': [20, 40, 30, 60]}, 30, id="tutor_merged_overlap_pupil"),
    pytest.param({'lesson': [0, 100], 'pupil': [10,20, 20,30, 40,50], 'tutor': [15,45]}, 20, id="pupil_touching_intervals_overlap_tutor"),
    pytest.param({'lesson': [0, 100], 'pupil': [10,20, 25,35], 'tutor': [15,30]}, 10, id="pupil_disjoint_tutor_overlap_both"), # (15,20) + (25,30) = 5+5 =10
    pytest.param({'lesson': [0, 10], 'pupil': [100,110], 'tutor': [100,110]}, 0, id="all_outside_lesson"),
    pytest.param({'lesson': [0, 0], 'pupil': [0,10], 'tutor': [0,10]}, 0, id="zero_duration_lesson"),
    pytest.param({'lesson': [0, 100], 'pupil': [10,5, 20,30], 'tutor': [0,100]}, 10, id="invalid_pupil_interval_ignored"),
]

@pytest.mark.parametrize("intervals_data, expected_duration", appearance_test_cases)
def test_appearance(intervals_data, expected_duration):
    assert appearance(intervals_data) == expected_duration


# --- Optional: Tests for helper functions if desired for more granularity ---

@pytest.mark.parametrize("timestamps, expected_intervals", [
    ([1, 2, 3, 4], [(1, 2), (3, 4)]),
    ([1, 2, 4, 3], [(1, 2)]), # Invalid (4,3) skipped
    ([1, 2, 3], [(1, 2)]),    # Odd number, last one skipped
    ([], []),
    ([5, 5], []), # Invalid (5,5)
])
def test_parse_timestamps_to_intervals(timestamps, expected_intervals):
    assert _parse_timestamps_to_intervals(timestamps) == expected_intervals

@pytest.mark.parametrize("intervals, lesson_s, lesson_e, expected_clipped", [
    ([(0, 10), (15, 25)], 5, 20, [(5, 10), (15, 20)]),
    ([(0, 5), (20, 25)], 5, 20, []), # All outside or touching boundaries
    ([(0, 25)], 5, 20, [(5, 20)]),
    ([], 0, 10, []),
])
def test_clip_intervals_to_lesson(intervals, lesson_s, lesson_e, expected_clipped):
    assert _clip_intervals_to_lesson(intervals, lesson_s, lesson_e) == expected_clipped

@pytest.mark.parametrize("intervals1, intervals2, expected_overlap", [
    ([(10, 20)], [(15, 25)], 5), # (15,20)
    ([(10, 20), (30, 40)], [(15, 35)], 10), # (15,20) + (30,35) = 5+5=10
    ([(10, 30)], [(15, 20), (20, 25)], 10), # (15,20) + (20,25) -> merged (15,25) -> 10
    ([(10, 50)], [(20, 30), (25, 40)], 20), # Common: (20,30), (25,40) -> Merged: (20,40) -> 20
    ([], [(10,20)], 0),
    ([(10,20)], [], 0),
])
def test_calculate_overlap_duration(intervals1, intervals2, expected_overlap):
    assert _calculate_overlap_duration(intervals1, intervals2) == expected_overlap