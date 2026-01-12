def divide_tool(g: float, h: float) -> float:
    """Divides one number by another.

    Args:
        g (float): The dividend.
        h (float): The divisor (must not be zero).

    Returns:
        float: The result of g divided by h.

    Raises:
        ZeroDivisionError: If h is zero.
    """
    return g / h


def add_tool(a: float, b: float) -> float:
    """Adds two numbers.

    Args:
        a (float): The first number.
        b (float): The second number.

    Returns:
        float: The sum of a and b.
    """
    return a + b


def subtract_tool(a: float, b: float) -> float:
    """Subtracts one number from another.

    Args:
        a (float): The number to subtract from.
        b (float): The number to subtract.

    Returns:
        float: The result of a minus b.
    """
    return a - b


def multiply_tool(a: float, b: float) -> float:
    """Multiplies two numbers.

    Args:
        a (float): The first number.
        b (float): The second number.

    Returns:
        float: The product of a and b.
    """
    return a * b


def map_kdi_number(i: float) -> float:
    """
    return the mapping of the numer i to it's kdi value

    Args:
        i (float): The number to map.


    Returns:
        float: The value of the dki of the given number.
    """
    return 3.14 * i
