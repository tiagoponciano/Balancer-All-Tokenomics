#!/usr/bin/env python3
"""
Script legado para consumir dados do Dune e gerar CSV
(Use main.py para múltiplas queries)
"""
from pathlib import Path
from dune_fetcher import fetch_and_save

# Configurações
API_KEY = "QTKSQUbw3YzhNCLgsXqEbEZG7iJheA3z"
QUERY_ID = 6623057
OUTPUT_FILE = "veBAL.csv"

# Obter o diretório raiz do projeto
PROJECT_ROOT = Path(__file__).parent.parent


def main():
    """Função principal para buscar dados do Dune e gerar CSV"""
    fetch_and_save(
        api_key=API_KEY,
        query_id=QUERY_ID,
        output_filename=OUTPUT_FILE,
        project_root=PROJECT_ROOT
    )


if __name__ == "__main__":
    main()
