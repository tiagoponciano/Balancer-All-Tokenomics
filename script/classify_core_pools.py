#!/usr/bin/env python3
"""
Script para classificar pools como core ou non-core baseado no histórico do CSV.

Regra lógica:
Uma pool é CORE em uma data D se existir no CSV histórico uma linha tal que:
- address = pool_address
- D >= added_date
- (removed_date IS NULL OR D < removed_date)

Caso contrário, ela é NON-CORE.

Requisitos:
1. Arquivo de histórico de core pools (core_pools_results.csv):
   - Deve conter colunas: 'address', 'added_date', 'removed_date' (opcional)
   - Cada linha representa um período em que uma pool foi Core Pool
   - removed_date pode ser NULL se a pool ainda é Core Pool

2. Dataset diário (veBAL.csv por padrão):
   - Deve conter colunas com address da pool e data
   - O script detecta automaticamente colunas com nomes como:
     * Address: 'project_contract_address', 'address', 'pool_address', etc.
     * Date: 'block_date', 'date', 'day', 'timestamp', etc.

3. Arquivo de saída:
   - classification_core_pools.csv com colunas: 'address', 'day', 'is_core'
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np

# Configurações
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Arquivos de entrada (ajuste conforme necessário)
# Histórico de core pools: deve conter colunas 'address', 'added_date', 'removed_date' (opcional)
CORE_POOLS_HISTORY_FILE = DATA_DIR / "core_pools_results.csv"  # Histórico de core pools
# Dataset diário: deve conter colunas com address da pool e data
DAILY_DATASET_FILE = DATA_DIR / "veBAL.csv"  # Dataset diário (veBAL.csv)

# Arquivo de saída
OUTPUT_FILE = DATA_DIR / "classification_core_pools.csv"


def classify_core_pools(
    core_pools_file: Path = CORE_POOLS_HISTORY_FILE,
    daily_dataset_file: Path = DAILY_DATASET_FILE,
    output_file: Path = OUTPUT_FILE
):
    """
    Classifica pools como core ou non-core baseado no histórico.
    
    Args:
        core_pools_file: Caminho para o CSV histórico de core pools
        daily_dataset_file: Caminho para o dataset diário
        output_file: Caminho para o arquivo de saída
    """
    print("=" * 60)
    print("🚀 Classificação de Core Pools")
    print("=" * 60)
    
    print("\n📖 Lendo arquivos...")
    
    # Verificar se os arquivos existem
    if not core_pools_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {core_pools_file}")
    if not daily_dataset_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {daily_dataset_file}")
    
    # Ler o CSV histórico de core pools
    core_pools_df = pd.read_csv(core_pools_file)
    
    # Ler o dataset diário
    daily_df = pd.read_csv(daily_dataset_file)
    
    print(f"✅ Core pools CSV: {len(core_pools_df):,} linhas")
    print(f"✅ Dataset diário: {len(daily_df):,} linhas")
    
    # Mostrar colunas disponíveis para debug
    print(f"\n📋 Colunas no histórico de core pools: {list(core_pools_df.columns)}")
    print(f"📋 Colunas no dataset diário: {list(daily_df.columns)}")
    
    # Verificar colunas necessárias no histórico de core pools
    required_core_cols = ['address', 'added_date']
    missing_core = [col for col in required_core_cols if col not in core_pools_df.columns]
    
    if missing_core:
        raise ValueError(f"Colunas faltando no histórico de core pools: {missing_core}")
    
    # Detectar automaticamente colunas do dataset diário
    # Tentar diferentes nomes possíveis para address e date
    address_col = None
    date_col = None
    
    # Possíveis nomes para coluna de address
    address_candidates = ['project_contract_address', 'address', 'pool_address', 'pool_id', 'contract_address']
    for col in address_candidates:
        if col in daily_df.columns:
            address_col = col
            break
    
    # Possíveis nomes para coluna de data
    date_candidates = ['block_date', 'date', 'day', 'timestamp', 'block_timestamp']
    for col in date_candidates:
        if col in daily_df.columns:
            date_col = col
            break
    
    if address_col is None:
        raise ValueError(
            f"Não foi possível encontrar coluna de address no dataset diário. "
            f"Colunas disponíveis: {list(daily_df.columns)}. "
            f"Tente renomear uma coluna para um destes nomes: {address_candidates}"
        )
    
    if date_col is None:
        raise ValueError(
            f"Não foi possível encontrar coluna de data no dataset diário. "
            f"Colunas disponíveis: {list(daily_df.columns)}. "
            f"Tente renomear uma coluna para um destes nomes: {date_candidates}"
        )
    
    print(f"\n✅ Colunas detectadas:")
    print(f"   Address: {address_col}")
    print(f"   Date: {date_col}")
    
    # Converter datas para datetime
    print("\n🔄 Convertendo datas...")
    core_pools_df['added_date'] = pd.to_datetime(core_pools_df['added_date'], errors='coerce')
    
    # Verificar se removed_date existe, se não, criar coluna vazia
    if 'removed_date' not in core_pools_df.columns:
        core_pools_df['removed_date'] = pd.NaT
    else:
        core_pools_df['removed_date'] = pd.to_datetime(core_pools_df['removed_date'], errors='coerce')
    
    daily_df[date_col] = pd.to_datetime(daily_df[date_col], errors='coerce')
    
    # Remover timezone se existir (tornar tudo tz-naive)
    def remove_timezone(series):
        """Remove timezone de uma série de datetime se existir."""
        try:
            if hasattr(series.dt, 'tz') and series.dt.tz is not None:
                return series.dt.tz_localize(None)
        except (AttributeError, TypeError):
            pass
        return series
    
    core_pools_df['added_date'] = remove_timezone(core_pools_df['added_date'])
    core_pools_df['removed_date'] = remove_timezone(core_pools_df['removed_date'])
    daily_df[date_col] = remove_timezone(daily_df[date_col])
    
    # Remover linhas com datas inválidas
    initial_daily_count = len(daily_df)
    daily_df = daily_df.dropna(subset=[date_col])
    core_pools_df = core_pools_df.dropna(subset=['added_date'])
    
    if len(daily_df) < initial_daily_count:
        print(f"⚠️  Removidas {initial_daily_count - len(daily_df):,} linhas com datas inválidas do dataset diário")
    
    print(f"✅ Dataset diário após limpeza: {len(daily_df):,} linhas")
    print(f"✅ Histórico de core pools após limpeza: {len(core_pools_df):,} linhas")
    
    print("\n🔍 Classificando pools...")
    
    # Método otimizado usando merge e condições vetorizadas
    # Criar uma cópia do dataset diário com colunas normalizadas
    result_df = daily_df[[address_col, date_col]].copy()
    result_df.columns = ['address', 'day']
    result_df = result_df.drop_duplicates()
    
    print(f"📊 Total de combinações únicas (address, day): {len(result_df):,}")
    
    # Fazer merge com o histórico de core pools
    # Isso cria todas as combinações possíveis
    merged = result_df.merge(
        core_pools_df[['address', 'added_date', 'removed_date']],
        on='address',
        how='left',
        suffixes=('', '_core')
    )
    
    print(f"📊 Total de combinações após merge: {len(merged):,}")
    
    # Aplicar a lógica de classificação de forma vetorizada
    # Uma pool é CORE se:
    # - day >= added_date
    # - (removed_date IS NULL OR day < removed_date)
    
    # Filtrar apenas registros onde day >= added_date
    valid_intervals = merged[
        (merged['day'] >= merged['added_date'])
    ].copy()
    
    # Para cada intervalo válido, verificar se day < removed_date (ou removed_date é NULL)
    valid_intervals['is_valid_interval'] = (
        valid_intervals['removed_date'].isna() | 
        (valid_intervals['day'] < valid_intervals['removed_date'])
    )
    
    # Filtrar apenas intervalos válidos
    core_intervals = valid_intervals[valid_intervals['is_valid_interval']]
    
    # Agora, para cada (address, day) único, verificar se existe pelo menos um intervalo válido
    core_classification = core_intervals.groupby(['address', 'day']).size().reset_index(name='count')
    core_classification['is_core'] = True
    
    # Fazer merge de volta com o dataset original
    result_df = result_df.merge(
        core_classification[['address', 'day', 'is_core']],
        on=['address', 'day'],
        how='left'
    )
    
    # Preencher False onde não há classificação (não é core)
    result_df['is_core'] = result_df['is_core'].fillna(False).astype(bool)
    
    # Estatísticas
    total_rows = len(result_df)
    core_rows = result_df['is_core'].sum()
    non_core_rows = total_rows - core_rows
    
    print(f"\n📊 Estatísticas:")
    print(f"  Total de combinações únicas: {total_rows:,}")
    print(f"  Core: {core_rows:,} ({100 * core_rows / total_rows:.2f}%)")
    print(f"  Non-core: {non_core_rows:,} ({100 * non_core_rows / total_rows:.2f}%)")
    
    # Ordenar por address e day
    result_df = result_df.sort_values(['address', 'day'])
    
    # Salvar o resultado
    print(f"\n💾 Salvando resultado em {output_file}...")
    result_df.to_csv(output_file, index=False)
    
    print(f"✅ Arquivo salvo com sucesso!")
    print(f"   Total de linhas no arquivo de saída: {len(result_df):,}")
    
    # Mostrar algumas amostras
    print("\n📋 Amostra dos resultados (primeiras 20 linhas):")
    print(result_df.head(20).to_string(index=False))
    
    # Verificar alguns casos específicos para validação
    print("\n🔍 Validação - Verificando alguns casos específicos:")
    
    # Pegar alguns addresses únicos para verificar
    sample_addresses = result_df['address'].unique()[:3]
    
    for address in sample_addresses:
        address_data = result_df[result_df['address'] == address].head(10)
        if len(address_data) > 0:
            print(f"\n  Address: {address}")
            print(address_data.to_string(index=False))
    
    # Verificar transições core -> non-core -> core
    print("\n🔍 Verificando transições Core <-> Non-Core:")
    transitions = []
    for address in result_df['address'].unique()[:5]:
        addr_data = result_df[result_df['address'] == address].sort_values('day')
        if len(addr_data) > 1:
            changes = addr_data['is_core'].ne(addr_data['is_core'].shift()).sum()
            if changes > 0:
                transitions.append({
                    'address': address,
                    'transitions': changes,
                    'first_date': addr_data['day'].min(),
                    'last_date': addr_data['day'].max()
                })
    
    if transitions:
        transitions_df = pd.DataFrame(transitions)
        print(transitions_df.to_string(index=False))
    
    return result_df


def main():
    """Função principal"""
    try:
        result_df = classify_core_pools()
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
