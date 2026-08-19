import builtins
import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path


if 'requests' not in sys.modules:
    sys.modules['requests'] = types.SimpleNamespace(
        session=lambda: types.SimpleNamespace(headers={})
    )

spec = importlib.util.spec_from_file_location('ulearning_cmd', Path(__file__).with_name('ulearning-cmd.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_account_switching():
    with tempfile.TemporaryDirectory() as temp_dir:
        app.CONFIG_PATH = str(Path(temp_dir) / 'ulearning-cmd.json')
        Path(app.CONFIG_PATH).write_text(json.dumps({
            'users': {
                '2021123456789': {'password': 'old'},
                'dgut2023000000000': {'password': 'new'},
            },
            'activeUser': 'dgut2021123456789',
        }), encoding='utf-8')

        app.users = {}
        assert app.loadCfg() == 1
        assert app.loginName == 'dgut2021123456789'
        assert '2021123456789' not in app.users

        target_user = 'dgut2023000000000'
        target_index = list(app.users).index(target_user) + 1
        original_input = builtins.input
        builtins.input = lambda _: str(target_index)
        try:
            app.chooseUser()
        finally:
            builtins.input = original_input

        assert app.loginName == target_user


if __name__ == '__main__':
    test_account_switching()
    print('account switching: ok')
