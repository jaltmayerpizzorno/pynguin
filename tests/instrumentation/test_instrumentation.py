#  This file is part of Pynguin.
#
#  SPDX-FileCopyrightText: 2019–2022 Pynguin Contributors
#
#  SPDX-License-Identifier: LGPL-3.0-or-later
#
import importlib
import os
import threading
from unittest import mock
from unittest.mock import MagicMock, call

import pytest
from bytecode import Compare

from pynguin.analyses.constants import (
    ConstantPool,
    DynamicConstantProvider,
    EmptyConstantProvider,
)
from pynguin.instrumentation.instrumentation import (
    ArtificialInstr,
    BranchCoverageInstrumentation,
    DynamicSeedingInstrumentation,
    InstrumentationAdapter,
    InstrumentationTransformer,
    LineCoverageInstrumentation,
)
from pynguin.testcase.execution import ExecutionTracer


@pytest.fixture()
def simple_module():
    simple = importlib.import_module("tests.fixtures.instrumentation.simple")
    simple = importlib.reload(simple)
    return simple


@pytest.fixture()
def artificial_none_module():
    simple = importlib.import_module("tests.fixtures.linecoverage.artificial_none")
    simple = importlib.reload(simple)
    return simple


@pytest.fixture()
def comparison_module():
    comparison = importlib.import_module("tests.fixtures.instrumentation.comparison")
    comparison = importlib.reload(comparison)
    return comparison


@pytest.fixture()
def tracer_mock():
    tracer = MagicMock()
    tracer.register_code_object.side_effect = range(100)
    tracer.register_predicate.side_effect = range(100)
    return tracer


def test_entered_function(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.simple_function.__code__ = transformer.instrument_module(
        simple_module.simple_function.__code__
    )
    simple_module.simple_function(1)
    tracer_mock.register_code_object.assert_called_once()
    tracer_mock.executed_code_object.assert_called_once()


def test_entered_for_loop_no_jump(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.for_loop.__code__ = transformer.instrument_module(
        simple_module.for_loop.__code__
    )
    tracer_mock.register_predicate.assert_called_once()
    simple_module.for_loop(3)
    tracer_mock.executed_bool_predicate.assert_called_with(True, 0)


def test_entered_for_loop_no_jump_not_entered(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.for_loop.__code__ = transformer.instrument_module(
        simple_module.for_loop.__code__
    )
    tracer_mock.register_predicate.assert_called_once()
    simple_module.for_loop(0)
    tracer_mock.executed_bool_predicate.assert_called_with(False, 0)


def test_entered_for_loop_full_loop(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.full_for_loop.__code__ = transformer.instrument_module(
        simple_module.full_for_loop.__code__
    )
    tracer_mock.register_predicate.assert_called_once()
    simple_module.full_for_loop(3)
    tracer_mock.executed_bool_predicate.assert_has_calls(
        [call(True, 0), call(True, 0), call(True, 0), call(False, 0)]
    )
    assert tracer_mock.executed_bool_predicate.call_count == 4


def test_entered_for_loop_full_loop_not_entered(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.full_for_loop.__code__ = transformer.instrument_module(
        simple_module.full_for_loop.__code__
    )
    tracer_mock.register_predicate.assert_called_once()
    simple_module.full_for_loop(0)
    tracer_mock.executed_bool_predicate.assert_called_with(False, 0)


def test_add_bool_predicate(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.bool_predicate.__code__ = transformer.instrument_module(
        simple_module.bool_predicate.__code__
    )
    simple_module.bool_predicate(True)
    tracer_mock.register_predicate.assert_called_once()
    tracer_mock.executed_bool_predicate.assert_called_once()


def test_add_cmp_predicate(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.cmp_predicate.__code__ = transformer.instrument_module(
        simple_module.cmp_predicate.__code__
    )
    simple_module.cmp_predicate(1, 2)
    tracer_mock.register_predicate.assert_called_once()
    tracer_mock.executed_compare_predicate.assert_called_once()


def test_transform_for_loop_multi(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.multi_loop.__code__ = transformer.instrument_module(
        simple_module.multi_loop.__code__
    )
    assert simple_module.multi_loop(2) == 4
    assert tracer_mock.register_predicate.call_count == 3
    calls = [call(True, 0), call(True, 1), call(True, 1), call(False, 1)] * 2 + [
        call(False, 0),
        call(False, 2),
    ]
    assert tracer_mock.executed_bool_predicate.call_count == len(calls)
    tracer_mock.executed_bool_predicate.assert_has_calls(calls)


def test_add_cmp_predicate_loop_comprehension(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.comprehension.__code__ = transformer.instrument_module(
        simple_module.comprehension.__code__
    )
    call_count = 5
    simple_module.comprehension(call_count, 3)
    assert tracer_mock.register_predicate.call_count == 2
    assert tracer_mock.executed_compare_predicate.call_count == call_count
    tracer_mock.executed_bool_predicate.assert_has_calls([call(True, 1)])


def test_add_cmp_predicate_lambda(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.lambda_func.__code__ = transformer.instrument_module(
        simple_module.lambda_func.__code__
    )
    lam = simple_module.lambda_func(10)
    lam(5)
    tracer_mock.register_predicate.assert_called_once()
    assert tracer_mock.register_code_object.call_count == 2
    tracer_mock.executed_compare_predicate.assert_called_once()
    tracer_mock.executed_code_object.assert_has_calls(
        [call(0), call(1)], any_order=True
    )


def test_conditional_assignment(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.conditional_assignment.__code__ = transformer.instrument_module(
        simple_module.conditional_assignment.__code__
    )
    simple_module.conditional_assignment(10)
    tracer_mock.register_predicate.assert_called_once()
    assert tracer_mock.register_code_object.call_count == 1
    tracer_mock.executed_compare_predicate.assert_called_once()
    tracer_mock.executed_code_object.assert_has_calls([call(0)])


def test_conditionally_nested_class(simple_module, tracer_mock):
    adapter = BranchCoverageInstrumentation(tracer_mock)
    transformer = InstrumentationTransformer(tracer_mock, [adapter])
    simple_module.conditionally_nested_class.__code__ = transformer.instrument_module(
        simple_module.conditionally_nested_class.__code__
    )
    assert tracer_mock.register_code_object.call_count == 3

    simple_module.conditionally_nested_class(6)
    tracer_mock.executed_code_object.assert_has_calls(
        [call(0), call(1), call(2)], any_order=True
    )
    tracer_mock.register_predicate.assert_called_once()
    tracer_mock.executed_compare_predicate.assert_called_once()


def test_avoid_duplicate_instrumentation(simple_module):
    tracer = MagicMock(ExecutionTracer)
    tracer.register_code_object.return_value = 0
    adapter = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    already_instrumented = transformer.instrument_module(
        simple_module.cmp_predicate.__code__
    )
    with pytest.raises(AssertionError):
        transformer.instrument_module(already_instrumented)


@pytest.mark.parametrize(
    "block,expected",
    [
        ([], {}),
        ([MagicMock()], {0: 0}),
        ([MagicMock(), MagicMock()], {0: 0, 1: 1}),
        ([MagicMock(), ArtificialInstr("POP_TOP"), MagicMock()], {0: 0, 1: 2}),
        ([ArtificialInstr("POP_TOP"), ArtificialInstr("POP_TOP"), MagicMock()], {0: 2}),
    ],
)
def test__map_instr_positions(block, expected):
    assert InstrumentationAdapter._map_instr_positions(block) == expected


@pytest.mark.parametrize(
    "function_name, branchless_function_count, branches_count",
    [
        ("simple_function", 1, 0),
        ("cmp_predicate", 0, 1),
        ("bool_predicate", 0, 1),
        ("for_loop", 0, 1),
        ("full_for_loop", 0, 1),
        ("multi_loop", 0, 3),
        ("comprehension", 1, 2),
        ("lambda_func", 1, 1),
        ("conditional_assignment", 0, 1),
        ("conditionally_nested_class", 2, 1),
    ],
)
def test_integrate_branch_distance_instrumentation(
    simple_module,
    function_name,
    branchless_function_count,
    branches_count,
):
    tracer = ExecutionTracer()
    function_callable = getattr(simple_module, function_name)
    adapter = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    function_callable.__code__ = transformer.instrument_module(
        function_callable.__code__
    )
    assert (
        len(tracer.get_known_data().branch_less_code_objects)
        == branchless_function_count
    )
    assert len(list(tracer.get_known_data().existing_predicates)) == branches_count


def test_integrate_line_coverage_instrumentation(simple_module):
    tracer = ExecutionTracer()
    function_callable = getattr(simple_module, "multi_loop")
    adapter = LineCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    function_callable.__code__ = transformer.instrument_module(
        function_callable.__code__
    )

    assert tracer.get_known_data().existing_lines
    # the body of the method contains 7 statements on lines 38 to 44
    assert {0, 1, 2, 3, 4, 5, 6} == tracer.get_known_data().existing_lines.keys()


@pytest.mark.parametrize(
    "op",
    [op for op in Compare if op != Compare.EXC_MATCH],
)
def test_comparison(comparison_module, op):
    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident
    function_callable = getattr(comparison_module, "_" + op.name.lower())
    adapter = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    function_callable.__code__ = transformer.instrument_module(
        function_callable.__code__
    )
    with mock.patch.object(tracer, "executed_compare_predicate") as trace_mock:
        function_callable("a", "a")
        trace_mock.assert_called_with("a", "a", 0, op)


def test_exception():
    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident

    def func():
        try:
            raise ValueError()
        except ValueError:
            pass

    adapter = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    func.__code__ = transformer.instrument_module(func.__code__)
    with mock.patch.object(tracer, "executed_exception_match") as trace_mock:
        func()
        trace_mock.assert_called_with(ValueError, ValueError, 0)


def test_exception_no_match():
    tracer = ExecutionTracer()
    tracer.current_thread_identifier = threading.current_thread().ident

    def func():
        try:
            raise RuntimeError()
        except ValueError:
            pass  # pragma: no cover

    adapter = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    func.__code__ = transformer.instrument_module(func.__code__)
    with mock.patch.object(tracer, "executed_exception_match") as trace_mock:
        with pytest.raises(RuntimeError):
            func()
        trace_mock.assert_called_with(RuntimeError, ValueError, 0)


def test_exception_integrate():
    tracer = ExecutionTracer()

    def func():
        try:
            raise ValueError()
        except ValueError:
            pass

    adapter = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    func.__code__ = transformer.instrument_module(func.__code__)
    tracer.current_thread_identifier = threading.current_thread().ident
    func()
    assert {0} == tracer.get_trace().executed_code_objects
    assert {0: 1} == tracer.get_trace().executed_predicates
    assert {0: 0.0} == tracer.get_trace().true_distances
    assert {0: 1.0} == tracer.get_trace().false_distances


def test_multiple_instrumentations_share_code_object_ids(simple_module):
    tracer = ExecutionTracer()

    line_instr = LineCoverageInstrumentation(tracer)
    branch_instr = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [line_instr, branch_instr])
    simple_module.simple_function.__code__ = transformer.instrument_module(
        simple_module.simple_function.__code__
    )

    tracer.current_thread_identifier = threading.current_thread().ident
    simple_module.simple_function(42)
    assert {0} == tracer.get_known_data().existing_code_objects.keys()
    assert {0} == tracer.get_known_data().branch_less_code_objects
    assert {0} == tracer.get_trace().executed_code_objects


def test_exception_no_match_integrate():
    tracer = ExecutionTracer()

    def func():
        try:
            raise RuntimeError()
        except ValueError:
            pass  # pragma: no cover

    adapter = BranchCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    func.__code__ = transformer.instrument_module(func.__code__)
    tracer.current_thread_identifier = threading.current_thread().ident
    with pytest.raises(RuntimeError):
        func()
    assert {0} == tracer.get_trace().executed_code_objects
    assert {0: 1} == tracer.get_trace().executed_predicates
    assert {0: 1.0} == tracer.get_trace().true_distances
    assert {0: 0.0} == tracer.get_trace().false_distances


def test_tracking_covered_statements_explicit_return(simple_module):
    tracer = ExecutionTracer()

    instr = LineCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [instr])
    simple_module.explicit_none_return.__code__ = transformer.instrument_module(
        simple_module.explicit_none_return.__code__
    )
    tracer.current_thread_identifier = threading.current_thread().ident
    simple_module.explicit_none_return()
    assert tracer.get_trace().covered_line_ids
    assert tracer.lineids_to_linenos(tracer.get_trace().covered_line_ids) == {77, 78}


@pytest.mark.parametrize(
    "value1, value2, expected_lines",
    [
        pytest.param(0, 1, {14, 17}),
        pytest.param(1, 0, {14, 15}),
    ],
)
def test_tracking_covered_statements_cmp_predicate(
    simple_module, value1, value2, expected_lines
):
    tracer = ExecutionTracer()

    adapter = LineCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    simple_module.cmp_predicate.__code__ = transformer.instrument_module(
        simple_module.cmp_predicate.__code__
    )
    tracer.current_thread_identifier = threading.current_thread().ident
    simple_module.cmp_predicate(value1, value2)
    assert tracer.get_trace().covered_line_ids
    assert (
        tracer.lineids_to_linenos(tracer.get_trace().covered_line_ids) == expected_lines
    )


@pytest.mark.parametrize(
    "value, expected_lines",
    [
        pytest.param(False, {21, 24}),
        pytest.param(True, {21, 22}),
    ],
)
def test_tracking_covered_statements_bool_predicate(
    simple_module, value, expected_lines
):
    tracer = ExecutionTracer()

    adapter = LineCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    simple_module.bool_predicate.__code__ = transformer.instrument_module(
        simple_module.bool_predicate.__code__
    )
    tracer.current_thread_identifier = threading.current_thread().ident
    simple_module.bool_predicate(value)
    assert tracer.get_trace().covered_line_ids
    assert (
        tracer.lineids_to_linenos(tracer.get_trace().covered_line_ids) == expected_lines
    )


@pytest.mark.parametrize(
    "number, expected_lines",
    [
        pytest.param(0, {33}),
        pytest.param(1, {33, 34}),
    ],
)
def test_tracking_covered_statements_for_loop(simple_module, number, expected_lines):
    tracer = ExecutionTracer()

    adapter = LineCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    simple_module.full_for_loop.__code__ = transformer.instrument_module(
        simple_module.full_for_loop.__code__
    )
    tracer.current_thread_identifier = threading.current_thread().ident
    simple_module.full_for_loop(number)
    assert tracer.get_trace().covered_line_ids
    assert (
        tracer.lineids_to_linenos(tracer.get_trace().covered_line_ids) == expected_lines
    )


@pytest.mark.parametrize(
    "number, expected_lines",
    [
        pytest.param(0, {48}),
        pytest.param(1, {48, 49, 50}),
    ],
)
def test_tracking_covered_statements_while_loop(simple_module, number, expected_lines):
    tracer = ExecutionTracer()

    adapter = LineCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    simple_module.while_loop.__code__ = transformer.instrument_module(
        simple_module.while_loop.__code__
    )
    tracer.current_thread_identifier = threading.current_thread().ident
    simple_module.while_loop(number)
    assert tracer.get_trace().covered_line_ids
    assert (
        tracer.lineids_to_linenos(tracer.get_trace().covered_line_ids) == expected_lines
    )


@pytest.mark.parametrize(
    "func,arg,expected_lines",
    [
        ("explicit_return_none", None, {8}),
        ("empty_function", None, {11}),
        ("pass_function", None, {16}),
        ("only_return_on_branch", True, {20, 21}),
        ("only_return_on_branch", False, {20}),
        ("return_on_both_branches", True, {25, 26}),
        ("return_on_both_branches", False, {25, 27}),
        ("pass_on_both", True, {31, 32}),
        ("pass_on_both", False, {31, 34}),
        ("for_return", [], {38}),
        ("for_return", [1], {38, 39}),
    ],
)
def test_expected_covered_lines(func, arg, expected_lines, artificial_none_module):
    tracer = ExecutionTracer()

    adapter = LineCoverageInstrumentation(tracer)
    transformer = InstrumentationTransformer(tracer, [adapter])
    func_object = getattr(artificial_none_module, func)
    func_object.__code__ = transformer.instrument_module(func_object.__code__)
    tracer.current_thread_identifier = threading.current_thread().ident
    func_object(arg)
    assert (
        tracer.lineids_to_linenos(tracer.get_trace().covered_line_ids) == expected_lines
    )


@pytest.fixture()
def dynamic_instr():
    constant_pool = ConstantPool()
    constant_provider = DynamicConstantProvider(
        pool=constant_pool, delegate=EmptyConstantProvider(), probability=1.0
    )
    adapter = DynamicSeedingInstrumentation(constant_provider)
    transformer = InstrumentationTransformer(ExecutionTracer(), [adapter])
    return constant_pool, transformer


@pytest.fixture()
def dummy_module():
    dummy_module = importlib.import_module(
        "tests.fixtures.seeding.dynamicseeding.dynamicseedingdummies"
    )
    dummy_module = importlib.reload(dummy_module)
    return dummy_module


def test_compare_op_int(dynamic_instr, dummy_module):
    dynamic, instr = dynamic_instr
    dummy_module.compare_op_dummy.__code__ = instr.instrument_module(
        dummy_module.compare_op_dummy.__code__
    )
    res = dummy_module.compare_op_dummy(10, 11)

    assert res == 1
    assert dynamic.get_all_constants_for(int) == {10, 11}


def test_compare_op_float(dynamic_instr, dummy_module):
    dynamic, instr = dynamic_instr
    dummy_module.compare_op_dummy.__code__ = instr.instrument_module(
        dummy_module.compare_op_dummy.__code__
    )
    res = dummy_module.compare_op_dummy(1.0, 2.5)

    assert res == 1
    assert dynamic.get_all_constants_for(float) == {1.0, 2.5}


def test_compare_op_string(dynamic_instr, dummy_module):
    dynamic, instr = dynamic_instr
    dummy_module.compare_op_dummy.__code__ = instr.instrument_module(
        dummy_module.compare_op_dummy.__code__
    )
    res = dummy_module.compare_op_dummy("abc", "def")

    assert res == 1
    assert dynamic.get_all_constants_for(str) == {"abc", "def"}


def test_compare_op_other_type(dynamic_instr, dummy_module):
    dynamic, instr = dynamic_instr
    dummy_module.compare_op_dummy.__code__ = instr.instrument_module(
        dummy_module.compare_op_dummy.__code__
    )
    res = dummy_module.compare_op_dummy(True, "def")

    assert res == 1
    assert not dynamic.has_constant_for(int)
    assert not dynamic.has_constant_for(float)
    assert dynamic.has_constant_for(str)
    assert dynamic.get_all_constants_for(str) == {"def"}


@pytest.mark.parametrize(
    "func_name,inp,tracked,result",
    [
        ("isalnum", "alnumtest", "alnumtest!", 0),
        ("isalnum", "alnum_test", "isalnum", 1),
        ("islower", "lower", "LOWER", 0),
        ("islower", "NotLower", "notlower", 1),
        ("isupper", "UPPER", "upper", 0),
        ("isupper", "NotUpper", "NOTUPPER", 1),
        ("isdecimal", "012345", "non_decimal", 0),
        ("isdecimal", "not_decimal", "0123456789", 1),
        ("isalpha", "alpha", "alpha1", 0),
        ("isalpha", "not_alpha", "isalpha", 1),
        ("isdigit", "012345", "012345_", 0),
        ("isdigit", "not_digit", "0", 1),
        ("isidentifier", "is_identifier", "is_identifier!", 0),
        ("isidentifier", "not_identifier!", "is_Identifier", 1),
        ("isnumeric", "44444", "44444A", 0),
        ("isnumeric", "not_numeric", "012345", 1),
        ("isprintable", "printable", f"printable{os.linesep}", 0),
        ("isprintable", f"not_printable{os.linesep}", "is_printable", 1),
        ("isspace", " ", " a", 0),
        ("isspace", "no_space", "   ", 1),
        ("istitle", "Title", "Title AAA", 0),
        ("istitle", "no Title", "Is Title", 1),
    ],
)
def test_string_functions(dynamic_instr, func_name, inp, tracked, result):
    # Some evil trickery
    glob = {}
    loc = {}
    exec(
        f"""def dummy(s):
    if s.{func_name}():
        return 0
    else:
        return 1""",
        glob,
        loc,
    )
    func = loc["dummy"]

    dynamic, instr = dynamic_instr
    func.__code__ = instr.instrument_module(func.__code__)
    assert func(inp) == result
    assert dynamic.has_constant_for(str)
    assert dynamic.get_all_constants_for(str) == {inp, tracked}


@pytest.mark.parametrize(
    "func_name,inp1,inp2,tracked,result",
    [
        ("startswith", "abc", "ab", "ababc", 0),
        ("endswith", "abc", "bc", "abcbc", 0),
    ],
)
def test_binary_string_functions(dynamic_instr, func_name, inp1, inp2, tracked, result):
    # Some evil trickery
    glob = {}
    loc = {}
    exec(
        f"""def dummy(s1,s2):
    if s1.{func_name}(s2):
        return 0
    else:
        return 1""",
        glob,
        loc,
    )
    func = loc["dummy"]

    dynamic, instr = dynamic_instr
    func.__code__ = instr.instrument_module(func.__code__)
    assert func(inp1, inp2) == result
    assert dynamic.has_constant_for(str)
    assert dynamic.get_all_constants_for(str) == {tracked}
