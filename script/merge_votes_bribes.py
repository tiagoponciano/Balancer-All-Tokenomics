#!/usr/bin/env python3
"""
Script para fazer merge entre Votes_Emissions.csv e Bribes.csv

Chaves de match:
- gauge_address
- day
- blockchain

Renomeações:
- amount_usdc (Bribes) → bribe_amount_usd
- daily_emissions (Votes_Emissions) → bal_emited_votes
- total_votes (Votes_Emissions) → votes_received
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

# Configurações
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Arquivos de entrada
VOTES_EMISSIONS_FILE = DATA_DIR / "Votes_Emissions.csv"
BRIBES_FILE = DATA_DIR / "Bribes.csv"

# Arquivo de saída
OUTPUT_FILE = DATA_DIR / "votes_bribes_merged.csv"


def merge_votes_bribes(
    votes_file: Path = VOTES_EMISSIONS_FILE,
    bribes_file: Path = BRIBES_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Faz merge entre Votes_Emissions.csv e Bribes.csv.
    
    Args:
        votes_file: Caminho para o CSV de Votes_Emissions
        bribes_file: Caminho para o CSV de Bribes
        output_file: Caminho para o arquivo de saída
        
    Returns:
        DataFrame com os dados mergeados
    """
    print("=" * 60)
    print("🔗 Merge de Votes_Emissions e Bribes")
    print("=" * 60)
    
    # Verificar se os arquivos existem
    if not votes_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {votes_file}")
    if not bribes_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {bribes_file}")
    
    print("\n📖 Lendo arquivos...")
    
    # Ler dados
    votes_df = pd.read_csv(votes_file)
    bribes_df = pd.read_csv(bribes_file)
    
    print(f"✅ Votes_Emissions CSV: {len(votes_df):,} linhas")
    print(f"   Colunas: {list(votes_df.columns)}")
    print(f"✅ Bribes CSV: {len(bribes_df):,} linhas")
    print(f"   Colunas: {list(bribes_df.columns)}")
    
    # Verificar colunas necessárias
    required_votes_cols = ['gauge_address', 'day', 'blockchain']
    required_bribes_cols = ['gauge_address', 'day', 'blockchain']
    
    missing_votes = [col for col in required_votes_cols if col not in votes_df.columns]
    missing_bribes = [col for col in required_bribes_cols if col not in bribes_df.columns]
    
    if missing_votes:
        raise ValueError(f"Colunas faltando no Votes_Emissions: {missing_votes}")
    if missing_bribes:
        raise ValueError(f"Colunas faltando no Bribes: {missing_bribes}")
    
    print("\n🧹 Limpando e preparando dados...")
    
    # Converter datas para datetime se necessário
    votes_df['day'] = pd.to_datetime(votes_df['day'], errors='coerce')
    bribes_df['day'] = pd.to_datetime(bribes_df['day'], errors='coerce')
    
    # Normalizar gauge_address e blockchain (lowercase, remover espaços)
    votes_df['gauge_address'] = votes_df['gauge_address'].astype(str).str.lower().str.strip()
    votes_df['blockchain'] = votes_df['blockchain'].astype(str).str.lower().str.strip()
    
    bribes_df['gauge_address'] = bribes_df['gauge_address'].astype(str).str.lower().str.strip()
    bribes_df['blockchain'] = bribes_df['blockchain'].astype(str).str.lower().str.strip()
    
    # Remover linhas com valores vazios nas chaves de match
    initial_votes = len(votes_df)
    votes_df = votes_df[
        votes_df['gauge_address'].notna() & 
        (votes_df['gauge_address'] != '') &
        (votes_df['gauge_address'].str.lower() != 'nan') &
        votes_df['day'].notna() &
        votes_df['blockchain'].notna() &
        (votes_df['blockchain'] != '')
    ]
    if len(votes_df) < initial_votes:
        print(f"   Removidas {initial_votes - len(votes_df):,} linhas inválidas do Votes_Emissions")
    
    initial_bribes = len(bribes_df)
    bribes_df = bribes_df[
        bribes_df['gauge_address'].notna() & 
        (bribes_df['gauge_address'] != '') &
        (bribes_df['gauge_address'].str.lower() != 'nan') &
        bribes_df['day'].notna() &
        bribes_df['blockchain'].notna() &
        (bribes_df['blockchain'] != '')
    ]
    if len(bribes_df) < initial_bribes:
        print(f"   Removidas {initial_bribes - len(bribes_df):,} linhas inválidas do Bribes")
    
    print(f"✅ Votes_Emissions após limpeza: {len(votes_df):,} linhas")
    print(f"✅ Bribes após limpeza: {len(bribes_df):,} linhas")
    
    # Renomear colunas antes do merge
    print("\n🔄 Renomeando colunas...")
    
    # Renomear no Bribes
    bribes_renamed = bribes_df.rename(columns={
        'amount_usdc': 'bribe_amount_usd'
    })
    
    # Renomear no Votes_Emissions
    votes_renamed = votes_df.rename(columns={
        'daily_emissions': 'bal_emited_votes',
        'total_votes': 'votes_received'
    })
    
    print("   Bribes: amount_usdc → bribe_amount_usd")
    print("   Votes_Emissions: daily_emissions → bal_emited_votes")
    print("   Votes_Emissions: total_votes → votes_received")
    
    # Fazer merge
    print("\n🔗 Fazendo merge dos dados...")
    print("   Chaves de match: gauge_address, day, blockchain")
    
    # Merge com outer join para manter todos os registros
    merged_df = pd.merge(
        votes_renamed,
        bribes_renamed,
        on=['gauge_address', 'day', 'blockchain'],
        how='outer',
        suffixes=('_votes', '_bribes'),
        indicator=True
    )
    
    # Identificar origem dos dados
    merged_df['source'] = merged_df['_merge'].map({
        'left_only': 'votes_only',
        'right_only': 'bribes_only',
        'both': 'both'
    })
    merged_df = merged_df.drop(columns=['_merge'])
    
    print(f"✅ Merge concluído: {len(merged_df):,} linhas")
    
    # Estatísticas do merge
    print(f"\n📊 Estatísticas do merge:")
    print(f"   Total de linhas após merge: {len(merged_df):,}")
    print(f"   Linhas apenas em Votes_Emissions: {(merged_df['source'] == 'votes_only').sum():,}")
    print(f"   Linhas apenas em Bribes: {(merged_df['source'] == 'bribes_only').sum():,}")
    print(f"   Linhas em ambos (match): {(merged_df['source'] == 'both').sum():,}")
    
    # Estatísticas de match por gauge_address
    matched_gauges = merged_df[merged_df['source'] == 'both']['gauge_address'].nunique()
    total_gauges_votes = votes_df['gauge_address'].nunique()
    total_gauges_bribes = bribes_df['gauge_address'].nunique()
    
    print(f"\n   Gauge addresses únicos:")
    print(f"     No Votes_Emissions: {total_gauges_votes:,}")
    print(f"     No Bribes: {total_gauges_bribes:,}")
    print(f"     Com match: {matched_gauges:,}")
    
    # Verificar se há valores duplicados de bribe_amount_usd para o mesmo match
    # (pode haver múltiplos bribes no mesmo dia)
    if 'bribe_amount_usd' in merged_df.columns:
        duplicates_check = merged_df[
            (merged_df['source'] == 'both') & 
            merged_df.duplicated(subset=['gauge_address', 'day', 'blockchain'], keep=False)
        ]
        if len(duplicates_check) > 0:
            print(f"\n⚠️  Aviso: {len(duplicates_check):,} linhas têm múltiplos registros para o mesmo (gauge_address, day, blockchain)")
            print("   Isso pode indicar múltiplos bribes no mesmo dia. Verificando...")
            
            # Agrupar e somar bribes duplicados
            print("   Agrupando e somando bribes duplicados...")
            
            # Separar colunas de votes e bribes
            votes_cols = [col for col in merged_df.columns if col.endswith('_votes') or col in ['gauge_address', 'day', 'blockchain', 'source']]
            bribes_cols = [col for col in merged_df.columns if col.endswith('_bribes') or col == 'bribe_amount_usd']
            
            # Para linhas com match, agrupar por gauge_address, day, blockchain e somar bribes
            matched_rows = merged_df[merged_df['source'] == 'both'].copy()
            
            # Agrupar e agregar
            agg_dict = {}
            for col in matched_rows.columns:
                if col in ['gauge_address', 'day', 'blockchain']:
                    agg_dict[col] = 'first'
                elif col == 'bribe_amount_usd':
                    agg_dict[col] = 'sum'  # Somar múltiplos bribes
                elif col.endswith('_votes'):
                    agg_dict[col] = 'first'  # Valores de votes são únicos
                elif col.endswith('_bribes') and col != 'bribe_amount_usd':
                    agg_dict[col] = 'first'
                elif col == 'source':
                    agg_dict[col] = 'first'
                else:
                    agg_dict[col] = 'first'
            
            matched_grouped = matched_rows.groupby(['gauge_address', 'day', 'blockchain']).agg(agg_dict).reset_index()
            
            # Combinar com linhas sem match
            votes_only = merged_df[merged_df['source'] == 'votes_only']
            bribes_only = merged_df[merged_df['source'] == 'bribes_only']
            
            # Reconstruir o DataFrame
            merged_df = pd.concat([matched_grouped, votes_only, bribes_only], ignore_index=True)
            
            print(f"   Após agrupamento: {len(merged_df):,} linhas")
    
    # Ordenar por day, blockchain, gauge_address
    merged_df = merged_df.sort_values(['day', 'blockchain', 'gauge_address'], na_position='last')
    
    # Salvar resultado
    print(f"\n💾 Salvando resultado em {output_file}...")
    merged_df.to_csv(output_file, index=False)
    
    print(f"✅ Arquivo salvo com sucesso!")
    print(f"   Total de linhas: {len(merged_df):,}")
    print(f"   Total de colunas: {len(merged_df.columns)}")
    
    # Mostrar amostra dos dados
    print(f"\n📋 Amostra dos dados (primeiras 10 linhas com match):")
    sample = merged_df[merged_df['source'] == 'both'].head(10)
    if len(sample) > 0:
        # Mostrar colunas principais
        cols_to_show = ['day', 'blockchain', 'gauge_address', 'bal_emited_votes', 'votes_received', 'bribe_amount_usd']
        available_cols = [col for col in cols_to_show if col in sample.columns]
        print(sample[available_cols].to_string(index=False))
    else:
        print("   Nenhuma linha com match encontrada para mostrar")
    
    # Estatísticas finais
    print(f"\n📊 Estatísticas finais:")
    if 'bribe_amount_usd' in merged_df.columns:
        total_bribes = merged_df['bribe_amount_usd'].sum()
        print(f"   Total de bribes (soma): {total_bribes:,.2f} USD")
    
    if 'bal_emited_votes' in merged_df.columns:
        total_emissions = merged_df['bal_emited_votes'].sum()
        print(f"   Total de BAL emitido (soma): {total_emissions:,.2f}")
    
    if 'votes_received' in merged_df.columns:
        total_votes = merged_df['votes_received'].sum()
        print(f"   Total de votes (soma): {total_votes:,.2f}")
    
    return merged_df


def main():
    """Função principal"""
    try:
        result_df = merge_votes_bribes()
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
