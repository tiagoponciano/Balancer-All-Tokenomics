#!/usr/bin/env python3
"""
Script para criar o dataset final combinando veBAL.csv e votes_bribes_merged.csv

Merge baseado em:
- gauge_address
- block_date (veBAL) = day (votes_bribes_merged)
- blockchain

Remove linhas onde project_contract_address não tem gauge_address.
"""
import pandas as pd
from pathlib import Path

# Configurações
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Arquivos de entrada
VEBAL_FILE = DATA_DIR / "veBAL.csv"
VOTES_BRIBES_FILE = DATA_DIR / "votes_bribes_merged.csv"

# Arquivo de saída
OUTPUT_FILE = DATA_DIR / "Balancer-All-Tokenomics.csv"

# Colunas desejadas na ordem final
FINAL_COLUMNS = [
    'blockchain',
    'project',
    'version',
    'block_date',
    'project_contract_address',
    'gauge_address',
    'pool_symbol',
    'pool_type',
    'swap_amount_usd',
    'tvl_usd',
    'tvl_eth',
    'total_protocol_fee_usd',
    'protocol_fee_amount_usd',
    'swap_fee_usd',
    'yield_fee_usd',
    'swap_fee_%',
    'core_non_core',
    'bal_emited_votes',
    'votes_received',
    'bribe_amount_usd'
]


def create_final_dataset(
    vebal_file: Path = VEBAL_FILE,
    votes_bribes_file: Path = VOTES_BRIBES_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Cria o dataset final combinando veBAL.csv e votes_bribes_merged.csv.
    
    Args:
        vebal_file: Caminho para o CSV do veBAL
        votes_bribes_file: Caminho para o CSV do votes_bribes_merged
        output_file: Caminho para o arquivo de saída
        
    Returns:
        DataFrame com o dataset final
    """
    print("=" * 60)
    print("🎯 Criando Dataset Final - Balancer All Tokenomics")
    print("=" * 60)
    
    # Verificar se os arquivos existem
    if not vebal_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {vebal_file}")
    if not votes_bribes_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {votes_bribes_file}")
    
    print("\n📖 Lendo arquivos...")
    
    # Ler dados
    vebal_df = pd.read_csv(vebal_file)
    votes_bribes_df = pd.read_csv(votes_bribes_file)
    
    print(f"✅ veBAL CSV: {len(vebal_df):,} linhas")
    print(f"   Colunas: {list(vebal_df.columns)}")
    print(f"✅ Votes_Bribes CSV: {len(votes_bribes_df):,} linhas")
    print(f"   Colunas: {list(votes_bribes_df.columns)}")
    
    # Verificar colunas necessárias
    required_vebal_cols = ['block_date', 'project_contract_address', 'gauge_address', 'blockchain']
    missing_vebal = [col for col in required_vebal_cols if col not in vebal_df.columns]
    
    if missing_vebal:
        raise ValueError(f"Colunas faltando no veBAL: {missing_vebal}")
    
    # Verificar se day existe no votes_bribes (pode ser day ou block_date)
    if 'day' not in votes_bribes_df.columns and 'block_date' not in votes_bribes_df.columns:
        raise ValueError("Coluna 'day' ou 'block_date' não encontrada no votes_bribes_merged")
    
    print("\n🧹 Limpando e preparando dados...")
    
    # Remover linhas onde project_contract_address não tem gauge_address
    initial_vebal = len(vebal_df)
    vebal_df = vebal_df[
        vebal_df['gauge_address'].notna() & 
        (vebal_df['gauge_address'] != '') &
        (vebal_df['gauge_address'].astype(str).str.lower() != 'nan')
    ]
    removed = initial_vebal - len(vebal_df)
    if removed > 0:
        print(f"   Removidas {removed:,} linhas sem gauge_address do veBAL")
    
    print(f"✅ veBAL após limpeza: {len(vebal_df):,} linhas")
    
    # Converter datas para datetime
    vebal_df['block_date'] = pd.to_datetime(vebal_df['block_date'], errors='coerce')
    
    # Normalizar coluna de data no votes_bribes
    if 'day' in votes_bribes_df.columns:
        votes_bribes_df['day'] = pd.to_datetime(votes_bribes_df['day'], errors='coerce')
        date_col_bribes = 'day'
    else:
        votes_bribes_df['block_date'] = pd.to_datetime(votes_bribes_df['block_date'], errors='coerce')
        date_col_bribes = 'block_date'
    
    # Normalizar gauge_address e blockchain (lowercase, remover espaços)
    vebal_df['gauge_address'] = vebal_df['gauge_address'].astype(str).str.lower().str.strip()
    vebal_df['blockchain'] = vebal_df['blockchain'].astype(str).str.lower().str.strip()
    
    votes_bribes_df['gauge_address'] = votes_bribes_df['gauge_address'].astype(str).str.lower().str.strip()
    if 'blockchain' in votes_bribes_df.columns:
        votes_bribes_df['blockchain'] = votes_bribes_df['blockchain'].astype(str).str.lower().str.strip()
    
    # Remover linhas com valores inválidos nas chaves de match
    initial_votes_bribes = len(votes_bribes_df)
    votes_bribes_df = votes_bribes_df[
        votes_bribes_df['gauge_address'].notna() & 
        (votes_bribes_df['gauge_address'] != '') &
        (votes_bribes_df['gauge_address'].astype(str).str.lower() != 'nan') &
        votes_bribes_df[date_col_bribes].notna()
    ]
    if len(votes_bribes_df) < initial_votes_bribes:
        print(f"   Removidas {initial_votes_bribes - len(votes_bribes_df):,} linhas inválidas do votes_bribes_merged")
    
    print(f"✅ Votes_Bribes após limpeza: {len(votes_bribes_df):,} linhas")
    
    # Renomear coluna de data no votes_bribes para block_date se necessário
    if date_col_bribes == 'day':
        votes_bribes_df = votes_bribes_df.rename(columns={'day': 'block_date'})
    
    # Fazer merge
    print("\n🔗 Fazendo merge dos dados...")
    print("   Chaves de match: gauge_address, block_date, blockchain")
    
    # Merge com left join (manter todas as linhas do veBAL)
    merged_df = pd.merge(
        vebal_df,
        votes_bribes_df,
        on=['gauge_address', 'block_date', 'blockchain'],
        how='left',
        suffixes=('', '_votes_bribes')
    )
    
    print(f"✅ Merge concluído: {len(merged_df):,} linhas")
    
    # Estatísticas do merge
    matched_count = merged_df['bal_emited_votes'].notna().sum() if 'bal_emited_votes' in merged_df.columns else 0
    unmatched_count = len(merged_df) - matched_count
    
    print(f"\n📊 Estatísticas do merge:")
    print(f"   Total de linhas: {len(merged_df):,}")
    print(f"   Linhas com dados de votes/bribes: {matched_count:,} ({100 * matched_count / len(merged_df):.2f}%)")
    print(f"   Linhas sem dados de votes/bribes: {unmatched_count:,} ({100 * unmatched_count / len(merged_df):.2f}%)")
    
    # Preparar colunas finais
    print("\n📋 Preparando colunas finais...")
    
    # Verificar quais colunas existem e criar as que faltam
    final_df = pd.DataFrame()
    
    for col in FINAL_COLUMNS:
        # Tentar encontrar a coluna (pode ter sufixo após merge)
        col_found = None
        if col in merged_df.columns:
            col_found = col
        else:
            # Procurar coluna com sufixo
            for merged_col in merged_df.columns:
                if merged_col.startswith(col) and not merged_col.endswith('_votes_bribes'):
                    col_found = merged_col
                    break
        
        if col_found:
            final_df[col] = merged_df[col_found]
        elif col == 'swap_fee_%':
            # Calcular swap_fee_% se não existir
            swap_fee_col = None
            swap_amount_col = None
            
            # Procurar colunas
            for c in merged_df.columns:
                if 'swap_fee_usd' in c.lower() and not c.endswith('_votes_bribes'):
                    swap_fee_col = c
                if 'swap_amount_usd' in c.lower() and not c.endswith('_votes_bribes'):
                    swap_amount_col = c
            
            if swap_fee_col and swap_amount_col:
                final_df[col] = (merged_df[swap_fee_col] / merged_df[swap_amount_col] * 100).fillna(0)
                print(f"   Calculada: {col} a partir de {swap_fee_col} e {swap_amount_col}")
            else:
                final_df[col] = 0
                print(f"   ⚠️  Não foi possível calcular {col} - colunas não encontradas")
        elif col == 'core_non_core':
            # Esta coluna virá do classification_core_pools.csv (será adicionada depois)
            final_df[col] = None
            print(f"   Criada (vazia): {col} - será preenchida depois")
        else:
            # Coluna não encontrada, criar como None
            final_df[col] = None
            print(f"   ⚠️  Coluna não encontrada: {col} - criada como vazia")
    
    # Remover linhas duplicadas se houver
    initial_count = len(final_df)
    final_df = final_df.drop_duplicates()
    if len(final_df) < initial_count:
        print(f"\n🧹 Removidas {initial_count - len(final_df):,} duplicatas")
    
    # Sort by block_date descending (most recent first), then blockchain, project_contract_address
    final_df = final_df.sort_values(['block_date', 'blockchain', 'project_contract_address'], ascending=[False, True, True], na_position='last')
    
    # Estatísticas finais
    print(f"\n📊 Estatísticas finais:")
    print(f"   Total de linhas: {len(final_df):,}")
    print(f"   Total de colunas: {len(final_df.columns)}")
    print(f"   Pools únicas: {final_df['project_contract_address'].nunique():,}")
    print(f"   Gauge addresses únicos: {final_df['gauge_address'].nunique():,}")
    
    if 'bribe_amount_usd' in final_df.columns:
        total_bribes = final_df['bribe_amount_usd'].sum()
        print(f"   Total de bribes: {total_bribes:,.2f} USD")
    
    if 'bal_emited_votes' in final_df.columns:
        total_emissions = final_df['bal_emited_votes'].sum()
        print(f"   Total de BAL emitido: {total_emissions:,.2f}")
    
    # Salvar resultado
    print(f"\n💾 Salvando resultado em {output_file}...")
    final_df.to_csv(output_file, index=False)
    
    print(f"✅ Arquivo salvo com sucesso!")
    
    # Mostrar amostra dos dados
    print(f"\n📋 Amostra dos dados (primeiras 10 linhas):")
    print(final_df.head(10).to_string(index=False))
    
    # Mostrar informações sobre colunas vazias
    print(f"\n📊 Informações sobre colunas:")
    for col in FINAL_COLUMNS:
        if col in final_df.columns:
            non_null = final_df[col].notna().sum()
            null_count = len(final_df) - non_null
            pct = 100 * non_null / len(final_df) if len(final_df) > 0 else 0
            print(f"   {col}: {non_null:,} valores ({pct:.1f}% preenchido)")
    
    return final_df


def main():
    """Função principal"""
    try:
        result_df = create_final_dataset()
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
