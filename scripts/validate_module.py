#!/usr/bin/env python3
"""
Script para validar se um módulo segue os contratos estabelecidos.

Uso:
    python scripts/validate_module.py users
    python scripts/validate_module.py products --detailed
"""

import sys
from pathlib import Path
import argparse
from typing import Dict, List, Tuple


def check_file_structure(module_name: str) -> Dict[str, bool]:
    """Verifica se estrutura de arquivos está correta."""
    checks = {}
    
    base_api = Path(f"app/app/api/{module_name}")
    base_services = Path(f"app/app/services")
    base_tests = Path(f"tests/{module_name}")
    
    # Arquivos obrigatórios
    required_files = {
        "api_init": base_api / "__init__.py",
        "api_routes": base_api / "routes.py", 
        "api_schemas": base_api / "schemas.py",
        "service": base_services / f"{module_name}_service.py",
        "wiring": base_services / f"{module_name}_wiring.py",
    }
    
    # Arquivos opcionais  
    optional_files = {
        "api_dependencies": base_api / "dependencies.py",
        "test_api": base_tests / "test_api.py",
        "test_service": base_tests / "test_service.py",
    }
    
    # Verificar obrigatórios
    for name, path in required_files.items():
        checks[f"has_{name}"] = path.exists()
    
    # Verificar opcionais
    for name, path in optional_files.items():
        checks[f"has_{name}"] = path.exists()
    
    return checks


def check_api_contracts(module_name: str) -> Dict[str, bool]:
    """Verifica contratos de API."""
    checks = {}
    
    routes_path = Path(f"app/app/api/{module_name}/routes.py")
    if not routes_path.exists():
        return {"routes_file_missing": False}
    
    content = routes_path.read_text()
    
    # Verificações básicas
    checks["has_versioned_prefix"] = f'prefix="/v1/{module_name}"' in content
    checks["has_router_instance"] = "router = APIRouter" in content  
    checks["has_proper_tags"] = f'tags=[' in content
    checks["imports_auth_deps"] = "from app.api.auth.dependencies import" in content
    checks["has_error_handling"] = "HTTPException" in content
    checks["has_logging"] = "logger" in content
    
    # Verificar endpoints CRUD básicos (heurística)
    checks["has_get_endpoint"] = "@router.get(" in content
    checks["has_post_endpoint"] = "@router.post(" in content
    checks["has_response_models"] = "response_model=" in content
    
    return checks


def check_implementation_contracts(module_name: str) -> Dict[str, bool]:
    """Verifica contratos de implementação."""
    checks = {}
    
    service_path = Path(f"app/app/services/{module_name}_service.py")
    if not service_path.exists():
        return {"service_file_missing": False}
    
    content = service_path.read_text()
    
    # Service layer
    checks["has_service_class"] = f"class {module_name.title()}Service" in content
    checks["has_domain_models"] = "@dataclass" in content  
    checks["has_protocol_interface"] = "Protocol" in content
    checks["has_custom_exceptions"] = "class " in content and "Error(Exception)" in content
    checks["has_structured_logging"] = 'logger.info("' in content and 'extra=' in content
    checks["has_dependency_injection"] = "def __init__(self" in content
    
    # Wiring
    wiring_path = Path(f"app/app/services/{module_name}_wiring.py")  
    checks["has_wiring_file"] = wiring_path.exists()
    
    if wiring_path.exists():
        wiring_content = wiring_path.read_text()
        checks["has_factory_function"] = f"def build_{module_name}_service" in wiring_content
    
    return checks


def generate_report(module_name: str, detailed: bool = False) -> Tuple[int, str]:
    """Gera relatório completo de validação."""
    
    print(f"\n🔍 Validando módulo '{module_name}'...")
    
    # Executar verificações
    file_checks = check_file_structure(module_name)
    api_checks = check_api_contracts(module_name) 
    impl_checks = check_implementation_contracts(module_name)
    
    # Calcular scores
    total_checks = len(file_checks) + len(api_checks) + len(impl_checks)
    passed_checks = sum([
        sum(file_checks.values()),
        sum(api_checks.values()), 
        sum(impl_checks.values())
    ])
    
    score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
    
    # Relatório
    report = f"""
📊 **RELATÓRIO DE CONFORMIDADE**

Módulo: {module_name}
Score: {score:.1f}% ({passed_checks}/{total_checks})

🏗️  **ESTRUTURA DE ARQUIVOS**
"""
    
    for check, passed in file_checks.items():
        icon = "✅" if passed else "❌"
        report += f"   {icon} {check.replace('_', ' ')}\n"
    
    report += f"\n🌐 **CONTRATOS DE API**\n"
    for check, passed in api_checks.items():
        icon = "✅" if passed else "❌" 
        report += f"   {icon} {check.replace('_', ' ')}\n"
    
    report += f"\n⚙️  **CONTRATOS DE IMPLEMENTAÇÃO**\n"
    for check, passed in impl_checks.items():
        icon = "✅" if passed else "❌"
        report += f"   {icon} {check.replace('_', ' ')}\n"
    
    # Recomendações
    if score < 70:
        report += f"\n🚨 **AÇÃO NECESSÁRIA**\n"
        report += f"   Score muito baixo. Revisar estrutura básica.\n"
    elif score < 90:
        report += f"\n⚠️  **MELHORIAS SUGERIDAS**\n"
        report += f"   Implementar itens faltantes para conformidade total.\n"
    else:
        report += f"\n🎉 **EXCELENTE!**\n"
        report += f"   Módulo segue contratos estabelecidos.\n"
    
    # Detailed output
    if detailed:
        report += f"\n📋 **PRÓXIMOS PASSOS**\n"
        
        missing_required = [k for k, v in file_checks.items() if not v and k.startswith("has_") and not k.startswith("has_test")]
        if missing_required:
            report += f"   1. Implementar arquivos obrigatórios faltantes\n"
        
        if not api_checks.get("imports_auth_deps", False):
            report += f"   2. Adicionar imports de dependências de auth\n"
            
        if not impl_checks.get("has_structured_logging", False):
            report += f"   3. Implementar logging estruturado\n"
        
        if score >= 90:
            report += f"   🏆 Módulo está pronto para produção!\n"
    
    return int(score), report


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Valida conformidade de módulo com contratos estabelecidos."
    )
    parser.add_argument("module_name", help="Nome do módulo para validar")
    parser.add_argument("--detailed", "-d", action="store_true", help="Relatório detalhado")
    
    args = parser.parse_args()
    
    # Verificar se estamos no diretório correto
    if not Path("app/app").exists():
        print("❌ Execute este script no root do projeto (onde está app/)")
        sys.exit(1)
    
    # Verificar se módulo existe
    module_path = Path(f"app/app/api/{args.module_name}")
    if not module_path.exists():
        print(f"❌ Módulo '{args.module_name}' não encontrado em {module_path}")
        print(f"💡 Use: python scripts/create_module.py {args.module_name} 'Display Name' 'Description'")
        sys.exit(1)
    
    # Gerar relatório
    score, report = generate_report(args.module_name, args.detailed)
    
    print(report)
    
    # Exit code baseado no score
    if score >= 90:
        print("🏆 Status: EXCELENTE")
        sys.exit(0)
    elif score >= 70:
        print("⚠️  Status: BOM (melhorias sugeridas)")
        sys.exit(0)  
    else:
        print("🚨 Status: PRECISA CORREÇÃO")
        sys.exit(1)


if __name__ == "__main__":
    main()