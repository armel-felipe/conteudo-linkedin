from pathlib import Path

import scheduling_contract


def test_plain_pytest_can_import_root_modules():
    assert Path("scheduling_contract.py").is_file()
    assert scheduling_contract.__file__.endswith("scheduling_contract.py")
