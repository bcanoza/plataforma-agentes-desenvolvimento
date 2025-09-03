# app/main.py
"""
Ponto de entrada da API.

- Configura logging padrão.
- Cria a instância FastAPI (`app`).
- Executa auto-discovery de controllers (compatível com `load_controllers` ou `include_controllers`).
- Expõe rota "/" só para um ping rápido.
- Registra logs em startup/shutdown.
"""

from fastapi import FastAPI
from app.core.logging_config import get_logger
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Inicializa logging o quanto antes
logger = get_logger()

# Instância global da aplicação
app = FastAPI(title="Assistente API", version="1.0.0")

# configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,        # <- necessário para cookies
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["set-cookie"], # opcional, útil para debug
)


# -------------------------------------------------------------------------
# Auto-discovery de módulos API (nova arquitetura)
# Prioriza nova estrutura app/api/ sobre controllers antigos
# -------------------------------------------------------------------------
try:
    from app.core.api_loader import include_api_modules as _autoload
    _autoload(app)
    logger.info("[main] módulos API carregados com sucesso.")
except Exception as e:
    logger.error(f"[main] falha ao carregar módulos API: {e}")
    
    # Fallback para controllers antigos
    try:
        from app.core.controller_loader import load_controllers as _fallback
        _fallback(app)
        logger.info("[main] controllers antigos carregados como fallback.")
    except Exception as e2:
        logger.error(f"[main] falha ao carregar controllers antigos: {e2}")

# -------------------------------------------------------------------------
# Eventos de ciclo de vida
# -------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    logger.info("[startup] iniciando aplicação...")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("[shutdown] finalizando aplicação...")

# -------------------------------------------------------------------------
# Rota raiz (ping simples)
# -------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "Assistente API rodando"}
