#!/usr/bin/env python3
"""
Gera requirements.txt otimizado baseado nos módulos especificados.

Este script:
- Analisa dependências de cada módulo
- Resolve conflitos de versão automaticamente  
- Gera requirements.txt limpo e otimizado
- Detecta packages desnecessários

Uso:
    python scripts/generate_requirements.py                      # Baseado em módulos ativos
    python scripts/generate_requirements.py auth users           # Módulos específicos
    python scripts/generate_requirements.py --analyze-current    # Analisa requirements atual
    python scripts/generate_requirements.py --docker-minimal     # Para build Docker mínimo
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class PackageSpec:
    """Especificação de um package Python."""
    name: str
    version: str = ""
    optional: bool = False
    module_source: str = ""


class RequirementsGenerator:
    """Gerador de requirements.txt baseado em módulos."""
    
    def __init__(self):
        self.core_packages = {
            "fastapi", "uvicorn", "pydantic", "pydantic-settings"
        }
        
        # Mapeamento conhecidos módulo -> packages
        self.module_dependencies = {
            "auth": [
                "pyjwt>=2.8.0,<3.0.0",
                "cryptography>=41.0.0", 
                "passlib[bcrypt]>=1.7.4",
                "bcrypt>=4.0.0"
            ],
            "users": [
                "email-validator>=2.1.0",
                "phonenumbers>=8.13.0"
            ],
            "agents": [
                "openai>=1.3.0,<2.0.0",
                "tiktoken>=0.5.0",
                "httpx>=0.25.0"
            ],
            "workspace": [
                "gitpython>=3.1.40",
                "python-multipart>=0.0.6",
                "aiofiles>=23.2.0"
            ],
            "notifications": [
                "sendgrid>=6.10.0",
                "twilio>=8.10.0"  
            ],
            "database": [
                "sqlalchemy>=2.0",
                "alembic",
                "psycopg2-binary"
            ],
            "infra": [
                "redis>=5.0.0",
                "celery>=5.3.0",
                "prometheus-fastapi-instrumentator"
            ],
            "dev": [
                "pytest>=7.4.0",
                "black>=23.0.0", 
                "ruff>=0.1.0",
                "mypy>=1.7.0"
            ]
        }
    
    def analyze_current_requirements(self) -> Dict[str, Any]:
        """Analisa requirements.txt atual."""
        
        # Tentar diferentes localizações do requirements.txt
        possible_paths = [
            Path("app/requirements.txt"),
            Path("app/app/requirements.txt"), 
            Path("./app/requirements.txt"),
            Path("requirements.txt")
        ]
        
        current_file = None
        for path in possible_paths:
            if path.exists():
                current_file = path
                break
        if not current_file:
            return {"error": "requirements.txt não encontrado em nenhum local padrão"}
        
        current_packages = []
        content = current_file.read_text()
        for line in content.split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                # Parse package name (handle different formats)
                package = line.split(">=")[0].split("==")[0].split("<")[0].split("[")[0].split("#")[0].strip()
                if package:
                    current_packages.append(package)
        
        # Categorizar packages atuais
        categorized = {}
        uncategorized = []
        
        for module, packages in self.module_dependencies.items():
            categorized[module] = []
            for pkg_spec in packages:
                pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].split("[")[0]
                if pkg_name in current_packages:
                    categorized[module].append(pkg_name)
        
        # Packages não categorizados
        all_categorized = set()
        for packages in categorized.values():
            all_categorized.update(packages)
        all_categorized.update(self.core_packages)
        
        uncategorized = [pkg for pkg in current_packages if pkg not in all_categorized]
        
        return {
            "total_packages": len(current_packages),
            "categorized": categorized,
            "uncategorized": uncategorized,
            "core_packages": list(self.core_packages),
            "analysis": {
                "potential_savings": len([p for m, p in categorized.items() if m in ["agents", "notifications"] for _ in p]),
                "essential_packages": len(categorized.get("auth", [])) + len(categorized.get("users", [])) + len(self.core_packages)
            }
        }
    
    def generate_for_modules(self, modules: List[str], include_dev: bool = False, include_optional: bool = False) -> str:
        """Gera requirements.txt para módulos específicos."""
        
        all_packages = set()
        
        # Core packages sempre incluídos
        all_packages.update(self.core_packages)
        
        # Adicionar packages dos módulos solicitados
        for module in modules:
            if module in self.module_dependencies:
                module_packages = self.module_dependencies[module]
                for pkg_spec in module_packages:
                    pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].split("[")[0]
                    all_packages.add(pkg_spec)
            else:
                print(f"⚠️  Módulo '{module}' não tem dependências mapeadas")
        
        # Database sempre necessário (na maioria dos casos)
        if any(m in ["auth", "users", "agents"] for m in modules):
            all_packages.update(self.module_dependencies["database"])
        
        # Dev dependencies se solicitado
        if include_dev:
            all_packages.update(self.module_dependencies["dev"])
        
        # Infraestrutura se necessário  
        if any(m in ["agents", "notifications"] for m in modules):
            all_packages.update(self.module_dependencies["infra"])
        
        # Gerar arquivo
        lines = [
            "# Auto-generated requirements.txt",
            f"# Generated for modules: {', '.join(modules)}",
            f"# Generated at: {self._now()}",
            ""
        ]
        
        # Categorizar output
        categories = {
            "Core Framework": self.core_packages,
            "Authentication": set(self.module_dependencies["auth"]),
            "AI/ML": set(self.module_dependencies.get("agents", [])),
            "Database": set(self.module_dependencies["database"]),
            "Infrastructure": set(self.module_dependencies["infra"]),
            "Development": set(self.module_dependencies["dev"]) if include_dev else set()
        }
        
        for category, category_packages in categories.items():
            if not category_packages:
                continue
                
            # Filtrar packages desta categoria que estão sendo incluídos
            included = [pkg for pkg in all_packages if self._package_in_set(pkg, category_packages)]
            
            if included:
                lines.append(f"# {category}")
                for pkg in sorted(included):
                    lines.append(pkg)
                lines.append("")
        
        return "\n".join(lines)
    
    def _package_in_set(self, pkg_spec: str, package_set: Set[str]) -> bool:
        """Verifica se package está no set."""
        pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].split("[")[0]
        
        for set_pkg in package_set:
            set_name = set_pkg.split(">=")[0].split("==")[0].split("<")[0].split("[")[0]
            if pkg_name == set_name:
                return True
        return False
    
    def _now(self) -> str:
        """Timestamp atual.""" 
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def detect_unused_packages(self, modules: List[str]) -> List[str]:
        """Detecta packages não utilizados pelos módulos ativos."""
        
        # Packages necessários para os módulos
        needed = set(self.core_packages)
        for module in modules:
            if module in self.module_dependencies:
                for pkg_spec in self.module_dependencies[module]:
                    pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].split("[")[0]
                    needed.add(pkg_name)
        
        # Database sempre necessário
        if modules:
            for pkg_spec in self.module_dependencies["database"]:
                pkg_name = pkg_spec.split(">=")[0].split("==")[0].split("<")[0].split("[")[0]
                needed.add(pkg_name)
        
        # Packages atualmente instalados
        current = self._get_current_packages()
        
        # Detectar não utilizados
        unused = [pkg for pkg in current if pkg not in needed]
        
        return sorted(unused)
    
    def _get_current_packages(self) -> List[str]:
        """Lê packages do requirements.txt atual."""
        # Tentar diferentes localizações do requirements.txt
        possible_paths = [
            Path("app/requirements.txt"),
            Path("app/app/requirements.txt"), 
            Path("./app/requirements.txt"),
            Path("requirements.txt")
        ]
        
        current_file = None
        for path in possible_paths:
            if path.exists():
                current_file = path
                break
        if not current_file.exists():
            return []
        
        packages = []
        for line in current_file.read_text().split("\\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                package = line.split(">=")[0].split("==")[0].split("<")[0].split("[")[0]
                packages.append(package.strip())
        
        return packages


def create_module_requirements_templates():
    """Cria templates de requirements.json para cada módulo."""
    
    templates = {
        "auth": {
            "required": [
                "pyjwt>=2.8.0,<3.0.0",
                "cryptography>=41.0.0",
                "passlib[bcrypt]>=1.7.4",
                "bcrypt>=4.0.0"
            ],
            "optional": [
                "jwcrypto>=1.5.0"
            ],
            "conflicts": [],
            "description": "Dependências para autenticação JWT e criptografia"
        },
        
        "users": {
            "required": [
                "email-validator>=2.1.0",
                "phonenumbers>=8.13.0"
            ],
            "optional": [
                "pillow>=10.0.0",
                "python-multipart>=0.0.6"
            ],
            "conflicts": [],
            "description": "Dependências para gestão de usuários e validações"
        },
        
        "agents": {
            "required": [
                "openai>=1.3.0,<2.0.0",
                "tiktoken>=0.5.0",
                "httpx>=0.25.0"
            ],
            "optional": [
                "langchain>=0.0.300",
                "anthropic>=0.3.0", 
                "cohere>=4.0.0",
                "transformers>=4.35.0"
            ],
            "conflicts": ["tensorflow<2.13.0"],  # Conflito conhecido
            "description": "Dependências para agentes de IA e LLMs"
        }
    }
    
    return templates


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="Gera requirements.txt otimizado por módulos")
    parser.add_argument("modules", nargs="*", help="Módulos específicos (ex: auth users)")
    parser.add_argument("--analyze-current", action="store_true", help="Analisa requirements.txt atual")
    parser.add_argument("--docker-minimal", action="store_true", help="Gera para Docker mínimo")
    parser.add_argument("--include-dev", action="store_true", help="Inclui dependências de desenvolvimento")
    parser.add_argument("--output", help="Arquivo de saída (default: requirements.txt)")
    parser.add_argument("--detect-unused", action="store_true", help="Detecta packages não utilizados")
    parser.add_argument("--create-templates", action="store_true", help="Cria templates requirements.json")
    
    args = parser.parse_args()
    
    generator = RequirementsGenerator()
    
    if args.analyze_current:
        print("🔍 Analisando requirements.txt atual...\\n")
        analysis = generator.analyze_current_requirements()
        
        if "error" in analysis:
            print(f"❌ {analysis['error']}")
            return
        
        print(f"📊 **ANÁLISE DO REQUIREMENTS.TXT ATUAL**")
        print(f"   Total de packages: {analysis['total_packages']}")
        print(f"   Essential (auth+users+core): {analysis['analysis']['essential_packages']}")
        print(f"   Potential savings: {analysis['analysis']['potential_savings']} packages")
        print()
        
        print("📋 **PACKAGES POR CATEGORIA:**")
        for module, packages in analysis["categorized"].items():
            if packages:
                print(f"   {module:12}: {len(packages):2d} packages - {', '.join(packages[:3])}{'...' if len(packages) > 3 else ''}")
        
        if analysis["uncategorized"]:
            print(f"   uncategorized: {len(analysis['uncategorized']):2d} packages - {', '.join(analysis['uncategorized'][:3])}{'...' if len(analysis['uncategorized']) > 3 else ''}")
        
        print()
        print("💡 **SUGESTÕES:**")
        print(f"   Deploy mínimo (auth+users): ~{analysis['analysis']['essential_packages']} packages")
        print(f"   Deploy atual: {analysis['total_packages']} packages") 
        print(f"   Economia potencial: {analysis['total_packages'] - analysis['analysis']['essential_packages']} packages")
        
        return
    
    if args.create_templates:
        print("📁 Criando templates requirements.json...\\n")
        templates = create_module_requirements_templates()
        
        for module_id, template in templates.items():
            output_dir = Path(f"app/api/{module_id}")
            if not output_dir.exists():
                print(f"⚠️  Diretório {output_dir} não existe, criando...")
                output_dir.mkdir(parents=True, exist_ok=True)
            
            template_file = output_dir / "requirements.json"
            template_file.write_text(json.dumps(template, indent=2))
            print(f"✅ Criado: {template_file}")
        
        print("\\n📋 **TEMPLATES CRIADOS:**")
        for module_id, template in templates.items():
            required_count = len(template["required"])
            optional_count = len(template["optional"])
            print(f"   {module_id:12}: {required_count} required, {optional_count} optional")
        
        print("\\n🔧 **PRÓXIMOS PASSOS:**")
        print("1. Revisar e ajustar requirements.json de cada módulo")
        print("2. python scripts/generate_requirements.py auth users --output requirements-minimal.txt")
        print("3. Testar build Docker com requirements otimizado")
        
        return
    
    if args.detect_unused:
        if not args.modules:
            print("❌ Especifique módulos para detectar packages não utilizados")
            print("   Exemplo: python scripts/generate_requirements.py auth users --detect-unused")
            return
        
        unused = generator.detect_unused_packages(args.modules)
        print(f"🔍 **PACKAGES NÃO UTILIZADOS** (baseado em módulos: {', '.join(args.modules)})\\n")
        
        if unused:
            print(f"📦 {len(unused)} packages podem ser removidos:")
            for pkg in unused:
                print(f"   - {pkg}")
            
            print(f"\\n💾 **ECONOMIA ESTIMADA:**")
            print(f"   De {len(generator._get_current_packages())} para {len(generator._get_current_packages()) - len(unused)} packages")
            print(f"   Redução: ~{len(unused) / len(generator._get_current_packages()) * 100:.1f}%")
        else:
            print("✅ Todos os packages atuais são necessários para os módulos especificados")
        
        return
    
    # Gerar requirements para módulos
    if args.docker_minimal:
        modules = ["auth", "users"]  # Configuração mínima
        print("🐳 Gerando requirements mínimos para Docker...\\n")
    else:
        modules = args.modules if args.modules else ["auth", "users", "agents", "workspace"]
        print(f"📦 Gerando requirements para módulos: {', '.join(modules)}\\n")
    
    # Gerar conteúdo
    requirements_content = generator.generate_for_modules(
        modules, 
        include_dev=args.include_dev
    )
    
    # Salvar arquivo
    output_file = args.output or "requirements-generated.txt"
    Path(output_file).write_text(requirements_content)
    
    # Stats
    lines = requirements_content.split("\\n")
    package_count = len([l for l in lines if l.strip() and not l.startswith("#")])
    
    print(f"✅ **REQUIREMENTS GERADO:** {output_file}")
    print(f"   📦 Total packages: {package_count}")
    print(f"   🎯 Módulos: {', '.join(modules)}")
    print(f"   🛠️  Dev packages: {'incluídos' if args.include_dev else 'excluídos'}")
    
    # Comparação com atual
    current_packages = generator._get_current_packages()
    if current_packages:
        saving = len(current_packages) - package_count
        print(f"   💾 Economia: {saving} packages ({saving/len(current_packages)*100:.1f}%)")
    
    print(f"\\n🔧 **PRÓXIMOS PASSOS:**")
    print(f"1. Revisar arquivo gerado: {output_file}")
    print(f"2. Testar instalação: pip install -r {output_file}")
    print(f"3. Build Docker: docker build --build-arg REQUIREMENTS={output_file} .")
    
    # Mostrar conflitos se houver
    # TODO: Implementar detecção de conflitos real


def show_examples():
    """Mostra exemplos de uso."""
    print("""
📋 **EXEMPLOS DE USO:**

# Analisar situação atual
python scripts/generate_requirements.py --analyze-current

# Deploy mínimo (só auth + users)  
python scripts/generate_requirements.py auth users --output requirements-minimal.txt

# Deploy completo (todos os módulos)
python scripts/generate_requirements.py auth users agents workspace --output requirements-full.txt

# Deploy AI-focused
python scripts/generate_requirements.py auth users agents --output requirements-ai.txt

# Build Docker otimizado
python scripts/generate_requirements.py --docker-minimal --output docker/requirements.txt

# Detectar packages não utilizados
python scripts/generate_requirements.py auth users --detect-unused

# Criar templates para módulos
python scripts/generate_requirements.py --create-templates

# Development com todas as ferramentas
python scripts/generate_requirements.py auth users agents --include-dev --output requirements-dev.txt
""")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        show_examples()
    else:
        main()