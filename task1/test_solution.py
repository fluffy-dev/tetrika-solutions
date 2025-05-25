# task_1/test_solution.py
import pytest
from task1.solution import strict  # Assuming solution.py is in the same directory or PYTHONPATH is set

# Define some functions to decorate for testing
@strict
def sum_two_strict(a: int, b: int) -> int:
    return a + b

@strict
def concat_strict(a: str, b: str) -> str:
    return a + b

@strict
def process_data_strict(name: str, age: int, score: float, active: bool) -> None:
    pass

@strict
def no_args_strict() -> str:
    return "done"

@strict
def one_arg_strict(val: int) -> int:
    return val * 2

class TestStrictDecorator:

    def test_sum_two_correct_types(self):
        assert sum_two_strict(1, 2) == 3
        assert sum_two_strict(0, 0) == 0
        assert sum_two_strict(-5, 5) == 0

    def test_sum_two_incorrect_first_type(self):
        with pytest.raises(TypeError) as excinfo:
            sum_two_strict("1", 2)
        assert "Argument 'a' expected type int, but got type str" in str(excinfo.value)

    def test_sum_two_incorrect_second_type(self):
        with pytest.raises(TypeError) as excinfo:
            sum_two_strict(1, 2.5)
        assert "Argument 'b' expected type int, but got type float" in str(excinfo.value)

    def test_sum_two_incorrect_both_types(self):
        with pytest.raises(TypeError) as excinfo: # Error will be for the first incorrect arg
            sum_two_strict("1", "2")
        assert "Argument 'a' expected type int, but got type str" in str(excinfo.value)

    def test_concat_correct_types(self):
        assert concat_strict("hello", "world") == "helloworld"
        assert concat_strict("", "test") == "test"

    def test_concat_incorrect_type(self):
        with pytest.raises(TypeError) as excinfo:
            concat_strict("hello", 123)
        assert "Argument 'b' expected type str, but got type int" in str(excinfo.value)

    def test_process_data_correct_types(self):
        try:
            process_data_strict("Alice", 30, 99.5, True)
        except TypeError:
            pytest.fail("process_data_strict raised TypeError unexpectedly")

    def test_process_data_incorrect_int_type(self):
        with pytest.raises(TypeError) as excinfo:
            process_data_strict("Alice", "30", 99.5, True)
        assert "Argument 'age' expected type int, but got type str" in str(excinfo.value)

    def test_process_data_incorrect_float_type(self):
        with pytest.raises(TypeError) as excinfo:
            process_data_strict("Alice", 30, "99.5", True)
        assert "Argument 'score' expected type float, but got type str" in str(excinfo.value)

    def test_process_data_incorrect_bool_type(self):
        with pytest.raises(TypeError) as excinfo:
            process_data_strict("Alice", 30, 99.5, "True")
        assert "Argument 'active' expected type bool, but got type str" in str(excinfo.value)

        with pytest.raises(TypeError) as excinfo_int: # Checking int is not bool
            process_data_strict("Alice", 30, 99.5, 1)
        assert "Argument 'active' expected type bool, but got type int" in str(excinfo_int.value)


    def test_no_args_function(self):
        assert no_args_strict() == "done"

    def test_one_arg_correct(self):
        assert one_arg_strict(10) == 20

    def test_one_arg_incorrect(self):
        with pytest.raises(TypeError) as excinfo:
            one_arg_strict("10")
        assert "Argument 'val' expected type int, but got type str" in str(excinfo.value)

    def test_function_with_return_annotation_only(self):
        @strict
        def func_ret_only() -> int:
            return 1
        assert func_ret_only() == 1 # Should not raise error

    def test_function_with_mixed_annotations(self):
        @strict
        def func_mixed(a: int, b) -> float: # b has no annotation
            return float(a + (b if isinstance(b, int) else 0))

        assert func_mixed(1, 2) == 3.0
        assert func_mixed(1, "no_check_for_b") == 1.0 # b is not type checked

        with pytest.raises(TypeError):
            func_mixed("1", 2) # a should be checked