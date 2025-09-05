# 📦 Gestão de Dependências por Módulo

Este documento define como cada módulo declara suas **dependências Python específicas** e como o sistema as resolve automaticamente.

## 🚨 **Problema Atual**

### **Requirements.txt Monolítico**
```python
# app/requirements.txt - TUDO misturado
fastapi         # ← usado por todos
pyjwt           # ← só auth
openai          # ← só agents  
psycopg2-binary # ← só BD
cryptography    # ← só auth
celery          # ← só background tasks
```

**Problemas:**
- ❌ **Instalação desnecessária** - módulo users instala OpenAI
- ❌ **Conflitos de versão** - módulos podem precisar versões diferentes
- ❌ **Módulos opcionais** - não consegue instalar só o necessário
- ❌ **Manutenção complexa** - requirements gigante e confuso
- ❌ **Deploy pesado** - imagens Docker com dependências não usadas

---

## ✅ **Solução: Dependências por Módulo**

### **1. Manifesto com Requirements**

**Cada módulo declara suas dependências:**
```json
// app/api/auth/module.json
{
  "id": "auth",
  "name": "Sistema de Autenticação",
  "version": "1.0.0",
  "dependencies": {
    "python": {
      "required": [
        "pyjwt>=2.8.0,<3.0.0",
        "cryptography>=41.0.0",
        "passlib[bcrypt]>=1.7.4",
        "bcrypt>=4.0.0"
      ],
      "optional": [
        "jwcrypto>=1.5.0"  // para features avançadas
      ]
    },
    "system": {
      "required": ["openssl", "libssl-dev"]  // deps de sistema se necessário
    },
    "modules": [
      {"id": "core", "version": ">=1.0.0"}  // dependência de outros módulos
    ]
  }
}

// app/api/agents/module.json  
{
  "id": "agents", 
  "name": "Agentes de IA",
  "dependencies": {
    "python": {
      "required": [
        "openai>=1.3.0,<2.0.0",
        "tiktoken>=0.5.0",      // para count de tokens
        "langchain>=0.0.300"    // se usar LangChain
      ],
      "optional": [
        "anthropic>=0.3.0",     // para Claude
        "cohere>=4.0.0"         // para Cohere
      ]
    },
    "modules": [
      {"id": "auth", "version": ">=1.0.0", "required": true},
      {"id": "users", "version": ">=1.0.0", "required": false}
    ]
  }
}
```

### **2. Core Dependencies (Base)**
```json
// app/core/module.json
{
  "id": "core",
  "name": "Core Framework", 
  "dependencies": {
    "python": {
      "required": [
        "fastapi>=0.104.0,<1.0.0",
        "uvicorn[standard]>=0.24.0", 
        "pydantic>=2.5.0,<3.0.0",
        "pydantic-settings>=2.1.0"
      ]
    }
  }
}
```

---

## 🏗️ **Sistema de Resolução**

### **Dependency Resolver**
```python
# app/core/dependency_resolver.py

@dataclass
class ModuleDependency:
    """Dependência Python de um módulo."""
    package: str
    version_spec: str  # >=1.0.0,<2.0.0
    optional: bool = False
    module_id: str = ""

@dataclass  
class DependencyGraph:
    """Grafo de dependências resolvido."""
    modules: List[str]                           # ordem de carregamento
    requirements: Dict[str, str]                 # package -> version final
    conflicts: List[Tuple[str, str, str]]        # conflicts detectados
    missing_modules: List[str]                   # módulos não encontrados

class DependencyResolver:
    """Resolve dependências entre módulos e gera requirements finais."""
    
    def __init__(self, module_registry: ModuleRegistryService):
        self.registry = module_registry
    
    async def resolve_dependencies(self, active_modules: List[str]) -> DependencyGraph:
        """
        Resolve dependências para lista de módulos ativos.
        
        Returns:
            DependencyGraph com requirements finais e ordem de carregamento
        """
        logger.info("dependency_resolution.start", extra={"modules": active_modules})
        
        # 1. Coletar todas as dependências Python
        all_requirements = {}
        conflicts = []
        
        for module_id in active_modules:
            module_info = await self.registry.get_module(module_id)
            if not module_info:
                continue
                
            # Extrair requirements do manifesto
            python_deps = module_info.manifest.get("dependencies", {}).get("python", {})
            required_deps = python_deps.get("required", [])
            optional_deps = python_deps.get("optional", [])
            
            # Processar dependências obrigatórias
            for dep_spec in required_deps:
                package, version = self._parse_requirement(dep_spec)
                
                if package in all_requirements:
                    # Verificar conflito
                    existing = all_requirements[package]
                    resolved = self._resolve_version_conflict(package, existing.version_spec, version)
                    
                    if resolved:
                        all_requirements[package] = ModuleDependency(
                            package=package,
                            version_spec=resolved,
                            module_id=f"{existing.module_id},{module_id}"
                        )
                    else:
                        conflicts.append((package, existing.version_spec, version))
                else:
                    all_requirements[package] = ModuleDependency(
                        package=package,
                        version_spec=version,
                        module_id=module_id
                    )
        
        # 2. Ordenar módulos por dependências
        sorted_modules = await self._topological_sort(active_modules)
        
        # 3. Gerar requirements.txt final
        final_requirements = {
            pkg: dep.version_spec 
            for pkg, dep in all_requirements.items()
        }
        
        graph = DependencyGraph(
            modules=sorted_modules,
            requirements=final_requirements,
            conflicts=conflicts,
            missing_modules=[]
        )
        
        logger.info("dependency_resolution.completed", extra={
            "total_packages": len(final_requirements),
            "conflicts": len(conflicts),
            "modules_order": sorted_modules
        })
        
        return graph
    
    def _parse_requirement(self, requirement_spec: str) -> Tuple[str, str]:
        """Parse 'package>=1.0.0,<2.0.0' -> ('package', '>=1.0.0,<2.0.0')."""
        if ">=" in requirement_spec:
            package = requirement_spec.split(">=")[0]
            version = requirement_spec[len(package):]
        elif "==" in requirement_spec:
            package = requirement_spec.split("==")[0] 
            version = requirement_spec[len(package):]
        else:
            # Sem versão especificada
            package = requirement_spec
            version = ""
            
        return package.strip(), version.strip()
    
    def _resolve_version_conflict(self, package: str, v1: str, v2: str) -> Optional[str]:
        """Tenta resolver conflito de versões."""
        # Implementação simples - pode ser melhorada com packaging.specifiers
        
        # Se uma versão é subset da outra, usar a mais restritiva
        if v1 in v2:
            return v2
        elif v2 in v1:
            return v1
        else:
            # Conflito real
            return None
    
    async def _topological_sort(self, modules: List[str]) -> List[str]:
        """Ordena módulos por dependências."""
        # Implementação simples baseada no kind
        # TODO: Implementar ordenação topológica real
        
        module_info_list = []
        for module_id in modules:
            info = await self.registry.get_module(module_id)
            if info:
                module_info_list.append(info)
        
        # Ordenar por kind + dependencies
        def sort_key(module):
            kind_order = {"core": 0, "system": 100, "admin": 200, "optional": 300}
            return kind_order.get(module.kind, 999) + module.display_order
        
        sorted_modules = sorted(module_info_list, key=sort_key)
        return [m.id for m in sorted_modules]
    
    async def generate_requirements_txt(self, active_modules: List[str]) -> str:
        """Gera requirements.txt baseado nos módulos ativos."""
        
        graph = await self.resolve_dependencies(active_modules)
        
        if graph.conflicts:
            raise DependencyError(
                "ERR_VERSION_CONFLICTS",
                f"Conflitos de versão detectados: {graph.conflicts}"
            )
        
        # Gerar arquivo requirements.txt
        lines = ["# Auto-generated requirements for active modules", ""]
        
        # Agrupar por categoria
        categories = {
            "Core Framework": ["fastapi", "uvicorn", "pydantic"],
            "Authentication": ["pyjwt", "cryptography", "passlib", "bcrypt"],
            "AI/ML": ["openai", "tiktoken", "langchain", "anthropic"],
            "Database": ["sqlalchemy", "psycopg2-binary", "redis"],
            "Development": ["pytest", "black", "ruff"]
        }
        
        # Adicionar por categoria
        for category, packages in categories.items():
            lines.append(f"# {category}")
            for pkg in packages:
                if pkg in graph.requirements:
                    version = graph.requirements[pkg]
                    line = f"{pkg}{version}" if version else pkg
                    lines.append(line)
            lines.append("")
        
        # Adicionar dependências não categorizadas
        categorized = set()
        for packages in categories.values():
            categorized.update(packages)
        
        uncategorized = [
            f"{pkg}{version}" if version else pkg
            for pkg, version in graph.requirements.items()
            if pkg not in categorized
        ]
        
        if uncategorized:
            lines.append("# Other dependencies")
            lines.extend(uncategorized)
        
        return "\n".join(lines)

class DependencyError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
```

---

## 🎯 **Implementação por Módulo**

### **Auth Module Dependencies**
```json
// app/api/auth/module.json
{
  "id": "auth",
  "name": "Sistema de Autenticação",
  "version": "1.0.0",
  "dependencies": {
    "python": {
      "required": [
        "pyjwt>=2.8.0,<3.0.0",           // JWT tokens
        "cryptography>=41.0.0",          // Key management
        "passlib[bcrypt]>=1.7.4",        // Password hashing
        "bcrypt>=4.0.0"                  // Bcrypt implementation
      ],
      "optional": [
        "jwcrypto>=1.5.0"                // Advanced JWT features
      ]
    },
    "modules": []  // Auth é base, sem dependências de módulos
  },
  "provides": {
    "services": ["auth_service"],
    "dependencies": ["require_user", "require_admin", "verify_api_key"],
    "schemas": ["User", "LoginRequest", "ErrorResponse"]
  }
}
```

### **Users Module Dependencies**
```json
// app/api/users/module.json
{
  "id": "users", 
  "name": "Gestão de Usuários",
  "version": "1.0.0",
  "dependencies": {
    "python": {
      "required": [
        "email-validator>=2.1.0",        // Validação de email
        "phonenumbers>=8.13.0"           // Validação WhatsApp
      ],
      "optional": [
        "pillow>=10.0.0",                // Processamento de avatars
        "python-multipart>=0.0.6"       // Upload de arquivos
      ]
    },
    "modules": [
      {"id": "auth", "version": ">=1.0.0", "required": true}
    ]
  },
  "provides": {
    "services": ["user_service"],
    "schemas": ["User", "CreateUserRequest", "UpdateUserRequest"]
  }
}
```

### **Agents Module Dependencies**
```json
// app/api/agents/module.json
{
  "id": "agents",
  "name": "Agentes de IA", 
  "version": "0.9.0",
  "dependencies": {
    "python": {
      "required": [
        "openai>=1.3.0,<2.0.0",         // OpenAI API
        "tiktoken>=0.5.0",              // Token counting
        "httpx>=0.25.0"                 // HTTP client para APIs
      ],
      "optional": [
        "langchain>=0.0.300",           // LangChain framework
        "anthropic>=0.3.0",             // Claude AI
        "cohere>=4.0.0",                // Cohere AI
        "transformers>=4.35.0"          // Local models
      ]
    },
    "modules": [
      {"id": "auth", "version": ">=1.0.0", "required": true},
      {"id": "users", "version": ">=1.0.0", "required": false}
    ]
  },
  "provides": {
    "services": ["agent_service", "conversation_service"],
    "schemas": ["AgentProfile", "ChatMessage", "CodeGenerationResponse"]
  }
}
```

---

## 🔧 **Sistema de Resolução Automática**

### **Dependency Manager Service**
```python
# app/services/dependency_manager_service.py

class DependencyManagerService:
    """Gerencia dependências Python por módulo."""
    
    def __init__(self, registry: ModuleRegistryService):
        self.registry = registry
    
    async def scan_module_dependencies(self, module_id: str) -> Dict[str, List[str]]:
        """Escaneia dependências de um módulo."""
        module = await self.registry.get_module(module_id)
        if not module:
            return {"required": [], "optional": []}
        
        python_deps = module.manifest.get("dependencies", {}).get("python", {})
        return {
            "required": python_deps.get("required", []),
            "optional": python_deps.get("optional", []),
            "module": module_id
        }
    
    async def resolve_active_modules(self) -> DependencyGraph:
        """Resolve dependências de todos os módulos ativos."""
        active_modules = await self.registry.get_active_modules()
        
        resolver = DependencyResolver(self.registry)
        return await resolver.resolve_dependencies([m.id for m in active_modules])
    
    async def generate_requirements_for_deployment(self, target_modules: List[str]) -> str:
        """Gera requirements.txt otimizado para deploy específico."""
        resolver = DependencyResolver(self.registry)
        return await resolver.generate_requirements_txt(target_modules)
    
    async def validate_module_dependencies(self, module_id: str) -> Dict[str, Any]:
        """Valida se dependências de um módulo podem ser satisfeitas."""
        
        # 1. Obter dependências do módulo
        deps = await self.scan_module_dependencies(module_id)
        
        # 2. Verificar se há conflitos com módulos ativos  
        active_modules = await self.registry.get_active_modules()
        current_graph = await self.resolve_active_modules()
        
        # 3. Simular adição do novo módulo
        test_modules = [m.id for m in active_modules] + [module_id]
        resolver = DependencyResolver(self.registry)
        
        try:
            test_graph = await resolver.resolve_dependencies(test_modules)
            
            return {
                "valid": True,
                "conflicts": test_graph.conflicts,
                "new_packages": len(test_graph.requirements) - len(current_graph.requirements),
                "requirements": deps
            }
        except DependencyError as e:
            return {
                "valid": False,
                "error": e.message,
                "requirements": deps
            }
```

---

## 🐳 **Integração com Docker**

### **Multi-stage Build com Dependências Dinâmicas**

**Dockerfile otimizado:**
```dockerfile
# Dockerfile.dynamic
FROM python:3.11-slim as deps-resolver

# Instalar resolver de dependências  
COPY app/core/dependency_resolver.py /app/
COPY app/services/dependency_manager_service.py /app/

# Gerar requirements.txt baseado em módulos ativos
ENV ACTIVE_MODULES="auth,users,agents"
RUN python /app/generate_requirements.py $ACTIVE_MODULES > /requirements.txt

# Stage principal
FROM python:3.11-slim

COPY --from=deps-resolver /requirements.txt /requirements.txt

# Instalar apenas dependências necessárias
RUN pip install --no-cache-dir -r /requirements.txt

COPY app/ /app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0"]
```

### **Docker Compose com Profiles**
```yaml
# docker-compose.yml
version: '3.8'

services:
  app-minimal:
    build: 
      dockerfile: Dockerfile.dynamic
      args:
        ACTIVE_MODULES: "auth,users"  # Só essenciais
    profiles: ["minimal"]
    
  app-full:
    build:
      dockerfile: Dockerfile.dynamic  
      args:
        ACTIVE_MODULES: "auth,users,agents,workspace"  # Todos os módulos
    profiles: ["full"]
    
  app-ai-only:
    build:
      dockerfile: Dockerfile.dynamic
      args:
        ACTIVE_MODULES: "auth,users,agents"  # Só IA
    profiles: ["ai"]

# Uso:
# docker-compose --profile minimal up    # Deploy leve
# docker-compose --profile full up       # Deploy completo  
# docker-compose --profile ai up         # Deploy focado em IA
```

---

## 📋 **Scripts de Gestão**

### **generate_requirements.py**
```python
#!/usr/bin/env python3
"""
Gera requirements.txt baseado nos módulos ativos.

Uso:
    python scripts/generate_requirements.py                    # Todos os ativos
    python scripts/generate_requirements.py auth users         # Módulos específicos
    python scripts/generate_requirements.py --output docker/   # Output customizado
"""

import asyncio
import sys
from pathlib import Path

from app.services.dependency_manager_service import DependencyManagerService
from app.services.module_registry_service import ModuleRegistryService, PgModuleRepo

async def generate_for_modules(modules: List[str], output_path: Optional[str] = None):
    """Gera requirements.txt para módulos especificados."""
    
    registry = ModuleRegistryService(PgModuleRepo())
    dep_manager = DependencyManagerService(registry)
    
    # Resolver dependências
    requirements_content = await dep_manager.generate_requirements_for_deployment(modules)
    
    # Salvar arquivo
    output_file = Path(output_path or "requirements.txt")
    output_file.write_text(requirements_content)
    
    print(f"✅ Requirements gerado: {output_file}")
    print(f"📦 Módulos: {modules}")
    
    # Estatísticas
    lines = requirements_content.split("\n")
    package_count = len([l for l in lines if l and not l.startswith("#")])
    print(f"📊 Packages: {package_count}")

async def analyze_current_requirements():
    """Analisa requirements.txt atual vs necessidades dos módulos."""
    
    # Ler requirements.txt atual
    current_file = Path("app/requirements.txt")
    if not current_file.exists():
        print("❌ app/requirements.txt não encontrado")
        return
    
    current_packages = []
    for line in current_file.read_text().split("\n"):
        if line.strip() and not line.startswith("#"):
            package = line.split(">=")[0].split("==")[0].split("<")[0]
            current_packages.append(package.strip())
    
    # Analisar dependências por módulo
    registry = ModuleRegistryService(PgModuleRepo())
    active_modules = await registry.list_modules(status="active")
    
    print(f"\n📊 Análise de Dependências:")
    print(f"   Requirements.txt atual: {len(current_packages)} packages")
    print(f"   Módulos ativos: {len(active_modules)}")
    
    # TODO: Comparar com dependências declaradas nos módulos
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        modules = sys.argv[1:]
        asyncio.run(generate_for_modules(modules))
    else:
        asyncio.run(analyze_current_requirements())
```

### **validate_dependencies.py**
```python
#!/usr/bin/env python3
"""
Valida dependências de módulos antes de ativar.

Uso:
    python scripts/validate_dependencies.py agents    # Validar antes de ativar
    python scripts/validate_dependencies.py --all     # Validar todos os ativos
"""

async def validate_module_deps(module_id: str):
    """Valida dependências de um módulo."""
    
    dep_manager = DependencyManagerService(registry)
    result = await dep_manager.validate_module_dependencies(module_id)
    
    if result["valid"]:
        print(f"✅ {module_id}: Dependências válidas")
        if result["new_packages"] > 0:
            print(f"   📦 Adicionará {result['new_packages']} novos packages")
    else:
        print(f"❌ {module_id}: {result['error']}")
        
    if result["conflicts"]:
        print(f"⚠️  Conflitos detectados: {result['conflicts']}")
        
    return result["valid"]
```

---

## 🎛️ **Admin APIs para Dependencies**

### **Novos Endpoints de Administração**
```python
# app/api/admin/dependencies_routes.py

@router.get("/dependencies/scan")
async def scan_all_dependencies(admin: CurrentUser = Depends(require_admin)):
    """Escaneia dependências de todos os módulos."""
    
    dep_manager = DependencyManagerService(registry)
    graph = await dep_manager.resolve_active_modules()
    
    return {
        "modules": graph.modules,
        "totalPackages": len(graph.requirements),
        "conflicts": graph.conflicts,
        "requirements": graph.requirements
    }

@router.get("/dependencies/{module_id}")
async def get_module_dependencies(module_id: str, admin: CurrentUser = Depends(require_admin)):
    """Dependências específicas de um módulo."""
    
    dep_manager = DependencyManagerService(registry)
    deps = await dep_manager.scan_module_dependencies(module_id)
    
    return {
        "moduleId": module_id,
        "dependencies": deps,
        "canActivate": True  # TODO: verificar conflitos
    }

@router.post("/dependencies/generate-requirements")
async def generate_requirements(
    modules: List[str] = Body(...),
    admin: CurrentUser = Depends(require_admin)
):
    """Gera requirements.txt para módulos específicos."""
    
    dep_manager = DependencyManagerService(registry)
    
    try:
        requirements_content = await dep_manager.generate_requirements_for_deployment(modules)
        
        return {
            "success": True,
            "modules": modules,
            "requirements": requirements_content,
            "timestamp": datetime.utcnow().isoformat()
        }
    except DependencyError as e:
        return {
            "success": False,
            "error": e.message,
            "modules": modules
        }
```

---

## 📁 **Estrutura de Arquivos Proposta**

### **Cada Módulo tem seu requirements.json**
```
app/api/auth/
├── routes.py
├── schemas.py  
├── dependencies.py
├── module.json         ← Manifesto completo
└── requirements.json   ← Dependências Python específicas

app/api/users/
├── routes.py
├── schemas.py
├── module.json
└── requirements.json

app/api/agents/
├── routes.py
├── schemas.py  
├── services.py
├── module.json
└── requirements.json   ← OpenAI, tiktoken, etc.
```

### **Requirements.json Format**
```json
{
  "required": [
    "package>=1.0.0,<2.0.0",
    "other-package==1.5.3"
  ],
  "optional": [
    "enhancement-package>=2.0.0"
  ],
  "conflicts": [
    "incompatible-package"  // packages que não podem coexistir
  ],
  "platform": {
    "linux": ["additional-package>=1.0.0"],
    "darwin": ["mac-specific>=1.0.0"]
  }
}
```

---

## 🚀 **Fluxo de Deploy Otimizado**

### **Build-time Dependency Resolution**
```bash
# 1. Determinar módulos ativos
ACTIVE_MODULES=$(curl -s http://registry-api/modules/active | jq -r '.[].id' | tr '\n' ',')

# 2. Gerar requirements otimizado
python scripts/generate_requirements.py $ACTIVE_MODULES --output docker/requirements.txt

# 3. Build Docker com requirements específicos  
docker build -f Dockerfile.dynamic \
  --build-arg REQUIREMENTS_FILE=docker/requirements.txt \
  --tag app:optimized .

# Resultado: Imagem com APENAS as dependências necessárias
```

### **Runtime Dependency Validation**
```python
# app/core/startup_validator.py

async def validate_runtime_dependencies():
    """Valida dependências no startup."""
    
    missing_packages = []
    
    # Verificar se packages necessários estão instalados
    active_modules = await registry.get_active_modules()
    
    for module in active_modules:
        python_deps = module.manifest.get("dependencies", {}).get("python", {})
        
        for package_spec in python_deps.get("required", []):
            package = package_spec.split(">=")[0].split("==")[0]
            
            try:
                __import__(package.replace("-", "_"))
            except ImportError:
                missing_packages.append(f"{package} (required by {module.id})")
    
    if missing_packages:
        logger.error("startup.missing_dependencies", extra={"missing": missing_packages})
        raise RuntimeError(f"Missing packages: {missing_packages}")
    else:
        logger.info("startup.dependencies.ok", extra={"modules": len(active_modules)})
```

---

## 🎯 **Casos de Uso Práticos**

### **Deploy Mínimo (Production)**
```bash
# Só módulos essenciais
ACTIVE_MODULES="auth,users"
python scripts/generate_requirements.py $ACTIVE_MODULES

# Resultado: requirements.txt com ~15 packages
# - fastapi, pydantic, pyjwt, bcrypt, psycopg2-binary, etc.
# SEM: openai, langchain, transformers (economy de ~500MB)
```

### **Deploy Completo (Development)**  
```bash
# Todos os módulos + dev tools
ACTIVE_MODULES="auth,users,agents,workspace,notifications" 
python scripts/generate_requirements.py $ACTIVE_MODULES --include-dev

# Resultado: requirements.txt com ~50 packages
# + openai, langchain, pytest, black, etc.
```

### **Deploy Específico (AI-focused)**
```bash
# Só módulos de IA
ACTIVE_MODULES="auth,users,agents"
python scripts/generate_requirements.py $ACTIVE_MODULES

# Resultado: inclui openai, tiktoken, mas exclui celery, redis-extras
```

---

## ⚠️ **Gestão de Conflitos**

### **Detecção Automática**
```python
# Exemplo de conflito:
# auth module: pyjwt>=2.8.0,<3.0.0
# other module: pyjwt==1.7.1  

# Resolver: usar versão mais restritiva que satisfaça ambos
# Resultado: pyjwt>=2.8.0,<3.0.0 (se compatível)

# Se incompatível: erro claro
{
  "error": "ERR_DEPENDENCY_CONFLICT",
  "message": "Conflito de versão: pyjwt",
  "details": {
    "auth": ">=2.8.0,<3.0.0", 
    "other": "==1.7.1",
    "resolution": "impossible"
  }
}
```

### **Resolução de Conflitos**
```python
# Opções para resolver conflitos:

# 1. Update da versão no módulo
PUT /v1/admin/modules/other/manifest 
{
  "dependencies": {
    "python": {
      "required": ["pyjwt>=2.8.0,<3.0.0"]  # ← Update para versão compatível
    }
  }
}

# 2. Desativar módulo conflitante temporariamente
POST /v1/admin/modules/other/disable

# 3. Override de versão (debug only)
PUT /v1/admin/dependencies/override
{
  "package": "pyjwt", 
  "version": "2.8.0",
  "force": true  # ← Força versão específica
}
```

---

## 📊 **Análise do Requirements.txt Atual**

### **Categorização das Dependencies**
```python
# app/requirements.txt atual analisado:

CORE = [
    "fastapi", "uvicorn", "pydantic", "pydantic-settings"
]  # ← Usado por TODOS os módulos

AUTH = [
    "pyjwt", "cryptography", "passlib", "bcrypt", "jwcrypto"  
]  # ← Só módulo auth

AI = [
    "openai"
]  # ← Só módulo agents

DATABASE = [
    "sqlalchemy", "alembic", "psycopg2-binary"
]  # ← Modules que usam BD

INFRA = [
    "celery", "redis", "fastapi-limiter", "prometheus-fastapi-instrumentator"
]  # ← Background tasks, monitoring

UTILS = [
    "httpx", "jsonschema", "PyYAML", "loguru"
]  # ← Utilities compartilhadas

DEV = [
    "pytest", "black", "ruff"
]  # ← Só desenvolvimento
```

### **Proposta de Reorganização**
```
# ANTES: 1 arquivo com tudo (37 packages)
app/requirements.txt  

# DEPOIS: Separado por módulo
app/core/requirements.json          # fastapi, pydantic (4 packages)
app/api/auth/requirements.json      # pyjwt, cryptography (5 packages)  
app/api/agents/requirements.json    # openai, tiktoken (3 packages)
app/api/users/requirements.json     # email-validator (2 packages)

# + geração automática do requirements.txt final
```

---

## 🔄 **Fluxo Completo**

### **Desenvolvimento de Novo Módulo**
```bash
# 1. Criar módulo 
python scripts/create_module.py notifications "Sistema de Notificações" "Alertas em tempo real"

# 2. Definir dependências específicas
# app/api/notifications/requirements.json:
{
  "required": [
    "sendgrid>=6.10.0",         # Email
    "twilio>=8.10.0",           # SMS  
    "firebase-admin>=6.3.0"     # Push notifications
  ],
  "optional": [
    "slack-sdk>=3.26.0"         # Slack integration
  ]
}

# 3. Validar dependências
python scripts/validate_dependencies.py notifications
# → ✅ Sem conflitos detectados, 3 novos packages

# 4. Gerar requirements atualizado
python scripts/generate_requirements.py --include notifications
# → requirements.txt com 40 packages (era 37 + 3 novos)

# 5. Rebuild container com novos packages
docker-compose build app
```

### **Deploy Production Otimizado**
```bash
# 1. Determinar módulos para produção
PROD_MODULES="auth,users,workspace"  # Sem IA para economizar

# 2. Gerar requirements mínimo
python scripts/generate_requirements.py $PROD_MODULES --output prod-requirements.txt

# 3. Build imagem otimizada  
docker build -f Dockerfile.prod \
  --build-arg REQUIREMENTS=prod-requirements.txt \
  --tag app:prod-minimal .

# Resultado: Imagem 60% menor sem OpenAI/LangChain
```

---

## 🛡️ **Segurança e Validação**

### **Package Scanning**
```python
# app/security/package_scanner.py

class PackageSecurityScanner:
    """Scanner de segurança para dependências."""
    
    async def scan_vulnerabilities(self, requirements: List[str]) -> Dict[str, Any]:
        """Escaneia vulnerabilidades conhecidas."""
        
        # Integração com PyUp, Snyk, ou safety
        vulnerabilities = []
        
        for package_spec in requirements:
            package = package_spec.split(">=")[0] 
            
            # Verificar em base de dados de vulnerabilidades
            vulns = await self._check_package_security(package)
            vulnerabilities.extend(vulns)
        
        return {
            "total_packages": len(requirements),
            "vulnerabilities": vulnerabilities,
            "safe": len(vulnerabilities) == 0
        }
    
    async def validate_package_licenses(self, requirements: List[str]) -> Dict[str, str]:
        """Valida licenças dos packages."""
        # Verificar compatibilidade de licenças
        pass
```

### **Dependency Lock File**
```json
// app/dependencies.lock (gerado automaticamente)
{
  "generated_at": "2024-01-15T10:30:00Z",
  "active_modules": ["auth", "users", "agents"],
  "resolved_dependencies": {
    "fastapi": "0.104.1",           // versão exata resolvida
    "pyjwt": "2.8.0",
    "openai": "1.3.7"
  },
  "dependency_tree": {
    "auth": ["pyjwt", "cryptography", "passlib"],
    "agents": ["openai", "tiktoken"]
  },
  "conflicts_resolved": [
    {
      "package": "httpx",
      "conflict": "auth wanted >=0.24.0, agents wanted >=0.25.0",
      "resolution": ">=0.25.0"
    }
  ]
}
```

---

## 🎯 **Integração com Module Management**

### **Dependency Check antes de Ativar Módulo**
```python
# No admin API:

@router.post("/modules/{module_id}/enable")
async def enable_module(module_id: str, admin: CurrentUser = Depends(require_admin)):
    """Ativa módulo com validação de dependências."""
    
    # 1. Validar dependências primeiro
    dep_manager = DependencyManagerService(registry)
    validation = await dep_manager.validate_module_dependencies(module_id)
    
    if not validation["valid"]:
        return {
            "success": False,
            "message": f"Dependências inválidas: {validation['error']}",
            "missingPackages": validation.get("missing", []),
            "conflicts": validation.get("conflicts", [])
        }
    
    # 2. Se tiver novos packages, informar admin
    if validation["new_packages"] > 0:
        return {
            "success": False,
            "message": f"Módulo requer {validation['new_packages']} novos packages",
            "action": "run: pip install + restart required",
            "newPackages": validation.get("new_requirements", [])
        }
    
    # 3. Ativar módulo (dependências já satisfeitas)
    success = await module_manager.enable_module(module_id)
    return {"success": success, "message": "Módulo ativado"}
```

### **Auto-install de Dependências (opcional)**
```python
@router.post("/modules/{module_id}/install-deps")
async def install_module_dependencies(
    module_id: str,
    auto_restart: bool = False,
    admin: CurrentUser = Depends(require_admin)
):
    """Instala dependências de um módulo automaticamente."""
    
    # CUIDADO: Só para desenvolvimento, não produção
    if not settings.ENABLE_AUTO_INSTALL:
        raise HTTPException(400, detail="Auto-install desabilitado em produção")
    
    dep_manager = DependencyManagerService(registry)
    deps = await dep_manager.scan_module_dependencies(module_id)
    
    # Gerar comando pip install
    pip_command = ["pip", "install"] + deps["required"]
    
    # Executar instalação
    import subprocess
    result = subprocess.run(pip_command, capture_output=True, text=True)
    
    return {
        "success": result.returncode == 0,
        "command": " ".join(pip_command),
        "stdout": result.stdout,
        "stderr": result.stderr,
        "restartRequired": True
    }
```

---

## 📈 **Benefícios da Nova Abordagem**

### **Deploy Otimizado**
```bash
# ANTES: requirements.txt com 37 packages (todos os módulos)
# Imagem Docker: ~800MB

# DEPOIS: requirements dinâmico baseado em módulos ativos
# Deploy minimal (auth+users): ~15 packages
# Imagem Docker: ~400MB (50% menor!)

# Deploy AI (auth+users+agents): ~25 packages  
# Imagem Docker: ~600MB 

# Deploy completo: todos os packages
# Imagem Docker: ~800MB (igual ao antes, mas apenas quando necessário)
```

### **Desenvolvimento Modular**
```python
# Desenvolvedor trabalhando só no módulo users:
python scripts/generate_requirements.py auth users --include-dev
pip install -r requirements-dev.txt

# SEM instalar: openai, langchain, transformers (economia de tempo)
```

### **Conflict Prevention**
```python
# Antes de ativar módulo:
POST /v1/admin/dependencies/validate/new-module
→ {
    "conflicts": ["openai: agents wants 1.3.0, new-module wants 0.28.0"],
    "resolution": "Update new-module to use openai>=1.3.0",
    "canProceed": false
  }
```

**🎉 Essa abordagem resolve completamente o problema de gestão de dependências por módulo!**

**Quer que eu implemente alguma parte específica ou tem alguma dúvida sobre como funcionaria na prática?** 🚀