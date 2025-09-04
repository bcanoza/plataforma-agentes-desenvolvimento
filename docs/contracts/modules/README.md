# 📚 Documentação de Contratos para Módulos

Esta documentação estabelece os **padrões obrigatórios** para criar módulos na Plataforma de Agentes de Desenvolvimento.

## 🎯 **O Que São Contratos?**

Contratos são **regras bem definidas** que garantem:
- ✅ **Consistência** - todos os módulos seguem o mesmo padrão
- ✅ **Interoperabilidade** - módulos se comunicam de forma padronizada  
- ✅ **Qualidade** - implementações seguem melhores práticas
- ✅ **Manutenibilidade** - código previsível e fácil de entender

---

## 📋 **Documentação Completa**

### **1. 🎯 [Contratos de Interface](./interface-contracts.md)**
**O que define:** Princípios fundamentais, separação de responsabilidades, comunicação entre módulos.

**Use quando:** Planejando um novo módulo ou refatorando módulos existentes.

**Exemplo prático:** Separação conceitual dos módulos `auth` vs `users`.

---

### **2. 🌐 [Contratos de API](./api-contracts.md)**  
**O que define:** Rotas, endpoints, schemas, error handling, performance.

**Use quando:** Implementando endpoints REST, definindo contratos de comunicação.

**Exemplo prático:** Padrões CRUD, versionamento, paginação, autenticação.

---

### **3. ⚙️ [Contratos de Implementação](./implementation-contracts.md)**
**O que define:** Services, repositories, dependency injection, logging, testes.

**Use quando:** Implementando lógica de negócio, persistência, estrutura interna.

**Exemplo prático:** Arquitetura em camadas, error handling, auditoria.

---

### **4. 🛠️ [Guia de Scaffolding](./scaffolding-guide.md)**
**O que define:** Templates prontos, scripts de geração, checklists, exemplos.

**Use quando:** Criando novos módulos rapidamente seguindo todos os contratos.

**Exemplo prático:** Script `create_module.py` para geração automática.

---

### **5. 🎯 [Exemplos Práticos](./practical-examples.md)**
**O que define:** Cases reais, otimizações, casos especiais, integração com UI.

**Use quando:** Implementando módulos complexos, integrações, casos de uso específicos.

**Exemplo prático:** Produtos (e-commerce), Notificações (SSE), Agentes IA (streaming).

---

### **6. 🎛️ [Sistema de Gestão de Módulos](./module-management-system.md)**
**O que define:** Como módulos são salvos, administrados e gerenciados no sistema.

**Use quando:** Implementando registry persistente, DI centralizado, administração via API.

**Exemplo prático:** Module registry, service container, admin APIs, configuração dinâmica.

---

## 🚀 **Quick Start**

### **1. Criar Novo Módulo**
```bash
# Gerar estrutura completa  
python scripts/create_module.py products "Gestão de Produtos" "CRUD produtos e-commerce"

# Validar conformidade
python scripts/validate_module.py products

# Testar
pytest tests/products/ -v
```

### **2. Validar Módulo Existente**
```bash
# Verificar se segue contratos
python scripts/check_contracts.py users

# Ver relatório de conformidade  
python scripts/audit_modules.py
```

---

## 📊 **Status dos Módulos Atuais**

| Módulo | Contratos de Interface | Contratos de API | Contratos de Implementação | Status |
|--------|:---------------------:|:---------------:|:-------------------------:|:------:|
| `auth` | ✅ | ✅ | ✅ | **Conforme** |
| `users` | ⚠️ | ✅ | ✅ | **Refactor sugerido** |
| `agents` | ❌ | ⚠️ | ⚠️ | **Precisa revisão** |
| `workspace` | ❌ | ❌ | ❌ | **Não conforme** |

**Legenda:**
- ✅ **Conforme** - segue todos os contratos
- ⚠️ **Parcial** - segue a maioria, pequenos ajustes necessários  
- ❌ **Não conforme** - precisa refatoração para seguir contratos

---

## 🎯 **Caso de Estudo: Auth vs Users**

### **Problema Identificado**
Módulos `auth` e `users` têm **responsabilidades misturadas**:
- Schema `User` está em `auth` mas deveria estar em `users`
- `auth` gerencia dados de usuário + tokens
- Dependência circular entre módulos

### **Solução Proposta** 
**Separar responsabilidades:**

**Módulo Auth:**
- ✅ Login/logout  
- ✅ Tokens JWT
- ✅ Validação de credenciais
- ✅ Reset de senha
- ❌ ~~CRUD de usuários~~

**Módulo Users:**  
- ✅ CRUD de usuários
- ✅ Perfil completo (`/me`)
- ✅ Preferências/configurações
- ❌ ~~Geração de tokens~~

**Resultado:** 2 módulos **independentes** com responsabilidades **bem definidas**.

---

## 🛡️ **Validação e Conformidade**

### **Automated Checks**
```python
# scripts/check_contracts.py

def validate_module(module_name: str) -> dict:
    """Valida se módulo segue todos os contratos."""
    
    results = {
        "interface": check_interface_contracts(module_name),
        "api": check_api_contracts(module_name), 
        "implementation": check_implementation_contracts(module_name),
    }
    
    return results

def check_interface_contracts(module_name: str) -> dict:
    """Verifica contratos de interface."""
    checks = {
        "single_responsibility": has_single_responsibility(module_name),
        "clear_boundaries": has_clear_module_boundaries(module_name),  
        "no_circular_deps": has_no_circular_dependencies(module_name),
    }
    return checks
```

### **Manual Review**
**Perguntas para fazer:**

**Interface:**
- ❓ Consigo explicar a responsabilidade do módulo em **1 frase**?
- ❓ O módulo tem **dependências claras** sem circulares?
- ❓ A **comunicação** com outros módulos é explícita?

**API:**  
- ❓ Endpoints seguem **convenções REST**?
- ❓ **Versionamento** está correto (`/v1/`)?
- ❓ **Error responses** são padronizados?
- ❓ **Autenticação** está implementada corretamente?

**Implementação:**
- ❓ **Service** está separado de **Repository**?
- ❓ **Dependency injection** está funcionando?
- ❓ **Logging** está estruturado?
- ❓ **Testes** têm cobertura adequada?

---

## 🔄 **Evolução dos Contratos**

### **Versionamento da Documentação**
- **v1.0** - Contratos iniciais baseados em auth/users
- **v1.1** - Adições baseadas em feedback de novos módulos
- **v2.0** - Revisões major após lições aprendidas

### **Processo de Mudanças**
1. **Proposta** - RFC com justificativa
2. **Discussão** - review com time de desenvolvimento  
3. **Aprovação** - consenso sobre mudanças
4. **Implementação** - atualizar contratos + templates
5. **Migração** - atualizar módulos existentes

---

## 🤝 **Como Contribuir**

### **Feedback sobre Contratos**
1. Use os contratos em módulos reais
2. Documente dificuldades encontradas
3. Proponha melhorias via issues/PRs
4. Compartilhe exemplos de sucesso

### **Melhoria dos Templates**
1. Identifique padrões repetitivos
2. Crie templates especializados
3. Otimize scripts de geração
4. Documente casos de uso

---

**🎉 Esta documentação te dá TUDO que precisa para criar módulos consistentes, seguros e escaláveis!**

**Próximo passo:** Teste criando um módulo novo usando os templates e nos dê feedback! 🚀