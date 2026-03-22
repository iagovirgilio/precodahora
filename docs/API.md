# API Contract

## Endpoint principal

### `POST /api/v1/precos/buscar`

Consulta os dados de precos para uma lista de GTINs e retorna:

- `consultado_em`
- `localizacao`
- `resultados` por GTIN

Cabecalhos de resposta (observabilidade do cache e do upstream):

| Cabecalho | Significado |
|-----------|-------------|
| `X-Cache` | `HIT` (todos os GTINs do cache), `MISS` (nenhum hit) ou `MIXED` |
| `X-Cache-Hits` | Quantidade de consultas atendidas pelo cache interno |
| `X-Cache-Misses` | Quantidade de consultas que foram ao portal |
| `X-Upstream-Posts` | POSTs HTTP ao portal na requisicao (401 com retry conta 2 no GTIN afetado) |

O mesmo resumo e registrado em log (`precos_buscar ... x_cache=...`) no logger `precodahora.api`.

### Request body

```json
{
  "gtins": ["7894904015108"],
  "latitude": -12.2690245,
  "longitude": -38.9295865,
  "raio": 15,
  "horas": 72
}
```

### Response body (resumido)

```json
{
  "consultado_em": "2026-03-20T13:21:28Z",
  "localizacao": {
    "latitude": -12.2690245,
    "longitude": -38.9295865,
    "raio_km": 15
  },
  "resultados": {
    "7894904015108": {
      "total_encontrado": 43,
      "top5": [
        {
          "descricao": "FILE PEITO FGO SEARA",
          "gtin": "7894904015108",
          "preco": 19.9,
          "preco_original": null,
          "desconto": null,
          "unidade": "BDJ9",
          "foto": "https://api.precodahora.ba.gov.br/v1/images/7894904015108",
          "registrado_em": "2026-03-20T13:02:25Z",
          "loja": {
            "nome": "ATACADAO",
            "cnpj": "93209765054985",
            "endereco": "AVENIDA EDUARDO FROES DA MOTA, 5500",
            "bairro": "SOBRADINHO",
            "cidade": "FEIRA DE SANTANA",
            "uf": "BA",
            "cep": "44021215",
            "telefone": null,
            "latitude": -12.2322007,
            "longitude": -38.9736466,
            "distancia_km": 2.8
          }
        }
      ]
    }
  }
}
```

## Endpoint de saude

### `GET /health`

Retorna status da API e alguns parametros operacionais (para conferencia de deploy), por exemplo:

- `cache_ttl_seconds`: tempo maximo para reutilizar resposta da fonte externa.
- `cache_max_entries`: tamanho maximo do cache em memoria (LRU); `0` significa sem limite de entradas.
- `rate_limit_window_seconds`: janela em segundos do rate limit por IP (ver `429`).

Exemplo:

```json
{
  "status": "ok",
  "cache_ttl_seconds": 900,
  "cache_max_entries": 512,
  "rate_limit_window_seconds": 60
}
```

## Codigos de status

- `200`: sucesso
- `422`: payload invalido
- `429`: rate limit excedido
- `502`: erro HTTP na fonte externa
- `503`: erro de rede com a fonte externa
- `500`: erro interno inesperado
