import inspect
from functools import wraps



def strict(func):
    """
Enforces type checking for function arguments based on annotations.

This decorator inspects the function's signature and type annotations.
If any passed argument does not match its annotated type, a TypeError
is raised. It assumes that annotated arguments are of type bool, int,
float, or str, and that no default values are used for parameters.
    """
    sig = inspect.signature(func)
    func_annotations = func.__annotations__

    @wraps(func)
    def wrapper(*args, **kwargs):
        """
The wrapper function that performs the type checking before calling
the original function.
        """
        bound_args = sig.bind(*args, **kwargs)

        for param_name, value in bound_args.arguments.items():
            if param_name in func_annotations:
                expected_type = func_annotations[param_name]

                if param_name == 'return': # Skip 'return' annotation for argument checking
                    continue

                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"Argument '{param_name}' expected type {expected_type.__name__}, "
                        f"but got type {type(value).__name__} with value {value!r}."
                    )
        return func(*args, **kwargs)
    return wrapper

@strict
def sum_two(a: int, b: int) -> int:
    return a + b


print(sum_two(1, 2))  # >>> 3

