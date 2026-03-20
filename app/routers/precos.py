import logging

import requests
from fastapi import APIRouter, Depends, HTTPException

from app.schemas.precos import BuscarPrecosRequest, BuscarPrecosResponse
from app.services.precos import (
    PrecoDaHoraService,
    UpstreamChallengeError,
    get_preco_da_hora_service,
)

router = APIRouter(prefix="/precos", tags=["Precos"])
logger = logging.getLogger("precodahora.api")


@router.post("/buscar", response_model=BuscarPrecosResponse)
def buscar_precos(
    payload: BuscarPrecosRequest,
    service: PrecoDaHoraService = Depends(get_preco_da_hora_service),
) -> BuscarPrecosResponse:
    try:
        resposta = service.buscar_lista(
            gtins=payload.gtins,
            latitude=payload.latitude,
            longitude=payload.longitude,
            raio=payload.raio,
            horas=payload.horas,
        )
        return BuscarPrecosResponse(**resposta)
    except requests.HTTPError as exc:
        detail = "Falha ao consultar o Preco da Hora."
        if exc.response is not None:
            detail = f"Erro HTTP no servico externo: {exc.response.status_code}"
        logger.exception("upstream_http_error")
        raise HTTPException(status_code=502, detail=detail) from exc
    except requests.RequestException as exc:
        logger.exception("upstream_network_error")
        raise HTTPException(
            status_code=503,
            detail="Erro de rede ao consultar o servico externo.",
        ) from exc
    except UpstreamChallengeError as exc:
        logger.exception("upstream_challenge_detected")
        raise HTTPException(
            status_code=503,
            detail=(
                "Upstream com captcha/challenge temporario. "
                "Tente novamente em instantes."
            ),
        ) from exc
    except RuntimeError as exc:
        logger.exception("internal_runtime_error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
