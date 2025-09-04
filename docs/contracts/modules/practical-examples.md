# 🎯 Exemplos Práticos: Aplicando Contratos

Este documento mostra **exemplos reais** de como aplicar os contratos na criação de módulos.

## 🛍️ **Exemplo 1: Módulo de Produtos (E-commerce)**

### **1. Planejamento (Interface Contracts)**

**Responsabilidade única:** 
> "Gerenciar catálogo de produtos: CRUD, categorias, preços, estoque."

**Dependências:**
- ✅ `auth` - para autenticação de usuários/admins
- ✅ `files` - para imagens de produtos (futuro)
- ❌ `orders` - produtos não gerenciam pedidos

**Comunicação:**
- Expõe dados de produtos para outros módulos
- Não depende de módulos de negócio

### **2. Design da API (API Contracts)**

**Endpoints:**
```
GET  /v1/products/              # Listagem pública (com cache)
GET  /v1/products/{id}          # Detalhes de produto
GET  /v1/products/categories    # Listar categorias

POST /v1/products/              # Criar produto (admin)
PUT  /v1/products/{id}          # Atualizar produto (admin) 
DELETE /v1/products/{id}        # Remover produto (admin)

POST /v1/products/{id}/images   # Upload imagens (admin)
PUT  /v1/products/{id}/stock    # Atualizar estoque (admin)
```

**Níveis de acesso:**
- **Público:** listagem, detalhes (para catálogo)
- **Admin:** CRUD completo, gestão de estoque

### **3. Implementação (Implementation Contracts)**

**Domain Model:**
```python
@dataclass 
class ProductModel:
    id: str
    name: str
    description: Optional[str] 
    price: float
    currency: str
    category: str
    stock_quantity: int
    status: str  # active, disabled, out_of_stock
    images: List[str]  # URLs das imagens
    metadata: Dict[str, Any]  # tags, atributos específicos
    createdAt: str
    updatedAt: str
```

**Custom Business Logic:**
```python
class ProductService:
    async def create_product(self, inp: CreateProductInput) -> ProductModel:
        # Validações de negócio
        if inp.price <= 0:
            raise ProductError("ERR_INVALID_PRICE", "Preço deve ser positivo")
            
        if await self.repo.find_by_name(inp.name):
            raise ProductError("ERR_PRODUCT_EXISTS", "Produto já existe")
        
        # Lógica específica: gerar SKU automático
        sku = await self._generate_sku(inp.category, inp.name)
        
        # Criar produto
        product = await self.repo.insert_product(
            **inp.__dict__,
            sku=sku,
            stock_quantity=0,  # iniciar com estoque zero
        )
        
        await self.audit.write(
            user_id=inp.created_by,
            event="product_created", 
            metadata={"product_id": product.id, "category": product.category}
        )
        
        return product
```

### **4. Geração Automática**
```bash
# Gerar estrutura base
python scripts/create_module.py products "Gestão de Produtos" "Catálogo de produtos para e-commerce"

# Customizar para necessidades específicas:
# - Adicionar campos price, currency, stock_quantity
# - Implementar lógica de SKU
# - Adicionar endpoints de categorias
# - Configurar cache para listagem pública
```

---

## 📧 **Exemplo 2: Módulo de Notificações**

### **1. Planejamento (Interface Contracts)**

**Responsabilidade única:**
> "Enviar e gerenciar notificações: email, SMS, push, in-app."

**Dependências:**
- ✅ `auth` - para autenticação
- ✅ `users` - para dados de contato (email, whatsapp)
- ✅ Serviços externos (SendGrid, Twilio)

**Comunicação:**
- Outros módulos chamam para enviar notificações
- Streaming de notificações em tempo real

### **2. Design da API (API Contracts)**

**Endpoints:**
```
# Para usuários
GET  /v1/notifications/         # Minhas notificações
PUT  /v1/notifications/{id}/read # Marcar como lida  
GET  /v1/notifications/stream   # SSE em tempo real

# Para sistema
POST /v1/notifications/send     # Enviar notificação (API key)
POST /v1/notifications/broadcast # Broadcast (admin)

# Para admin
GET  /v1/notifications/stats    # Estatísticas de envio
```

**Features especiais:**
- **Streaming:** SSE para notificações em tempo real
- **Bulk operations:** broadcast para múltiplos usuários  
- **Rate limiting:** prevenir spam

### **3. Implementação (Implementation Contracts)**

**Domain Model:**
```python
@dataclass
class NotificationModel:
    id: str
    user_id: str
    type: str  # email, sms, push, in_app
    title: str
    message: str
    status: str  # pending, sent, failed, read
    sent_at: Optional[str]
    read_at: Optional[str]
    metadata: Dict[str, Any]  # provider_id, delivery_receipt, etc.
    createdAt: str
```

**Streaming Implementation:**
```python
class NotificationService:
    async def stream_user_notifications(self, user_id: str):
        """Stream SSE de notificações para usuário."""
        async for notification in self._watch_notifications(user_id):
            yield f"data: {json.dumps(notification.dict())}\n\n"
    
    async def send_notification(self, inp: SendNotificationInput) -> NotificationModel:
        """Enviar notificação via provider específico."""
        # 1. Validar usuário e tipo
        # 2. Escolher provider (email/sms/push)
        # 3. Enviar via provider  
        # 4. Salvar status
        # 5. Stream para usuário se online
```

**External Integration:**
```python
class EmailProvider(Protocol):
    async def send_email(self, to: str, subject: str, body: str) -> str: ...

class SendGridProvider:
    async def send_email(self, to: str, subject: str, body: str) -> str:
        # Implementação real com SendGrid API
        pass
```

---

## 🤖 **Exemplo 3: Módulo de Agentes IA**

### **1. Planejamento (Interface Contracts)**

**Responsabilidade única:**
> "Gerenciar conversas com agentes IA: chat, contexto, geração de código."

**Complexidades especiais:**
- **Streaming** - respostas grandes via SSE
- **Contexto** - memória de conversas
- **Rate limiting** - operações caras de IA

### **2. Design da API (API Contracts)**

**Endpoints:**
```
# Chat
POST /v1/agents/chat            # Conversa com agente
GET  /v1/agents/conversations   # Histórico de conversas
POST /v1/agents/conversations/{id}/reset # Limpar contexto

# Geração específica
POST /v1/agents/generate-code   # Gerar código
POST /v1/agents/review-code     # Review de código
POST /v1/agents/generate-tests  # Gerar testes

# Streaming
GET  /v1/agents/chat/stream     # SSE para respostas longas
```

**Features especiais:**
- **Timeout longo:** 30-60s para IA
- **Streaming obrigatório:** para UX fluida
- **Context management:** histórico de conversas

### **3. Implementação (Implementation Contracts)**

**Streaming Response:**
```python
@router.post("/chat/stream")
async def chat_stream(
    body: ChatRequest,
    current: CurrentUser = Depends(require_user)
):
    """Chat com streaming SSE."""
    return StreamingResponse(
        service.chat_stream(current["sub"], body.message, body.agent_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"}
    )

class AgentService:
    async def chat_stream(self, user_id: str, message: str, agent_id: str):
        """Gera resposta com streaming."""
        async for chunk in self._call_openai_stream(message):
            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
        
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
```

**Context Management:**
```python
@dataclass
class ConversationModel:
    id: str
    user_id: str
    agent_id: str
    messages: List[Dict[str, str]]  # [{role: user, content: ...}]
    context_size: int  # tracking para limits
    last_message_at: str

class AgentService:
    async def add_to_context(self, conv_id: str, message: str, role: str):
        """Adiciona mensagem ao contexto com size management."""
        conv = await self.repo.find_by_id(conv_id)
        
        # Truncar contexto se muito grande
        if conv.context_size > MAX_CONTEXT_SIZE:
            conv.messages = conv.messages[-MAX_MESSAGES:]
        
        conv.messages.append({"role": role, "content": message})
        await self.repo.update_conversation(conv_id, messages=conv.messages)
```

---

## 📁 **Exemplo 4: Módulo de Files/Upload**

### **1. Planejamento (Interface Contracts)**

**Responsabilidade única:**
> "Gerenciar upload, storage e serving de arquivos: imagens, documentos, attachments."

**Integrações:**
- Storage backend (S3, local filesystem)
- CDN para serving (CloudFlare)  
- Vírus scanning (ClamAV)
- Image processing (thumbnails)

### **2. Design da API (API Contracts)**

**Upload Flow:**
```python
# Upload direto
POST /v1/files/upload           # Multipart upload
GET  /v1/files/{id}            # Metadata do arquivo
GET  /v1/files/{id}/download   # Download/serving
DELETE /v1/files/{id}          # Remoção

# Upload com chunking (arquivos grandes)
POST /v1/files/upload/init     # Inicializar upload
POST /v1/files/upload/{session}/chunk # Upload por partes  
POST /v1/files/upload/{session}/complete # Finalizar
```

### **3. Implementação (Implementation Contracts)**

**Multipart Handling:**
```python
@router.post("/upload", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    current: CurrentUser = Depends(require_user)
):
    """Upload de arquivo com validações."""
    
    # Validações de segurança
    if file.size > MAX_FILE_SIZE:
        raise FileError("ERR_FILE_TOO_LARGE", f"Máximo {MAX_FILE_SIZE} bytes")
    
    if not await service.is_safe_file_type(file.content_type):
        raise FileError("ERR_UNSAFE_FILE_TYPE", "Tipo de arquivo não permitido")
    
    # Processar upload
    file_info = await service.process_upload(
        file_content=await file.read(),
        filename=file.filename,
        content_type=file.content_type,
        uploaded_by=current["sub"],
        description=description
    )
    
    return build_file_response(file_info)
```

**Storage Abstraction:**
```python
class FileStorageProvider(Protocol):
    async def store(self, content: bytes, key: str) -> str: ...
    async def get_url(self, key: str) -> str: ...
    async def delete(self, key: str) -> bool: ...

class S3StorageProvider:
    async def store(self, content: bytes, key: str) -> str:
        # Implementação real com boto3
        pass
```

---

## 🔧 **Exemplo 5: Casos Especiais**

### **Módulo Simples (apenas leitura)**

**Caso:** Módulo de configurações do sistema
```python
# Só endpoints GET, sem CRUD
@router.get("/config")           # Configs públicas
@router.get("/config/features")  # Feature flags
@router.get("/config/limits")    # Rate limits, quotas
```

**Simplificações:**
- ❌ Sem service layer (configs estáticas)
- ❌ Sem repository (leitura de settings)
- ✅ Mantém schemas e error handling

### **Módulo Complexo (com sub-recursos)**

**Caso:** Módulo de projetos + arquivos
```python
# Recursos aninhados
@router.get("/projects/")                    # Lista projetos
@router.get("/projects/{id}/files")          # Arquivos do projeto  
@router.post("/projects/{id}/files/upload")  # Upload para projeto
@router.get("/projects/{id}/files/{file_id}") # Arquivo específico
```

**Considerações:**
- ✅ Sub-recursos mantêm hierarquia clara
- ✅ Validação de ownership (projeto pertence ao user)
- ✅ Cascade deletes (projeto → arquivos)

### **Módulo com Integração Externa**

**Caso:** Módulo de pagamentos
```python
# Endpoints híbridos (internos + externos)
@router.post("/payments/")               # Criar pagamento (user)
@router.get("/payments/{id}")            # Status pagamento (user)
@router.post("/payments/webhook")        # Webhook provider (public)

class PaymentService:
    async def create_payment(self, inp: CreatePaymentInput):
        # 1. Validar dados internos
        # 2. Chamar API externa (Stripe/PagSeguro)
        # 3. Salvar referência interna
        # 4. Retornar link de pagamento
        pass
```

---

## ⚡ **Otimizações Comuns**

### **Caching Strategy**
```python
# Para dados frequentemente acessados
class ProductService:
    @cached(ttl=300)  # 5 minutos
    async def list_featured_products(self) -> List[ProductModel]:
        """Produtos em destaque - cache agressivo."""
        return await self.repo.find_featured()
    
    async def get_product_by_id(self, product_id: str) -> ProductModel:
        """Sem cache - dados podem mudar (preço, estoque)."""
        return await self.repo.find_by_id(product_id)
```

### **Pagination Strategy**
```python
# Cursor-based para grandes datasets
@router.get("/products/")
async def list_products(
    cursor: Optional[str] = None,
    limit: int = Query(20, le=100),
):
    products, next_cursor = await service.list_products_cursor(cursor, limit)
    return {
        "items": [build_product_response(p) for p in products],
        "nextCursor": next_cursor,
        "hasMore": next_cursor is not None
    }
```

### **Background Processing**
```python
# Para operações lentas
@router.post("/products/{id}/generate-descriptions")  
async def generate_ai_descriptions(
    product_id: str,
    current: CurrentUser = Depends(require_admin)
):
    """Gerar descrições com IA - async."""
    
    # Enfileirar job background
    job_id = await service.enqueue_description_generation(product_id)
    
    return {
        "message": "Geração iniciada",
        "jobId": job_id,
        "statusUrl": f"/v1/jobs/{job_id}/status"
    }
```

---

## 🎨 **UI Integration Patterns**

### **Frontend Communication**
```javascript
// Módulos expõem dados estruturados para UI
const productsModule = {
  async getProducts(filters) {
    return await core.http.request({
      method: 'GET',
      url: '/v1/products/',
      params: filters,
      auth: 'core'  // injeta auth automaticamente
    });
  },
  
  async createProduct(data) {
    return await core.http.request({
      method: 'POST', 
      url: '/v1/products/',
      body: data,
      auth: 'core'
    });
  }
};
```

### **Module Manifest Integration**
```json
{
  "id": "products",
  "name": "Produtos",
  "kind": "optional", 
  "version": "1.0.0",
  "order": 300,
  "buttons": [
    {
      "id": "list_products",
      "label": "Catálogo", 
      "route": "/products",
      "icon": "package",
      "order": 1
    },
    {
      "id": "add_product",
      "label": "Novo Produto",
      "route": "/products/new",
      "icon": "plus", 
      "order": 2
    }
  ],
  "apis": [
    {
      "id": "main",
      "baseUrl": "/v1/products",
      "auth": "core",
      "allowedPaths": ["*"],
      "rateLimit": {"maxRps": 10}
    }
  ],
  "permissions": ["net:request"]
}
```

---

## 🧩 **Padrões de Composição**

### **Módulo que Usa Outros Módulos**

**Caso:** Orders depende de Products + Users
```python
class OrderService:
    def __init__(self, order_repo: OrderRepo, audit_repo: AuditLogRepo):
        self.repo = order_repo
        self.audit = audit_repo
        # NÃO injetar ProductService diretamente
    
    async def create_order(self, inp: CreateOrderInput):
        # ✅ Correto: chamar via HTTP (mantém independência)
        product = await self._get_product_via_api(inp.product_id)
        user = await self._get_user_via_api(inp.user_id)
        
        # Validar business rules
        if product.stock_quantity < inp.quantity:
            raise OrderError("ERR_INSUFFICIENT_STOCK", "Estoque insuficiente")
        
        # Criar order
        order = await self.repo.insert_order(...)
        
        # Notificar outros módulos via eventos/API
        await self._notify_stock_update(inp.product_id, inp.quantity)
        
        return order
```

### **Módulo com Sub-módulos**

**Caso:** AI module com diferentes agentes
```
app/api/ai/
├── routes.py              # Endpoints gerais
├── agents/
│   ├── code_generator.py  # Agente específico
│   ├── code_reviewer.py   # Agente específico
│   └── test_generator.py  # Agente específico
└── shared/
    ├── context.py         # Context management
    └── providers.py       # OpenAI integration
```

---

## ✅ **Checklist Completo**

### **Antes de Começar**
- [ ] Responsabilidade do módulo definida em **1 frase**
- [ ] Dependências mapeadas (quais outros módulos precisa?)
- [ ] APIs públicas vs internas identificadas  
- [ ] Nível de autenticação definido (public/user/admin/system)

### **Durante Implementação**
- [ ] Estrutura de arquivos seguindo template
- [ ] Todos os endpoints têm response_model definido
- [ ] Error handling com códigos padronizados
- [ ] Logging estruturado implementado
- [ ] Validações Pydantic nos schemas
- [ ] Service com dependency injection

### **Antes de Deploy**
- [ ] Testes unitários com cobertura >80%
- [ ] Validação de conformidade: `python scripts/validate_module.py {module}`
- [ ] Rate limiting configurado apropriadamente
- [ ] Docs de API atualizadas (/docs)
- [ ] Auditoria implementada para operações críticas

### **Pós Deploy**
- [ ] Monitoramento configurado
- [ ] Logs sendo coletados corretamente
- [ ] Métricas de performance normais
- [ ] Usuários conseguem usar sem problemas

---

**🎉 Com estes exemplos práticos, você tem roadmap completo para implementar qualquer tipo de módulo seguindo todos os contratos estabelecidos!**