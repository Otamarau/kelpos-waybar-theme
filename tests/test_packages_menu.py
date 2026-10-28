import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'packages_menu', Path(__file__).resolve().parents[1] / 'scripts/packages-menu.py')
menu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(menu)


class PackageSearchTests(unittest.TestCase):
    def test_prompt_placeholder_does_not_block_typed_search(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            menu.search_prompt('aur')
        text = output.getvalue()
        self.assertIn('\0no-custom\x1ffalse', text)
        self.assertNotIn('permanent\x1ftrue', text)
        rows = [line.split('\0')[0] for line in text.splitlines() if not line.startswith('\0')]
        self.assertTrue(rows)
        self.assertFalse(any('firefox' in row.casefold() for row in rows))

    def test_custom_input_searches_selected_source(self):
        with patch.dict(menu.os.environ, ROFI_RETV='2',
                        ROFI_DATA=json.dumps({'source': 'aur'})), \
             patch.object(menu.sys, 'argv', ['packages-menu.py', 'firefox']), \
             patch.object(menu, 'search') as search:
            menu.main()
        search.assert_called_once_with('firefox', 'aur')

    def test_source_selection_opens_search_prompt(self):
        with patch.dict(menu.os.environ, ROFI_RETV='1', ROFI_DATA='{}',
                        ROFI_INFO=json.dumps({'action': 'source', 'source': 'repo'})), \
             patch.object(menu, 'search_prompt') as prompt:
            menu.main()
        prompt.assert_called_once_with('repo')


if __name__ == '__main__':
    unittest.main()
