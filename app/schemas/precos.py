import re

from pydantic import BaseModel, Field, field_validator

from app.config import settings


class BuscarPrecosRequest(BaseModel):
    gtins: list[str] = Field(
        ...,
        min_length=1,
        description="Lista de codigos de barras EAN/GTIN.",
        examples=[["7894904015108", "7896224802963"]],
    )
    latitude: float = Field(default=settings.default_latitude)
    longitude: float = Field(default=settings.default_longitude)
    raio: int = Field(default=settings.default_raio, ge=1, le=100)
    horas: int = Field(default=settings.default_horas, ge=1, le=168)

    @field_validator("gtins")
    @classmethod
    def validar_gtins(cls, value: list[str]) -> list[str]:
        tamanhos_validos = {8, 12, 13, 14}
        normalizados: list[str] = []
        for gtin in value:
            apenas_digitos = re.sub(r"\D", "", gtin or "")
            if len(apenas_digitos) not in tamanhos_validos:
                raise ValueError(
                    "Cada GTIN deve conter 8, 12, 13 ou 14 digitos numericos."
                )
            normalizados.append(apenas_digitos)
        return normalizados


class BuscarPrecosResponse(BaseModel):
    consultado_em: str
    localizacao: "LocalizacaoResponse"
    resultados: dict[str, "ResultadoPorGtinResponse"]


class LocalizacaoResponse(BaseModel):
    latitude: float
    longitude: float
    raio_km: int


class LojaResponse(BaseModel):
    nome: str | None = None
    cnpj: str | None = None
    endereco: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    cep: str | None = None
    telefone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distancia_km: float | None = None


class ItemPrecoResponse(BaseModel):
    descricao: str | None = None
    gtin: str
    preco: float
    preco_original: float | None = None
    desconto: float | None = None
    unidade: str | None = None
    foto: str | None = None
    registrado_em: str | None = None
    loja: LojaResponse


class ResultadoPorGtinResponse(BaseModel):
    total_encontrado: int
    top5: list[ItemPrecoResponse]
