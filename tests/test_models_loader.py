from __future__ import annotations


def test_models_has_default():
    from kai_code.model import get_default_model

    assert isinstance(get_default_model(), str)
    assert get_default_model()
