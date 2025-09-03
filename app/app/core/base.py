import logging
"""Configuração base e inicialização do app."""
from fastapi import FastAPI
from app.core.logging_config import setup_logging

def setup_app(app: FastAPI) -> None:
    """Configura middlewares, logs e eventos de startup/shutdown."""
    setup_logging()
    @app.on_event("startup")
    async def startup_event():
        import logging
        logging.getLogger("assistente").info("[startup] iniciando aplicação...")

    @app.on_event("shutdown")
    async def shutdown_event():
        import logging
        logging.getLogger("assistente").info("[shutdown] finalizando aplicação...")
