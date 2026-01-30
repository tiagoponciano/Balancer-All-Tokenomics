#!/usr/bin/env python3
"""
Script para combinar dados de bribes do Dune (Bribes.csv) com dados do HiddenHand (hiddenhand_bribes.csv).

O script:
1. Lê ambos os CSVs
2. Faz match por proposal_hash
3. Identifica pools novas do HiddenHand que não estão no Bribes.csv
4. Combina os dados mantendo todas as informações
5. Salva como Bribes.csv atualizado
"""
import pandas as pd
from pathlib import Path
from typing import Optional

# Configurações
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Arquivos de entrada
DUNE_BRIBES_FILE = DATA_DIR / "Bribes.csv"  # Dados do Dune
HIDDENHAND_BRIBES_FILE = DATA_DIR / "hiddenhand_bribes.csv"  # Dados do HiddenHand

# Arquivo de saída (sobrescreve o Bribes.csv original)
OUTPUT_FILE = DATA_DIR / "Bribes.csv"


def merge_bribes_data(
    dune_file: Path = DUNE_BRIBES_FILE,
    hiddenhand_file: Path = HIDDENHAND_BRIBES_FILE,
    output_file: Path = OUTPUT_FILE
) -> pd.DataFrame:
    """
    Combina dados de bribes do Dune e HiddenHand por proposal_hash.
    
    Args:
        dune_file: Caminho para o CSV do Dune
        hiddenhand_file: Caminho para o CSV do HiddenHand
        output_file: Caminho para o arquivo de saída
        
    Returns:
        DataFrame com os dados combinados
    """
    print("=" * 60)
    print("🔄 Merge de Dados de Bribes")
    print("=" * 60)
    
    # Verificar se os arquivos existem
    if not hiddenhand_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {hiddenhand_file}")
    
    print("\n📖 Lendo arquivos...")
    
    # Ler dados do HiddenHand
    hiddenhand_df = pd.read_csv(hiddenhand_file)
    print(f"✅ HiddenHand CSV: {len(hiddenhand_df):,} linhas")
    print(f"   Colunas: {list(hiddenhand_df.columns)}")
    
    # Verificar se proposal_hash existe no HiddenHand
    if 'proposal_hash' not in hiddenhand_df.columns:
        raise ValueError(
            f"Coluna 'proposal_hash' não encontrada no arquivo HiddenHand. "
            f"Colunas disponíveis: {list(hiddenhand_df.columns)}"
        )
    
    # Ler dados do Dune (se existir)
    dune_df = None
    if dune_file.exists():
        dune_df = pd.read_csv(dune_file)
        print(f"✅ Dune CSV: {len(dune_df):,} linhas")
        print(f"   Colunas: {list(dune_df.columns)}")
        
        # Verificar se proposal_hash existe no Dune
        if 'proposal_hash' not in dune_df.columns:
            print(f"⚠️  Coluna 'proposal_hash' não encontrada no arquivo Dune.")
            print(f"   Tentando encontrar coluna similar...")
            
            # Tentar encontrar coluna similar
            proposal_cols = [col for col in dune_df.columns if 'proposal' in col.lower() or 'hash' in col.lower()]
            if proposal_cols:
                print(f"   Colunas encontradas: {proposal_cols}")
                # Usar a primeira coluna encontrada e renomear
                dune_df = dune_df.rename(columns={proposal_cols[0]: 'proposal_hash'})
                print(f"   Coluna '{proposal_cols[0]}' renomeada para 'proposal_hash'")
            else:
                print(f"⚠️  Não foi possível encontrar coluna de proposal_hash no Dune.")
                print(f"   Continuando apenas com dados do HiddenHand...")
                dune_df = None
    else:
        print(f"⚠️  Arquivo Dune não encontrado: {dune_file}")
        print(f"   Continuando apenas com dados do HiddenHand...")
    
    # Limpar proposal_hash vazios
    print("\n🧹 Limpando dados...")
    initial_hiddenhand = len(hiddenhand_df)
    hiddenhand_df = hiddenhand_df[hiddenhand_df['proposal_hash'].notna() & (hiddenhand_df['proposal_hash'] != '')]
    if len(hiddenhand_df) < initial_hiddenhand:
        print(f"   Removidas {initial_hiddenhand - len(hiddenhand_df):,} linhas com proposal_hash vazio do HiddenHand")
    
    if dune_df is not None:
        initial_dune = len(dune_df)
        dune_df = dune_df[dune_df['proposal_hash'].notna() & (dune_df['proposal_hash'] != '')]
        if len(dune_df) < initial_dune:
            print(f"   Removidas {initial_dune - len(dune_df):,} linhas com proposal_hash vazio do Dune")
    
    # Normalizar proposal_hash (lowercase, remover espaços)
    hiddenhand_df['proposal_hash'] = hiddenhand_df['proposal_hash'].astype(str).str.lower().str.strip()
    if dune_df is not None:
        dune_df['proposal_hash'] = dune_df['proposal_hash'].astype(str).str.lower().str.strip()
    
    print(f"\n📊 Estatísticas iniciais:")
    print(f"   HiddenHand: {len(hiddenhand_df):,} registros únicos por proposal_hash")
    unique_hiddenhand = hiddenhand_df['proposal_hash'].nunique()
    print(f"   HiddenHand: {unique_hiddenhand:,} proposal_hashes únicos")
    
    if dune_df is not None:
        print(f"   Dune: {len(dune_df):,} registros únicos por proposal_hash")
        unique_dune = dune_df['proposal_hash'].nunique()
        print(f"   Dune: {unique_dune:,} proposal_hashes únicos")
    
    # Fazer merge dos dados
    print("\n🔗 Fazendo merge dos dados...")
    
    if dune_df is not None:
        # Merge: manter todos os registros de ambos os lados
        # Usar outer join para incluir todos os proposal_hashes
        merged_df = pd.merge(
            hiddenhand_df,
            dune_df,
            on='proposal_hash',
            how='outer',
            suffixes=('_hiddenhand', '_dune'),
            indicator=True
        )
        
        # Identificar origem dos dados
        merged_df['source'] = merged_df['_merge'].map({
            'left_only': 'hiddenhand_only',
            'right_only': 'dune_only',
            'both': 'both'
        })
        merged_df = merged_df.drop(columns=['_merge'])
        
        # Estatísticas do merge
        print(f"\n📊 Resultado do merge:")
        print(f"   Total de registros após merge: {len(merged_df):,}")
        print(f"   Proposal_hashes apenas no HiddenHand: {(merged_df['source'] == 'hiddenhand_only').sum():,}")
        print(f"   Proposal_hashes apenas no Dune: {(merged_df['source'] == 'dune_only').sum():,}")
        print(f"   Proposal_hashes em ambos: {(merged_df['source'] == 'both').sum():,}")
        
        # Identificar pools novas (apenas no HiddenHand)
        new_pools = merged_df[merged_df['source'] == 'hiddenhand_only']
        if len(new_pools) > 0:
            print(f"\n🆕 Pools novas encontradas no HiddenHand: {len(new_pools):,}")
            if 'derived_pool_address' in new_pools.columns:
                unique_new_pools = new_pools['derived_pool_address'].nunique()
                print(f"   Pools únicas (por address): {unique_new_pools:,}")
    else:
        # Se não há dados do Dune, usar apenas HiddenHand
        merged_df = hiddenhand_df.copy()
        merged_df['source'] = 'hiddenhand_only'
        print(f"   Usando apenas dados do HiddenHand: {len(merged_df):,} registros")
    
    # Remover duplicatas (se houver)
    initial_count = len(merged_df)
    merged_df = merged_df.drop_duplicates(subset=['proposal_hash'], keep='first')
    if len(merged_df) < initial_count:
        print(f"\n🧹 Removidas {initial_count - len(merged_df):,} duplicatas")
    
    # Ordenar por data (se houver coluna de data)
    date_cols = [col for col in merged_df.columns if 'date' in col.lower() or 'timestamp' in col.lower() or 'week' in col.lower()]
    if date_cols:
        # Usar a primeira coluna de data encontrada
        sort_col = date_cols[0]
        merged_df = merged_df.sort_values(sort_col, ascending=False, na_position='last')
        print(f"   Ordenado por: {sort_col}")
    else:
        # Ordenar por proposal_hash
        merged_df = merged_df.sort_values('proposal_hash')
        print(f"   Ordenado por: proposal_hash")
    
    # Salvar resultado
    print(f"\n💾 Salvando resultado em {output_file}...")
    merged_df.to_csv(output_file, index=False)
    
    print(f"✅ Arquivo salvo com sucesso!")
    print(f"   Total de registros: {len(merged_df):,}")
    print(f"   Total de colunas: {len(merged_df.columns)}")
    
    # Mostrar amostra dos dados
    print(f"\n📋 Amostra dos dados (primeiras 10 linhas):")
    print(merged_df.head(10).to_string())
    
    # Estatísticas finais
    print(f"\n📊 Estatísticas finais:")
    print(f"   Total de registros: {len(merged_df):,}")
    print(f"   Proposal_hashes únicos: {merged_df['proposal_hash'].nunique():,}")
    
    if 'derived_pool_address' in merged_df.columns:
        print(f"   Pools únicas (por address): {merged_df['derived_pool_address'].nunique():,}")
    
    if 'source' in merged_df.columns:
        print(f"\n   Distribuição por origem:")
        source_counts = merged_df['source'].value_counts()
        for source, count in source_counts.items():
            print(f"     {source}: {count:,} ({100 * count / len(merged_df):.2f}%)")
    
    return merged_df


def main():
    """Função principal"""
    try:
        result_df = merge_bribes_data()
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
