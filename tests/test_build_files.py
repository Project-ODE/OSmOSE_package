import OSmOSE.timestamps as tm
import re
import pytest
from OSmOSE.utils.audio_utils import is_supported_audio_format
from pathlib import Path



@pytest.mark.unit
def test_convert_template_to_re():
    raw_all = "".join(tm.__converter.keys())
    simple_template = "%Y/%m/%d"
    simple_text = "sample_file_2017/02/24.txt"
    invalid_simple_text = "sample_file_2049/25/01"
    complex_template = "y_%Y-m_%m, %I%p."
    complex_text = " y_2017-m_02, 11AM%"

    assert tm.convert_template_to_re(raw_all) == "".join(tm.__converter.values())
    simple_res = tm.convert_template_to_re(simple_template)
    assert re.search(simple_res, simple_text)[0] == "2017/02/24"
    assert re.search(simple_res, invalid_simple_text) == None
    complex_res = tm.convert_template_to_re(complex_template)
    assert re.search(complex_res, complex_text)[0] == "y_2017-m_02, 11AM%"
