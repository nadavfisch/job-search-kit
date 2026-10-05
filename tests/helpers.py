"""Shared setup for the tests: paths, a throwaway workspace, and running a kit script like the agent does."""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIT = os.path.join(ROOT, "kit")
DEMO = os.path.join(ROOT, "examples", "demo")
TEMPLATES = os.path.join(ROOT, "templates")
DEMO_JOB = "001 - Globex - Operations Automation Lead"
sys.path.insert(0, KIT)


class KitTest(unittest.TestCase):
    def workspace(self, demo=True):
        """A temporary workspace: a copy of examples/demo (or nothing), plus the templates it lacks."""
        ws = tempfile.mkdtemp(prefix="jobkit-test-")
        self.addCleanup(shutil.rmtree, ws, True)
        if demo:
            shutil.copytree(DEMO, ws, dirs_exist_ok=True)
        for name in ("tracker.md", "log.md", "contacts.md", "preferences.md", "answers-bank.md", "search.yaml"):
            if not os.path.exists(os.path.join(ws, name)):
                shutil.copy(os.path.join(TEMPLATES, name), ws)
        for folder in ("jobs", "batches"):
            os.makedirs(os.path.join(ws, folder), exist_ok=True)
        return ws

    def kit(self, script, *args, ws=None, stdin=None):
        """Run kit/<script> with its arguments (and --workspace ws). Returns the CompletedProcess."""
        cmd = [sys.executable, os.path.join(KIT, script), *args] + (["--workspace", ws] if ws else [])
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        return subprocess.run(cmd, input=stdin, capture_output=True, text=True, encoding="utf-8", env=env, timeout=600)

    def assertOK(self, result):
        self.assertEqual(result.returncode, 0, f"exit {result.returncode}\n{result.stdout}\n{result.stderr}")
        return result.stdout


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
