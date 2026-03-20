"""
Script de diagnóstico — inspeciona todos os cookies e headers
recebidos do precodahora.ba.gov.br para identificar o CSRF token correto.
"""

import requests
import re

BASE_URL = "https://precodahora.ba.gov.br/produtos/"

BROWSER_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "pt-BR,pt;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

session = requests.Session()
session.headers.update(BROWSER_HEADERS)

print("=== GET na página principal ===\n")
response = session.get(BASE_URL, timeout=15)
print(f"Status: {response.status_code}")

print("\n=== Cookies recebidos ===")
for name, value in session.cookies.items():
    print(f"  {name}: {value[:80]}{'...' if len(value) > 80 else ''}")

print("\n=== Tentando extrair csrf_token do cookie 'session' (JWT Flask) ===")
session_cookie = session.cookies.get("session")
if session_cookie:
    import base64, json as _json

    try:
        # Cookie de sessão Flask é base64(payload).assinatura
        payload_b64 = session_cookie.split(".")[0]
        # Adiciona padding se necessário
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64)
        data = _json.loads(payload)
        print(f"  Payload decodificado: {data}")
        if "csrf_token" in data:
            print(f"  ✅ csrf_token encontrado: {data['csrf_token']}")
    except Exception as e:
        print(f"  Não foi possível decodificar: {e}")

print("\n=== Tentando extrair CSRF do HTML da página ===")
# Alguns sites embutem o token em meta tag ou input hidden
csrf_meta = re.search(
    r'<meta[^>]+name=["\']csrf[_-]?token["\'][^>]+content=["\']([^"\']+)["\']',
    response.text,
    re.I,
)
csrf_input = re.search(
    r'<input[^>]+name=["\']csrf[_-]?token["\'][^>]+value=["\']([^"\']+)["\']',
    response.text,
    re.I,
)
csrf_js = re.search(
    r'csrf[_-]?token["\'\s]*[:=]["\'\s]*([A-Za-z0-9._-]{20,})', response.text
)

if csrf_meta:
    print(f"  ✅ Meta tag: {csrf_meta.group(1)}")
elif csrf_input:
    print(f"  ✅ Input hidden: {csrf_input.group(1)}")
elif csrf_js:
    print(f"  ✅ JavaScript: {csrf_js.group(1)}")
else:
    print("  ❌ Nenhum CSRF encontrado no HTML")

print("\n=== Trecho do HTML (primeiros 3000 chars) ===")
print(response.text[:3000])
