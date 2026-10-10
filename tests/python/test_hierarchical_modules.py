"""Unit tests for hierarchical module and interface namespaces with aliasing."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DRIVER = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

import quest.ast as ast
from quest.build.manifest import read_qm
from quest.codegen.compiler_runner import compile_c_to_object, run_binary
from quest.grammar import parse_quest_program
from quest.interface_compiler import compile_interface_file
from quest.module_compiler import compile_module_file
from quest.pipeline import CompilerContext, CompilerOptions, default_pipeline
from quest.runtime import QInt
from quest.tokenizer import Tokenizer
from quest.tokens import SourceMap
from quest_driver import run_compile, run_driver


def _parse(code: str) -> ast.Program:
    source_map = SourceMap(code, "<test>")
    tokens = Tokenizer(code, "<test>").tokenize_all()
    prog = parse_quest_program(tokens, source_map)
    assert isinstance(prog, ast.Program)
    return prog


class TestHierarchicalModuleSyntax(unittest.TestCase):
    """Tests syntax variations for hierarchical imports and aliasing."""

    def test_parse_dual_alias(self) -> None:
        prog = _parse("import rnd : Rnd = util/random : util/Random;")
        self.assertEqual(len(prog.phrases), 1)
        imp = prog.phrases[0]
        self.assertIsInstance(imp, ast.ImportPhrase)
        self.assertEqual(len(imp.items), 1)
        item = imp.items[0]
        self.assertEqual(item.names, ("rnd",))
        self.assertEqual(item.interface_name, "Rnd")
        self.assertEqual(item.effective_module_paths, ("util/random",))
        self.assertEqual(item.effective_interface_path, "util/Random")

    def test_parse_module_alias_only(self) -> None:
        prog = _parse("import rnd = util/random : util/Random;")
        item = prog.phrases[0].items[0]
        self.assertEqual(item.names, ("rnd",))
        self.assertEqual(item.interface_name, "Random")
        self.assertEqual(item.effective_module_paths, ("util/random",))
        self.assertEqual(item.effective_interface_path, "util/Random")

    def test_parse_interface_alias_with_module(self) -> None:
        prog = _parse("import :Rnd = util/random : util/Random;")
        item = prog.phrases[0].items[0]
        self.assertEqual(item.names, ("random",))
        self.assertEqual(item.interface_name, "Rnd")
        self.assertEqual(item.effective_module_paths, ("util/random",))
        self.assertEqual(item.effective_interface_path, "util/Random")

    def test_parse_interface_only_with_alias(self) -> None:
        prog = _parse("import :Rnd = :util/Random;")
        item = prog.phrases[0].items[0]
        self.assertEqual(item.names, ())
        self.assertEqual(item.interface_name, "Rnd")
        self.assertEqual(item.effective_module_paths, ())
        self.assertEqual(item.effective_interface_path, "util/Random")

    def test_parse_interface_only_unaliased(self) -> None:
        prog = _parse("import :util/Random;")
        item = prog.phrases[0].items[0]
        self.assertEqual(item.names, ())
        self.assertEqual(item.interface_name, "Random")
        self.assertEqual(item.effective_module_paths, ())
        self.assertEqual(item.effective_interface_path, "util/Random")

    def test_parse_hierarchical_unaliased(self) -> None:
        prog = _parse("import util/random : util/Random;")
        item = prog.phrases[0].items[0]
        self.assertEqual(item.names, ("random",))
        self.assertEqual(item.interface_name, "Random")
        self.assertEqual(item.effective_module_paths, ("util/random",))
        self.assertEqual(item.effective_interface_path, "util/Random")

    def test_parse_comma_separated_aliased_entries(self) -> None:
        prog = _parse("import r1 = p1/mod1, r2 = p2/mod2 : util/Random;")
        item = prog.phrases[0].items[0]
        self.assertEqual(item.names, ("r1", "r2"))
        self.assertEqual(item.interface_name, "Random")
        self.assertEqual(item.effective_module_paths, ("p1/mod1", "p2/mod2"))
        self.assertEqual(item.effective_interface_path, "util/Random")

    def test_parse_deep_hierarchy(self) -> None:
        prog = _parse("import a/b/c/d : A/B/C/D;")
        item = prog.phrases[0].items[0]
        self.assertEqual(item.names, ("d",))
        self.assertEqual(item.interface_name, "D")
        self.assertEqual(item.effective_module_paths, ("a/b/c/d",))
        self.assertEqual(item.effective_interface_path, "A/B/C/D")

    def test_division_operator_undisturbed(self) -> None:
        prog = _parse("let x: Int = 10 / 2;")
        self.assertEqual(len(prog.phrases), 1)
        binding = prog.phrases[0]
        self.assertIsInstance(binding, ast.LetValueBinding)
        self.assertIsInstance(binding.value, ast.ExprInfix)
        self.assertEqual(binding.value.op, "/")


class TestHierarchicalModuleExecution(unittest.TestCase):
    """End-to-end tests for hierarchical module loading, typechecking, and execution."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp(prefix="quest_hier_test_")
        self.root = Path(self.test_dir)
        self.pipeline = default_pipeline()

    def tearDown(self) -> None:
        shutil.rmtree(self.test_dir)

    def _run_pipeline(self, file_path: Path, options: CompilerOptions | None = None):
        source_text = file_path.read_text(encoding="utf-8")
        ctx = CompilerContext.create(source_text, file_name=str(file_path), options=options)
        res = self.pipeline.execute(source_text, file_name=str(file_path), options=options, ctx=ctx)
        return res, ctx

    def test_hierarchical_modules_interpreter(self) -> None:
        util_dir = self.root / "util"
        util_dir.mkdir(parents=True)

        (util_dir / "helper.int.quest").write_text(
            "interface Helper\n"
            "export\n"
            "    offset: Int\n"
            "end;\n",
            encoding="utf-8",
        )
        (util_dir / "helper.mod.quest").write_text(
            "module helper : Helper\n"
            "export\n"
            "    let offset: Int = 5;\n"
            "end;\n",
            encoding="utf-8",
        )

        (util_dir / "math.int.quest").write_text(
            "interface Math\n"
            "export\n"
            "    add(a: Int b: Int): Int\n"
            "    addWithOffset(a: Int): Int\n"
            "end;\n",
            encoding="utf-8",
        )
        # Sibling import without prefix inside util/math.mod.quest
        (util_dir / "math.mod.quest").write_text(
            "module math : Math\n"
            "import helper : Helper;\n"
            "export\n"
            "    let add(a: Int b: Int): Int = a + b;\n"
            "    let addWithOffset(a: Int): Int = add(a helper.offset);\n"
            "end;\n",
            encoding="utf-8",
        )

        main_quest = self.root / "main.quest"
        main_quest.write_text(
            "import m : M = util/math : util/Math;\n"
            "let res1: Int = m.add(10 20);\n"
            "let res2: Int = m.addWithOffset(100);\n"
            "let result: Int = res1 + res2;\n",
            encoding="utf-8",
        )

        options = CompilerOptions(include_paths=[self.root])
        res, ctx = self._run_pipeline(main_quest, options=options)
        self.assertTrue(res.success, f"Pipeline diagnostics: {res.diagnostics}")
        val = ctx.runtime_env.lookup("result")
        self.assertEqual(val, QInt(135))

    def test_hierarchical_manifest_type_alias_interpreter(self) -> None:
        geom_dir = self.root / "geom"
        geom_dir.mkdir(parents=True)

        (geom_dir / "point.int.quest").write_text(
            "interface Point\n"
            "export\n"
            "    Def T = Record x: Int y: Int end\n"
            "    make(x: Int y: Int): T\n"
            "    sumCoords(p: T): Int\n"
            "end;\n",
            encoding="utf-8",
        )
        (geom_dir / "point.mod.quest").write_text(
            "module point : Point\n"
            "export\n"
            "    Let T = Record x: Int y: Int end;\n"
            "    let make(x: Int y: Int): T = record x = x y = y end;\n"
            "    let sumCoords(p: T): Int = p.x + p.y;\n"
            "end;\n",
            encoding="utf-8",
        )

        main_quest = self.root / "main.quest"
        main_quest.write_text(
            "import pt : Pt = geom/point : geom/Point;\n"
            "let p: Pt_T = pt.make(15 27);\n"
            "let result: Int = pt.sumCoords(p);\n",
            encoding="utf-8",
        )

        options = CompilerOptions(include_paths=[self.root])
        res, ctx = self._run_pipeline(main_quest, options=options)
        self.assertTrue(res.success, f"Pipeline diagnostics: {res.diagnostics}")
        val = ctx.runtime_env.lookup("result")
        self.assertEqual(val, QInt(42))

    def test_hierarchical_c_compilation_and_execution(self) -> None:
        util_dir = self.root / "util"
        util_dir.mkdir(parents=True)

        intf_file = util_dir / "calc.int.quest"
        intf_file.write_text(
            "interface Calc\n"
            "export\n"
            "    multiply(a: Int b: Int): Int\n"
            "end;\n",
            encoding="utf-8",
        )

        mod_file = util_dir / "calc.mod.quest"
        mod_file.write_text(
            "module calc : Calc\n"
            "export\n"
            "    let multiply(a: Int b: Int): Int = a * b;\n"
            "end;\n",
            encoding="utf-8",
        )

        # Precompile interface and module
        compile_interface_file(intf_file, output_dir=util_dir, include_paths=[self.root])
        compile_module_file(mod_file, output_dir=util_dir, include_paths=[self.root])

        # Remove source to ensure client links against precompiled .o
        mod_file.unlink()

        # Verify compiled artifacts were produced with correct paths
        self.assertTrue((util_dir / "calc.int.h").is_file())
        self.assertTrue((util_dir / "calc.qi").is_file())
        self.assertTrue((util_dir / "calc.o").is_file())

        main_quest = self.root / "main.quest"
        main_quest.write_text(
            "import c = util/calc : util/Calc;\n"
            "import writer : Writer;\n"
            "import conv : Conv;\n"
            "writer.putString(writer.output conv.int(c.multiply(6 7)));\n",
            encoding="utf-8",
        )

        out_bin = self.root / "main_bin"
        ret = run_compile([
            str(main_quest),
            str(util_dir / "calc.o"),
            "-o", str(out_bin),
            "-I", str(self.root),
            "--build-dir", str(self.root / ".build"),
        ])
        self.assertEqual(ret, 0)
        self.assertTrue(out_bin.exists())

        proc = run_binary(out_bin)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "42")

    def test_module_named_after_c_standard_header(self) -> None:
        """A generated header for util/Math must not shadow <math.h>, though build/util is on the -I path."""
        util_dir = self.root / "util"
        util_dir.mkdir(parents=True)
        (util_dir / "math.int.quest").write_text(
            "interface Math\n"
            "export\n"
            "    square(a: Int): Int\n"
            "end;\n",
            encoding="utf-8",
        )
        (util_dir / "math.mod.quest").write_text(
            "module math : Math\n"
            "export\n"
            "    let square(a: Int): Int = a * a;\n"
            "end;\n",
            encoding="utf-8",
        )
        main_quest = self.root / "main.quest"
        main_quest.write_text(
            "import m = util/math : util/Math;\n"
            "import writer : Writer;\n"
            "import conv : Conv;\n"
            "writer.putString(writer.output conv.int(m.square(7)));\n",
            encoding="utf-8",
        )

        build_dir = self.root / "build"
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            ret = run_driver([
                "--stop-after", "run_c_compiled",
                str(main_quest),
                "-I", str(self.root),
                "--build-dir", str(build_dir),
            ])
        self.assertEqual(ret, 0, out.getvalue())
        self.assertIn("49", out.getvalue())
        self.assertTrue((build_dir / "util" / "math.int.h").is_file())
        self.assertTrue((build_dir / "util" / "math.mod.c").is_file())
        self.assertFalse((build_dir / "util" / "math.h").exists())

    def test_same_named_interfaces_in_different_directories_share_a_c_unit(self) -> None:
        """util/Calc and a top-level Calc get distinct include guards and typedefs, so one C unit can include both."""
        util_dir = self.root / "util"
        util_dir.mkdir(parents=True)
        util_intf = util_dir / "calc.int.quest"
        util_intf.write_text("interface Calc\nexport\n    combine(a: Int b: Int): Int\nend;\n", encoding="utf-8")
        top_intf = self.root / "calc.int.quest"
        top_intf.write_text("interface Calc\nexport\n    combine(a: Int): Int\nend;\n", encoding="utf-8")

        build_dir = self.root / ".build"
        util_h, _ = compile_interface_file(util_intf, include_paths=[self.root], build_dir=build_dir)
        top_h, _ = compile_interface_file(top_intf, include_paths=[self.root], build_dir=build_dir)
        self.assertEqual(util_h, build_dir.resolve() / "util" / "calc.int.h")
        self.assertEqual(top_h, build_dir.resolve() / "calc.int.h")
        self.assertIn("#ifndef QUEST_INTF_UTIL__CALC_H", util_h.read_text(encoding="utf-8"))
        self.assertIn("#ifndef QUEST_INTF_CALC_H", top_h.read_text(encoding="utf-8"))

        # Both headers' declarations must survive in one translation unit.
        c_file = self.root / "both.c"
        c_file.write_text(
            '#include "util/calc.int.h"\n'
            '#include "calc.int.h"\n'
            "static QInt mul(QInt a, QInt b) { return a * b; }\n"
            "static QInt inc(QInt a) { return a + 1; }\n"
            "quest_sig_util__Calc_combine util_combine = mul;\n"
            "quest_sig_Calc_combine top_combine = inc;\n",
            encoding="utf-8",
        )
        compile_c_to_object(c_file, self.root / "both.o", include_paths=[build_dir])

    # util/calc and a top-level calc each implement their own Calc and import a sibling helper : Helper,
    # which also names different modules and interfaces in the two directories.
    SAME_NAMED_FILES = {
        "util/helper.int.quest": "interface Helper\nexport\n    offset: Int\nend;\n",
        "util/helper.mod.quest": "module helper : Helper\nexport\n    let offset: Int = 5;\nend;\n",
        "helper.int.quest": "interface Helper\nexport\n    bonus: Int\nend;\n",
        "helper.mod.quest": "module helper : Helper\nexport\n    let bonus: Int = 1000;\nend;\n",
        "util/calc.int.quest": "interface Calc\nexport\n    combine(a: Int b: Int): Int\nend;\n",
        "util/calc.mod.quest": (
            "module calc : Calc\n"
            "import helper : Helper;\n"
            "export\n"
            "    let combine(a: Int b: Int): Int = helper.offset + a * b;\n"
            "end;\n"
        ),
        "calc.int.quest": "interface Calc\nexport\n    combine(a: Int): Int\nend;\n",
        "calc.mod.quest": (
            "module calc : Calc\n"
            "import helper : Helper;\n"
            "export\n"
            "    let combine(a: Int): Int = a + helper.bonus;\n"
            "end;\n"
        ),
    }

    # Each order of imports must resolve every name to the right file; 47 + 1100 + 1000.
    SAME_NAMED_IMPORT_ORDERS = (
        ("import helper : Helper;", "import um : UCalc = util/calc : util/Calc;", "import m = calc : Calc;"),
        ("import m = calc : Calc;", "import um : UCalc = util/calc : util/Calc;", "import helper : Helper;"),
        ("import um : UCalc = util/calc : util/Calc;", "import m = calc : Calc;", "import helper : Helper;"),
    )

    def _write_same_named_modules(self, root: Path, imports: tuple[str, ...], result_stmt: str) -> Path:
        for rel, text in self.SAME_NAMED_FILES.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        main_quest = root / "main.quest"
        main_quest.write_text(
            "\n".join(imports) + "\n"
            "let result: Int = um.combine(6 7) + m.combine(100) + helper.bonus;\n" + result_stmt,
            encoding="utf-8",
        )
        return main_quest

    def test_same_named_modules_in_different_directories_interpreter(self) -> None:
        for i, imports in enumerate(self.SAME_NAMED_IMPORT_ORDERS):
            with self.subTest(imports=imports):
                root = self.root / f"order{i}"
                main_quest = self._write_same_named_modules(root, imports, "")
                res, ctx = self._run_pipeline(main_quest, options=CompilerOptions(include_paths=[root]))
                self.assertTrue(res.success, f"Pipeline diagnostics: {res.diagnostics}")
                self.assertEqual(ctx.runtime_env.lookup("result"), QInt(2147))

    def test_same_named_modules_in_different_directories_c_compiled(self) -> None:
        for i, imports in enumerate(self.SAME_NAMED_IMPORT_ORDERS):
            with self.subTest(imports=imports):
                root = self.root / f"order{i}"
                main_quest = self._write_same_named_modules(
                    root,
                    ("import writer : Writer;", "import conv : Conv;") + imports,
                    "writer.putString(writer.output conv.int(result));\n",
                )
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
                    ret = run_driver([
                        "--stop-after", "run_c_compiled",
                        str(main_quest),
                        "-I", str(root),
                        "--build-dir", str(root / "build"),
                    ])
                self.assertEqual(ret, 0, out.getvalue())
                self.assertIn("2147", out.getvalue())


def _write_units(directory: Path, units: dict[str, str]) -> None:
    for name, text in units.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


# util/arith imports its sibling util/helper by its bare name.
ARITH_UNITS = {
    "util/helper.int.quest": "interface Helper\nexport\n    offset: Int\nend;\n",
    "util/helper.mod.quest": "module helper : Helper\nexport\n    let offset: Int = 5;\nend;\n",
    "util/arith.int.quest": "interface Arith\nexport\n    addWithOffset(a: Int): Int\nend;\n",
    "util/arith.mod.quest": (
        "module arith : Arith\n"
        "import helper : Helper;\n"
        "export\n"
        "    let addWithOffset(a: Int): Int = a + helper.offset;\n"
        "end;\n"
    ),
    "main.quest": "import m : M = util/arith : util/Arith;\nm.addWithOffset(100)\n",
}

COUNTER_UNITS = {
    "counter.int.quest": "interface Counter\nexport\n    T::TYPE\n    new(n: Int): T\n    get(c: T): Int\nend;\n",
    "counter.mod.quest": (
        "module counter : Counter\n"
        "export\n"
        "    Let T = Int;\n"
        "    let new(n: Int): T = n;\n"
        "    let get(c: T): Int = c * {scale};\n"
        "end;\n"
    ),
    "main.quest": "import counter : Counter;\ncounter.get(counter.new(7))\n",
}


class TestCanonicalNamesInCCompilation(unittest.TestCase):
    """Units found by sibling search have one canonical name in C compilation (docs/modules.md §2.3).

    The importer, the unit's own module header, the .qm manifests, and the mangled C symbols must agree on it,
    however the unit was found and whatever include paths are given.
    """

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="quest_canon_test_")).resolve()
        self.build_dir = Path(tempfile.mkdtemp(prefix="quest_canon_build_")).resolve()

    def tearDown(self) -> None:
        shutil.rmtree(self.root)
        shutil.rmtree(self.build_dir)

    def _run(self, program: Path, phase: str, *args: str) -> str:
        proc = self._run_process(program, phase, *args)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout.strip()

    def _run_process(self, program: Path, phase: str, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
        return subprocess.run(
            [sys.executable, str(DRIVER), "--stop-after", phase, "--build-dir", str(self.build_dir), *args,
             "--print-result", str(program)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=program.parent,
        )

    def _assert_c_matches_interpreter(self, program: Path, expected: str, *args: str) -> None:
        self.assertEqual(self._run(program, "interpret", *args), expected)
        self.assertEqual(self._run(program, "run_c_compiled", *args), expected)

    def test_hierarchical_import_outside_include_roots(self) -> None:
        """A program under no include root names its units relative to its own directory."""
        _write_units(self.root, ARITH_UNITS)
        self._assert_c_matches_interpreter(self.root / "main.quest", "105 : Int")
        manifest = read_qm(self.build_dir / "util" / "arith.qm")
        assert manifest is not None
        self.assertEqual(manifest.name, "util/arith")
        self.assertEqual(manifest.interface, "util/Arith")
        self.assertEqual([m.name for m in manifest.imported_modules], ["util/helper"])
        self.assertEqual([m.interface for m in manifest.imported_modules], ["util/Helper"])

    def test_sibling_import_in_hierarchical_module_with_include_root(self) -> None:
        """A sibling import inside util/ links against util/helper, not a flat helper."""
        _write_units(self.root, ARITH_UNITS)
        self._assert_c_matches_interpreter(self.root / "main.quest", "105 : Int", "-I", str(self.root))
        manifest = read_qm(self.build_dir / "util" / "helper.qm")
        assert manifest is not None
        self.assertEqual(manifest.name, "util/helper")

    def test_sibling_import_under_project_directory(self) -> None:
        """Units beside a program in the project directory are named relative to it, with or without -I."""
        # Under build/ (ignored by git), with only letters and digits in its path as canonical names require.
        # The directory is left behind (empty), since concurrent test runs may share it.
        program_dir = ROOT_DIR / "build" / f"canonical{uuid.uuid4().hex}"
        program_dir.mkdir(parents=True)
        try:
            _write_units(program_dir, {k: v.format(scale=2) for k, v in COUNTER_UNITS.items()})
            relative = program_dir.relative_to(ROOT_DIR).as_posix()
            main = program_dir / "main.quest"
            self._assert_c_matches_interpreter(main, "14 : Int")
            manifest = read_qm(self.build_dir / relative / "counter.qm")
            assert manifest is not None
            self.assertEqual(manifest.name, f"{relative}/counter")
            self.assertEqual(manifest.interface, f"{relative}/Counter")

            # A deeper include root is preferred to the project directory.
            shutil.rmtree(self.build_dir)
            self._assert_c_matches_interpreter(main, "14 : Int", "-I", str(program_dir.parent))
            manifest = read_qm(self.build_dir / program_dir.name / "counter.qm")
            assert manifest is not None
            self.assertEqual(manifest.name, f"{program_dir.name}/counter")
            self.assertEqual(manifest.interface, f"{program_dir.name}/Counter")
        finally:
            shutil.rmtree(program_dir)

    def test_path_with_other_characters_is_an_error(self) -> None:
        """Directory and file names in canonical names may contain only letters and digits."""
        _write_units(self.root / "x-y", {k: v.format(scale=2) for k, v in COUNTER_UNITS.items()})
        for phase in ("interpret", "run_c_compiled"):
            proc = self._run_process(self.root / "x-y" / "main.quest", phase, "-I", str(self.root))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("'x-y' contains characters other than letters and digits", proc.stdout + proc.stderr)

    def test_units_with_the_same_base_name_in_one_program(self) -> None:
        """counter and util/counter are different units, whichever is imported first and by whom."""
        _write_units(self.root, {k: v.format(scale=1) for k, v in COUNTER_UNITS.items() if k != "main.quest"})
        _write_units(self.root, {
            "util/counter.int.quest": "interface Counter\nexport\n    step: Int\nend;\n",
            "util/counter.mod.quest": "module counter : Counter\nexport\n    let step = 100;\nend;\n",
            "util/arith.int.quest": "interface Arith\nexport\n    bump(x: Int): Int\nend;\n",
            "util/arith.mod.quest": (
                "module arith : Arith\nimport counter: Counter;\nexport\n"
                "    let bump(x: Int): Int = x + counter.step;\nend;\n"
            ),
            "first.quest": (
                "import counter: Counter;\nimport arith = util/arith : util/Arith;\n"
                "arith.bump(counter.get(counter.new(11)))\n"
            ),
            "last.quest": (
                "import arith = util/arith : util/Arith;\nimport counter: Counter;\n"
                "arith.bump(counter.get(counter.new(11)))\n"
            ),
            "both.quest": (
                "import counter: Counter;\nimport c2 = util/counter : util/Counter;\n"
                "counter.get(counter.new(c2.step))\n"
            ),
        })
        self._assert_c_matches_interpreter(self.root / "first.quest", "111 : Int")
        self._assert_c_matches_interpreter(self.root / "last.quest", "111 : Int")
        self._assert_c_matches_interpreter(self.root / "both.quest", "100 : Int")

    def test_same_unit_name_in_two_directories_shares_build_directory(self) -> None:
        """Programs in different directories under one include root keep their same-named units apart."""
        for sub, scale in (("one", 2), ("two", 3)):
            _write_units(self.root / sub, {k: v.format(scale=scale) for k, v in COUNTER_UNITS.items()})
        include = ("-I", str(self.root))
        self._assert_c_matches_interpreter(self.root / "one" / "main.quest", "14 : Int", *include)
        self._assert_c_matches_interpreter(self.root / "two" / "main.quest", "21 : Int", *include)
        self.assertTrue((self.build_dir / "one" / "counter.o").is_file())
        self.assertTrue((self.build_dir / "two" / "counter.o").is_file())



if __name__ == "__main__":
    unittest.main()
