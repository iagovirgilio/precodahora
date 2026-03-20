import pytest
from pydantic import ValidationError

from app.schemas.precos import BuscarPrecosRequest


def test_deve_aceitar_gtins_validos():
    payload = BuscarPrecosRequest(gtins=["7894904015108", "12345670", "123456789012"])
    assert payload.gtins == ["7894904015108", "12345670", "123456789012"]


def test_deve_normalizar_gtin_removendo_caracteres_nao_numericos():
    payload = BuscarPrecosRequest(gtins=["78962-248.02963"])
    assert payload.gtins == ["7896224802963"]


def test_deve_rejeitar_gtin_com_tamanho_invalido():
    with pytest.raises(ValidationError):
        BuscarPrecosRequest(gtins=["1234567"])
