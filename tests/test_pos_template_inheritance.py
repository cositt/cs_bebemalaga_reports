"""Check that the POS (OWL) template extensions apply on the installed Odoo build.

OWL resolves ``t-inherit`` in the browser, so a broken xpath does not show up
on the server: the POS just renders a blank screen the first time it draws an
order line. This script replays that inheritance step against the
``point_of_sale`` sources of the Odoo it runs on.

It is a standalone script (there is no ``tests/__init__.py``, so Odoo's test
runner ignores it). Run it inside the same image as production:

    docker run --rm --entrypoint python3 \
        -v "$PWD":/mnt/cs_bebemalaga_reports:ro odoo:<tag> \
        /mnt/cs_bebemalaga_reports/tests/test_pos_template_inheritance.py
"""

import copy
import os
import re
import sys
import unittest
from pathlib import Path

from lxml import etree

MODULE_DIR = Path(__file__).resolve().parent.parent
MODULE_TEMPLATES = sorted((MODULE_DIR / "static/src/app").rglob("*.xml"))
MODULE_SCRIPTS = sorted((MODULE_DIR / "static/src/app").rglob("*.js"))
HASCLASS = re.compile(r"hasclass\(([^)]*)\)")


def _pos_source_dir():
    override = os.environ.get("POS_SRC")
    if override:
        return Path(override)
    import odoo.addons.point_of_sale as pos

    return Path(pos.__file__).resolve().parent / "static/src"


def _load_templates(files):
    templates = {}
    for path in files:
        root = etree.parse(str(path)).getroot()
        for node in root.iter("t"):
            name = node.get("t-name")
            if name:
                templates[name] = node
    return templates


def _owl_xpath(expr):
    """Translate OWL's ``hasclass()`` helper into plain XPath 1.0."""

    def repl(match):
        classes = [c.strip().strip("'\"") for c in match.group(1).split(",")]
        return " and ".join(
            f"contains(concat(' ', normalize-space(@class), ' '), ' {c} ')"
            for c in classes
        )

    return HASCLASS.sub(repl, expr)


def _apply_inheritance(base, extension):
    """Minimal port of @web/core/template_inheritance applyInheritance."""
    result = etree.fromstring(etree.tostring(base))
    for spec in extension:
        if not isinstance(spec.tag, str) or spec.tag != "xpath":
            continue
        expr = spec.get("expr")
        found = result.xpath(_owl_xpath(expr))
        if not found:
            raise AssertionError(f"xpath {expr!r} cannot be located")
        target = found[0]
        children = [copy.deepcopy(c) for c in spec]
        position = spec.get("position", "inside")
        if position == "attributes":
            for attr in spec.iter("attribute"):
                target.set(attr.get("name"), attr.text or "")
        elif position == "replace":
            parent = target.getparent()
            index = parent.index(target)
            parent.remove(target)
            for offset, child in enumerate(children):
                parent.insert(index + offset, child)
        elif position == "before":
            parent = target.getparent()
            index = parent.index(target)
            for offset, child in enumerate(children):
                parent.insert(index + offset, child)
        elif position == "after":
            parent = target.getparent()
            index = parent.index(target) + 1
            for offset, child in enumerate(children):
                parent.insert(index + offset, child)
        elif position == "inside":
            for child in children:
                target.append(child)
        else:
            raise AssertionError(f"unsupported position {position!r}")
    return result


class TestPosTemplateInheritance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        src = _pos_source_dir()
        cls.core_js = "\n".join(p.read_text() for p in src.rglob("*.js"))
        cls.core = _load_templates(src.rglob("*.xml"))
        cls.extensions = [
            node
            for node in _load_templates(MODULE_TEMPLATES).values()
            if node.get("t-inherit")
        ]

    def test_there_are_extensions_to_check(self):
        self.assertTrue(self.extensions)

    def test_every_xpath_applies(self):
        for ext in self.extensions:
            parent = ext.get("t-inherit")
            with self.subTest(template=ext.get("t-name")):
                self.assertIn(parent, self.core, f"{parent} not in this build")
                _apply_inheritance(self.core[parent], ext)

    def test_orderline_does_not_use_undefined_vals(self):
        """``vals``/``lineScreenValues`` only exist in newer Odoo 19 builds."""
        if "lineScreenValues" in self.core_js:
            self.skipTest("this build provides lineScreenValues")
        for ext in self.extensions:
            if ext.get("t-inherit") != "point_of_sale.Orderline":
                continue
            merged = etree.tostring(
                _apply_inheritance(self.core[ext.get("t-inherit")], ext)
            ).decode()
            self.assertNotRegex(merged, r"\bvals\.")
        for script in MODULE_SCRIPTS:
            self.assertNotRegex(
                script.read_text(),
                r"get\s+lineScreenValues|\.lineScreenValues",
                script.name,
            )

    def test_receipt_line_keeps_module_format(self):
        ext = next(
            e for e in self.extensions if e.get("t-inherit") == "point_of_sale.Orderline"
        )
        merged = _apply_inheritance(self.core["point_of_sale.Orderline"], ext)
        info = merged.xpath("//li[contains(@class, 'bm-line-info')]")
        self.assertEqual(len(info), 1, "reference/unit price row missing")
        discount_li = merged.xpath("//li[@t-if and contains(@t-if, 'line.discount')]")
        self.assertTrue(discount_li)
        self.assertIn("!bmIsReceipt", discount_li[0].get("t-if"))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    sys.exit(not result.wasSuccessful())
