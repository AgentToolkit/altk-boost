from jinja2 import Environment, PackageLoader, select_autoescape

from altk.pre_tool.toolguard.toolguard.common.py import path_to_module
from altk.pre_tool.toolguard.toolguard.common.str import to_snake_case

env = Environment(
    loader=PackageLoader("altk.pre_tool.toolguard.toolguard.gen_py", "templates"),
    autoescape=select_autoescape(),
)
env.globals["path_to_module"] = path_to_module
env.globals["to_snake_case"] = to_snake_case


def load_template(template_name: str):
    return env.get_template(template_name)
