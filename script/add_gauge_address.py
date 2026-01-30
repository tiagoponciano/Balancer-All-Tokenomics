#!/usr/bin/env python3
"""
Script para adicionar gauge_address ao veBAL.csv baseado no match com FSN_data.csv

Lógica:
- Match entre poolId (primeiros 42 caracteres) do FSN_data.csv 
  e project_contract_address do veBAL.csv
- Se os primeiros 42 caracteres de poolId forem iguais ao project_contract_address,
  adiciona o id (gauge_address) do FSN_data.csv ao veBAL.csv
"""
import pandas as pd
from pathlib import Path
from typing import Optional

# Configurações
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Arquivos de entrada
VEBAL_FILE = DATA_DIR / "veBAL.csv"
FSN_DATA_FILE = DATA_DIR / "FSN_data.csv"

# Arquivo de saída (sobrescreve o veBAL.csv original)
OUTPUT_FILE = DATA_DIR / "veBAL.csv"


def add_gauge_address(
    vebal_file: Path = VEBAL_FILE,
    fsn_data_file: Path = FSN_DATA_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Adiciona gauge_address ao veBAL.csv baseado no match com FSN_data.csv.
    
    Args:
        vebal_file: Caminho para o CSV do veBAL
        fsn_data_file: Caminho para o CSV do FSN_data
        output_file: Caminho para o arquivo de saída
        
    Returns:
        DataFrame com os dados do veBAL incluindo gauge_address
    """
    print("=" * 60)
    print("🔗 Adicionando Gauge Address ao veBAL")
    print("=" * 60)
    
    # Verificar se os arquivos existem
    if not vebal_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {vebal_file}")
    if not fsn_data_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {fsn_data_file}")
    
    print("\n📖 Lendo arquivos...")
    
    # Ler dados do veBAL
    vebal_df = pd.read_csv(vebal_file)
    print(f"✅ veBAL CSV: {len(vebal_df):,} linhas")
    print(f"   Colunas: {list(vebal_df.columns)}")
    
    # Verificar se project_contract_address existe
    if 'project_contract_address' not in vebal_df.columns:
        raise ValueError(
            f"Coluna 'project_contract_address' não encontrada no veBAL. "
            f"Colunas disponíveis: {list(vebal_df.columns)}"
        )
    
    # Ler dados do FSN
    fsn_df = pd.read_csv(fsn_data_file)
    print(f"✅ FSN_data CSV: {len(fsn_df):,} linhas")
    print(f"   Colunas: {list(fsn_df.columns)}")
    
    # Verificar se id e poolId existem
    if 'id' not in fsn_df.columns:
        raise ValueError(
            f"Coluna 'id' não encontrada no FSN_data. "
            f"Colunas disponíveis: {list(fsn_df.columns)}"
        )
    if 'poolId' not in fsn_df.columns:
        raise ValueError(
            f"Coluna 'poolId' não encontrada no FSN_data. "
            f"Colunas disponíveis: {list(fsn_df.columns)}"
        )
    
    print("\n🧹 Limpando e preparando dados...")
    
    # Limpar dados vazios
    initial_fsn = len(fsn_df)
    fsn_df = fsn_df[fsn_df['poolId'].notna() & (fsn_df['poolId'] != '')]
    if len(fsn_df) < initial_fsn:
        print(f"   Removidas {initial_fsn - len(fsn_df):,} linhas com poolId vazio do FSN_data")
    
    initial_vebal = len(vebal_df)
    vebal_df = vebal_df[vebal_df['project_contract_address'].notna() & (vebal_df['project_contract_address'] != '')]
    if len(vebal_df) < initial_vebal:
        print(f"   Removidas {initial_vebal - len(vebal_df):,} linhas com project_contract_address vazio do veBAL")
    
    # Normalizar endereços (lowercase, remover espaços)
    vebal_df['project_contract_address'] = vebal_df['project_contract_address'].astype(str).str.lower().str.strip()
    fsn_df['poolId'] = fsn_df['poolId'].astype(str).str.lower().str.strip()
    fsn_df['id'] = fsn_df['id'].astype(str).str.lower().str.strip()
    
    print("\n🔍 Criando match entre datasets...")
    
    # Criar uma coluna no FSN com os primeiros 42 caracteres do poolId
    fsn_df['poolId_42'] = fsn_df['poolId'].str[:42]
    
    # Remover linhas onde poolId tem menos de 42 caracteres (após limpeza)
    fsn_df = fsn_df[fsn_df['poolId_42'].str.len() >= 42]
    
    print(f"   FSN_data após processamento: {len(fsn_df):,} linhas")
    print(f"   Pools únicas no FSN_data: {fsn_df['poolId_42'].nunique():,}")
    print(f"   Gauge addresses únicos: {fsn_df['id'].nunique():,}")
    
    # Verificar se há pools duplicadas (mesmo poolId_42 mas gauge_address diferente)
    duplicates = fsn_df.groupby('poolId_42')['id'].nunique()
    duplicates = duplicates[duplicates > 1]
    if len(duplicates) > 0:
        print(f"\n⚠️  Aviso: {len(duplicates)} pools têm múltiplos gauge_address:")
        for pool_id, count in duplicates.head(10).items():
            gauges = fsn_df[fsn_df['poolId_42'] == pool_id]['id'].unique()
            print(f"   Pool {pool_id}: {count} gauges - {list(gauges)[:3]}")
        print("   Usando o primeiro gauge_address encontrado para cada pool")
    
    # Criar dicionário de mapeamento: poolId_42 -> gauge_address
    # Se houver múltiplos gauges para a mesma pool, usar o primeiro
    gauge_mapping = fsn_df.groupby('poolId_42')['id'].first().to_dict()
    
    print(f"\n📊 Mapeamento criado: {len(gauge_mapping):,} pools mapeadas")
    
    # Aplicar o match ao veBAL
    print("\n🔄 Aplicando match ao veBAL...")
    
    # Criar coluna gauge_address no veBAL
    vebal_df['gauge_address'] = vebal_df['project_contract_address'].map(gauge_mapping)
    
    # Estatísticas
    matched_count = vebal_df['gauge_address'].notna().sum()
    unmatched_count = len(vebal_df) - matched_count
    unique_pools_matched = vebal_df[vebal_df['gauge_address'].notna()]['project_contract_address'].nunique()
    unique_pools_total = vebal_df['project_contract_address'].nunique()
    
    print(f"\n📊 Estatísticas do match:")
    print(f"   Total de linhas no veBAL: {len(vebal_df):,}")
    print(f"   Linhas com gauge_address: {matched_count:,} ({100 * matched_count / len(vebal_df):.2f}%)")
    print(f"   Linhas sem gauge_address: {unmatched_count:,} ({100 * unmatched_count / len(vebal_df):.2f}%)")
    print(f"   Pools únicas com match: {unique_pools_matched:,} / {unique_pools_total:,} ({100 * unique_pools_matched / unique_pools_total:.2f}%)")
    
    # Mostrar algumas amostras de pools sem match
    if unmatched_count > 0:
        unmatched_pools = vebal_df[vebal_df['gauge_address'].isna()]['project_contract_address'].unique()[:10]
        print(f"\n📋 Exemplos de pools sem match (primeiras 10):")
        for pool in unmatched_pools:
            print(f"   {pool}")
    
    # Salvar resultado
    print(f"\n💾 Salvando resultado em {output_file}...")
    vebal_df.to_csv(output_file, index=False)
    
    print(f"✅ Arquivo salvo com sucesso!")
    print(f"   Total de linhas: {len(vebal_df):,}")
    print(f"   Total de colunas: {len(vebal_df.columns)}")
    
    # Mostrar amostra dos dados
    print(f"\n📋 Amostra dos dados (primeiras 10 linhas com gauge_address):")
    sample = vebal_df[vebal_df['gauge_address'].notna()].head(10)
    if len(sample) > 0:
        # Mostrar apenas colunas relevantes
        cols_to_show = ['project_contract_address', 'gauge_address', 'pool_symbol', 'block_date']
        available_cols = [col for col in cols_to_show if col in sample.columns]
        print(sample[available_cols].to_string(index=False))
    else:
        print("   Nenhuma linha com gauge_address encontrada para mostrar")
    
    return vebal_df


def main():
    """Função principal"""
    try:
        result_df = add_gauge_address()
        print("\n" + "=" * 60)
        print("✅ Processo concluído com sucesso!")
        print("=" * 60)
        return result_df
    except Exception as e:
        print(f"\n❌ Erro durante o processamento: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
