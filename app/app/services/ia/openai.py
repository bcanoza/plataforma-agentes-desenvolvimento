
# --- helper adicionado automaticamente ---
try:
    from app.config import settings
except Exception:
    class _S: OPENAI_MODEL = 'o4-mini'
    settings = _S()

class OpenAIClient:
    def __init__(self):
        self.model = getattr(settings, 'OPENAI_MODEL', 'o4-mini')
    async def run(self, prompt: str) -> str:
        return f'[stub:{self.model}] {prompt}'

def get_client() -> OpenAIClient:
    return OpenAIClient()
