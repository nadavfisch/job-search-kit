"""How the scripts are built: each one does its work in main(), so importing it (a test, another script) runs nothing."""

import contextlib
import io
import os
import runpy
import sys
import unittest
from unittest import mock

from helpers import KIT


class Scripts(unittest.TestCase):
    def test_importing_a_script_runs_nothing(self):
        for name in sorted(f for f in os.listdir(KIT) if f.endswith(".py")):
            out = io.StringIO()
            with self.subTest(name), mock.patch.object(sys, "argv", [name]), contextlib.redirect_stdout(out):
                module = runpy.run_path(os.path.join(KIT, name), run_name=name[:-3])  # not "__main__"
                self.assertEqual(out.getvalue(), "")
                if name != "common.py":  # the shared helpers, not a script
                    self.assertTrue(callable(module.get("main")), f"{name} has no main()")


if __name__ == "__main__":
    unittest.main()
