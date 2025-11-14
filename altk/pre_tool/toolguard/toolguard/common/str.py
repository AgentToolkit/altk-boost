def to_camel_case(snake_str: str) -> str:
    return (
        snake_str.replace("_", " ")
        .title()
        .replace(" ", "")
        .replace("-", "_")
        .replace("'", "_")
        .replace(",", "_")
        .replace(".", "_")
    )


def to_snake_case(human_name: str) -> str:
    return (
        human_name.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("'", "_")
        .replace(",", "_")
        .replace(".", "_")
    )
