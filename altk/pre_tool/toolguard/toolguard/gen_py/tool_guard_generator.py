import inspect
import os
import asyncio
import logging
from os.path import join
import re
from typing import Callable, List, Tuple

from altk.pre_tool.toolguard.toolguard.common import py
from altk.pre_tool.toolguard.toolguard.common.llm_py import get_code_content
from altk.pre_tool.toolguard.toolguard.common.py_doc_str import extract_docstr_args
from altk.pre_tool.toolguard.toolguard.common.str import to_snake_case
from altk.pre_tool.toolguard.toolguard.data_types import (
    DEBUG_DIR,
    TESTS_DIR,
    FileTwin,
    RuntimeDomain,
    ToolPolicy,
    ToolPolicyItem,
)
from altk.pre_tool.toolguard.toolguard.gen_py.consts import (
    guard_fn_module_name,
    guard_fn_name,
    guard_item_fn_module_name,
    guard_item_fn_name,
    test_fn_module_name,
)
from altk.pre_tool.toolguard.toolguard.gen_py.tool_dependencies import tool_dependencies
from altk.pre_tool.toolguard.toolguard.runtime import (
    ToolGuardCodeResult,
    find_class_in_module,
    load_module_from_path,
)
import altk.pre_tool.toolguard.toolguard.gen_py.utils.pytest as pytest
import altk.pre_tool.toolguard.toolguard.gen_py.utils.pyright as pyright
from altk.pre_tool.toolguard.toolguard.gen_py.prompts.gen_tests import (
    generate_init_tests,
    improve_tests,
)
from altk.pre_tool.toolguard.toolguard.gen_py.prompts.improve_guard import (
    improve_tool_guard,
)
from altk.pre_tool.toolguard.toolguard.gen_py.templates import load_template

logger = logging.getLogger(__name__)

MAX_TOOL_IMPROVEMENTS = 5
MAX_TEST_GEN_TRIALS = 3


class ToolGuardGenerator:
    app_name: str
    py_path: str
    tool_policy: ToolPolicy
    domain: RuntimeDomain
    common: FileTwin

    def __init__(
        self,
        app_name: str,
        tool_policy: ToolPolicy,
        py_path: str,
        domain: RuntimeDomain,
        py_env: str,
    ) -> None:
        self.py_path = py_path
        self.app_name = app_name
        self.tool_policy = tool_policy
        self.domain = domain
        self.py_env = py_env

    def start(self):
        app_path = join(self.py_path, to_snake_case(self.app_name))
        os.makedirs(app_path, exist_ok=True)
        os.makedirs(
            join(app_path, to_snake_case(self.tool_policy.tool_name)), exist_ok=True
        )
        os.makedirs(join(self.py_path, to_snake_case(DEBUG_DIR)), exist_ok=True)
        os.makedirs(
            join(
                self.py_path,
                to_snake_case(DEBUG_DIR),
                to_snake_case(self.tool_policy.tool_name),
            ),
            exist_ok=True,
        )
        for item in self.tool_policy.policy_items:
            os.makedirs(
                join(
                    self.py_path,
                    to_snake_case(DEBUG_DIR),
                    to_snake_case(self.tool_policy.tool_name),
                    to_snake_case(item.name),
                ),
                exist_ok=True,
            )
        os.makedirs(join(self.py_path, to_snake_case(TESTS_DIR)), exist_ok=True)

    async def generate(self) -> ToolGuardCodeResult:
        self.start()
        tool_guard, init_item_guards = self._create_initial_tool_guards()

        # Generate guards for all tool items
        tests_and_guards = await asyncio.gather(
            *[
                self._generate_item_tests_and_guard(item, item_guard)
                for item, item_guard in zip(
                    self.tool_policy.policy_items, init_item_guards
                )
            ]
        )

        item_tests, item_guards = zip(*tests_and_guards)
        return ToolGuardCodeResult(
            tool=self.tool_policy,
            guard_fn_name=guard_fn_name(self.tool_policy),
            guard_file=tool_guard,
            item_guard_files=item_guards,
            test_files=item_tests,
        )

    async def _generate_item_tests_and_guard(
        self, item: ToolPolicyItem, init_guard: FileTwin
    ) -> Tuple[FileTwin | None, FileTwin]:
        # Dependencies of this tool
        tool_fn_name = to_snake_case(self.tool_policy.tool_name)
        tool_fn = self._find_api_function(tool_fn_name)
        sig_str = f"{tool_fn_name}{str(inspect.signature(tool_fn))}"
        dep_tools = []
        if self.domain.app_api_size > 1:
            domain = self.domain.get_definitions_only()  # remove runtime fields
            dep_tools = list(await tool_dependencies(item, sig_str, domain))
        logger.debug(f"Dependencies of '{item.name}': {dep_tools}")

        # Generate tests
        try:
            guard_tests = await self._generate_tests(item, init_guard, dep_tools)
        except Exception as ex:
            logger.warning(f"Tests generation failed for item {item.name} %s", str(ex))
            try:
                logger.warning("try to generate the code without tests... %s", str(ex))
                guard = await self._improve_guard(item, init_guard, [], dep_tools)
                return None, guard
            except Exception as ex:
                logger.warning(
                    "guard generation failed. returning initial guard: %s", str(ex)
                )
                return None, init_guard

        # Tests generated, now generate guards
        try:
            guard = await self._improve_guard_green_loop(
                item, init_guard, guard_tests, dep_tools
            )
            logger.debug(
                f"tool item generated successfully '{item.name}'"
            )  # 😄🎉 Happy path
            return guard_tests, guard
        except Exception as ex:
            logger.warning(
                "guard generation failed. returning initial guard: %s", str(ex)
            )
            return None, init_guard

    # async def tool_dependencies(self, policy_item: ToolPolicyItem, tool_signature: str) -> Set[str]:
    #     domain = self.domain.get_definitions_only() #remove runtime fields
    #     pseudo_code = await tool_policy_pseudo_code(policy_item, tool_signature, domain)
    #     dep_tools = await extract_api_dependencies_from_pseudo_code(pseudo_code, domain)
    #     return set(dep_tools)

    async def _generate_tests(
        self, item: ToolPolicyItem, guard: FileTwin, dep_tools: List[str]
    ) -> FileTwin:
        test_file_name = join(
            TESTS_DIR, self.tool_policy.tool_name, f"{test_fn_module_name(item)}.py"
        )
        errors = []
        test_file = None
        trials = "a b c".split()
        for trial_no in trials:
            logger.debug(
                f"Generating tests iteration '{trial_no}' for tool {self.tool_policy.tool_name} '{item.name}'."
            )
            domain = self.domain.get_definitions_only()  # remove runtime fields
            first_time = trial_no == "a"
            if first_time:
                # FIXME when melea will support aysnc
                res = await asyncio.to_thread(
                    lambda: generate_init_tests(
                        fn_src=guard,
                        policy_item=item,
                        domain=domain,  # noqa: B023
                        dependent_tool_names=dep_tools,
                    )
                )
            else:
                assert test_file
                # FIXME when melea will support aysnc
                res = await asyncio.to_thread(
                    lambda: improve_tests(
                        prev_impl=test_file.content,  # noqa: B023
                        domain=domain,  # noqa: B023
                        policy_item=item,
                        review_comments=errors,  # noqa: B023
                        dependent_tool_names=dep_tools,
                    )
                )

            test_file = FileTwin(
                file_name=test_file_name, content=get_code_content(res)
            ).save(self.py_path)
            test_file.save_as(self.py_path, self.debug_dir(item, f"test_{trial_no}.py"))

            syntax_report = pyright.run(self.py_path, test_file.file_name, self.py_env)
            FileTwin(
                file_name=self.debug_dir(item, f"test_{trial_no}_pyright.json"),
                content=syntax_report.model_dump_json(indent=2),
            ).save(self.py_path)

            if syntax_report.summary.errorCount > 0:
                logger.warning(
                    f"{syntax_report.summary.errorCount} syntax errors in tests iteration '{trial_no}' in item '{item.name}'."
                )
                errors = syntax_report.list_error_messages(test_file.content)
                continue

            # syntax ok, try to run it...
            logger.debug(
                f"Generated Tests for tool '{self.tool_policy.tool_name}' '{item.name}'(trial='{trial_no}')"
            )
            report_file_name = self.debug_dir(item, f"test_{trial_no}_pytest.json")
            pytest_report = pytest.run(
                self.py_path, test_file.file_name, report_file_name
            )
            if (
                pytest_report.all_tests_collected_successfully()
                and pytest_report.non_empty_tests()
            ):
                return test_file
            if not pytest_report.non_empty_tests():  # empty test set
                errors = ["empty set of generated unit tests is not allowed"]
            else:
                errors = pytest_report.list_errors()

        raise Exception("Generated tests contain syntax errors")

    async def _improve_guard_green_loop(
        self,
        item: ToolPolicyItem,
        guard: FileTwin,
        tests: FileTwin,
        dep_tools: List[str],
    ) -> FileTwin:
        trial_no = 0
        while trial_no < MAX_TOOL_IMPROVEMENTS:
            pytest_report_file = self.debug_dir(item, f"guard_{trial_no}_pytest.json")
            errors = pytest.run(
                self.py_path, tests.file_name, pytest_report_file
            ).list_errors()
            if errors:
                logger.debug(f"'{item.name}' guard function tests failed. Retrying...")

                trial_no += 1
                try:
                    guard = await self._improve_guard(
                        item, guard, errors, dep_tools, trial_no
                    )
                except Exception:
                    continue  # probably a syntax error in the generated code. lets retry...
            else:
                logger.debug(
                    f"'{item.name}' guard function generated succefully and is Green 😄🎉. "
                )
                return guard  # Green

        raise Exception(
            f"Failed {MAX_TOOL_IMPROVEMENTS} times to generate guard function for tool {to_snake_case(self.tool_policy.tool_name)} policy: {item.name}"
        )

    async def _improve_guard(
        self,
        item: ToolPolicyItem,
        prev_guard: FileTwin,
        review_comments: List[str],
        dep_tools: List[str],
        round: int = 0,
    ) -> FileTwin:
        module_name = guard_item_fn_module_name(item)
        errors = []
        trials = "a b c".split()
        for trial in trials:
            logger.debug(
                f"Improving guard function '{module_name}'... (trial = {round}.{trial})"
            )
            domain = self.domain.get_definitions_only()  # omit runtime fields
            prev_python = get_code_content(prev_guard.content)
            # FIXME when melea will support aysnc
            res = await asyncio.to_thread(
                lambda: improve_tool_guard(
                    prev_impl=prev_python,  # noqa: B023
                    domain=domain,  # noqa: B023
                    policy_item=item,
                    dependent_tool_names=dep_tools,
                    review_comments=review_comments + errors,  # noqa: B023
                )
            )

            guard = FileTwin(
                file_name=prev_guard.file_name, content=get_code_content(res)
            ).save(self.py_path)
            guard.save_as(
                self.py_path, self.debug_dir(item, f"guard_{round}_{trial}.py")
            )

            syntax_report = pyright.run(self.py_path, guard.file_name, self.py_env)
            FileTwin(
                file_name=self.debug_dir(item, f"guard_{round}_{trial}.pyright.json"),
                content=syntax_report.model_dump_json(indent=2),
            ).save(self.py_path)
            logger.info(
                f"Generated function {module_name} with {syntax_report.summary.errorCount} errors."
            )

            if syntax_report.summary.errorCount > 0:
                # Syntax errors. retry...
                errors = syntax_report.list_error_messages(guard.content)
                continue

            guard.save_as(self.py_path, self.debug_dir(item, f"guard_{round}_final.py"))
            return (
                guard  # Happy path. improved vesion of the guard with no syntax errors
            )

        # Failed to generate valid python after iterations
        raise Exception(f"Syntax error generating for tool '{item.name}'.")

    def _find_api_function(self, tool_fn_name: str):
        with py.temp_python_path(self.py_path):
            module = load_module_from_path(self.domain.app_api.file_name, self.py_path)
        assert module, f"File not found {self.domain.app_api.file_name}"
        cls = find_class_in_module(module, self.domain.app_api_class_name)
        return getattr(cls, tool_fn_name)

    def _create_initial_tool_guards(self) -> Tuple[FileTwin, List[FileTwin]]:
        tool_fn_name = to_snake_case(self.tool_policy.tool_name)
        tool_fn = self._find_api_function(tool_fn_name)
        assert tool_fn, f"Function not found, {tool_fn_name}"

        # __init__.py
        path = join(to_snake_case(self.app_name), tool_fn_name, "__init__.py")
        FileTwin(file_name=path, content="").save(self.py_path)

        # item guards files
        item_files = [
            self._create_item_module(item, tool_fn)
            for item in self.tool_policy.policy_items
        ]
        # tool guard file
        tool_file = self._create_tool_module(tool_fn, item_files)

        # Save to debug folder
        for item_guard_fn, policy_item in zip(
            item_files, self.tool_policy.policy_items
        ):
            item_guard_fn.save_as(self.py_path, self.debug_dir(policy_item, "g0.py"))

        return (tool_file, item_files)

    def _create_tool_module(
        self, tool_fn: Callable, item_files: List[FileTwin]
    ) -> FileTwin:
        file_name = join(
            to_snake_case(self.app_name),
            to_snake_case(self.tool_policy.tool_name),
            py.py_extension(guard_fn_module_name(self.tool_policy)),
        )
        items = [
            {"guard_fn": guard_item_fn_name(item), "file_name": file.file_name}
            for (item, file) in zip(self.tool_policy.policy_items, item_files)
        ]
        sig = inspect.signature(tool_fn)
        sig_str = self._signature_str(sig)
        args_call = ", ".join([p for p in sig.parameters if p != "self"])
        args_doc_str = extract_docstr_args(tool_fn)
        extra_imports = []
        if "Decimal" in sig_str:
            extra_imports.append("from decimal import Decimal")

        return FileTwin(
            file_name=file_name,
            content=load_template("tool_guard.j2").render(
                domain=self.domain,
                method={
                    "name": guard_fn_name(self.tool_policy),
                    "signature": sig_str,
                    "args_call": args_call,
                    "args_doc_str": args_doc_str,
                },
                items=items,
                extra_imports=extra_imports,
            ),
        ).save(self.py_path)

    def _signature_str(self, sig: inspect.Signature):
        sig_str = str(sig)
        sig_str = sig_str[
            sig_str.find("self,") + len("self,") : sig_str.rfind(")")
        ].strip()
        # Strip module prefixes like airline.airline_types.XXX → XXX
        clean_sig_str = re.sub(r"\b(?:\w+\.)+(\w+)", r"\1", sig_str)
        return clean_sig_str

    def _create_item_module(
        self, tool_item: ToolPolicyItem, tool_fn: Callable
    ) -> FileTwin:
        file_name = join(
            to_snake_case(self.app_name),
            to_snake_case(self.tool_policy.tool_name),
            py.py_extension(guard_item_fn_module_name(tool_item)),
        )
        sig_str = self._signature_str(inspect.signature(tool_fn))
        args_doc_str = extract_docstr_args(tool_fn)
        extra_imports = []
        if "Decimal" in sig_str:
            extra_imports.append("from decimal import Decimal")
        return FileTwin(
            file_name=file_name,
            content=load_template("tool_item_guard.j2").render(
                domain=self.domain,
                method={
                    "name": guard_item_fn_name(tool_item),
                    "signature": sig_str,
                    "args_doc_str": args_doc_str,
                },
                policy=tool_item.description,
                extra_imports=extra_imports,
            ),
        ).save(self.py_path)

    def debug_dir(self, policy_item: ToolPolicyItem, dir: str):
        return join(
            DEBUG_DIR,
            to_snake_case(self.tool_policy.tool_name),
            to_snake_case(policy_item.name),
            dir,
        )
