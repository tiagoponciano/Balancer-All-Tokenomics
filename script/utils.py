import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import sys
from dotenv import load_dotenv
import io


def _log(msg: str) -> None:
    """Print and flush so Streamlit Cloud runtime logs show it immediately."""
    print(msg)
    try:
        sys.stdout.flush()
    except Exception:
        pass

# Load environment variables (cwd and project root so Streamlit finds .env)
load_dotenv()
try:
    _script_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.dirname(_script_dir)
    load_dotenv(os.path.join(_project_root, ".env"))
except Exception:
    pass

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # For private buckets
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "data")  # Default bucket name

def get_supabase_client():
    """Initialize and return Supabase client if credentials are available"""
    if not SUPABASE_URL:
        return None
    
    # Prefer service key for private buckets, fallback to anon key
    supabase_key = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
    if not supabase_key:
        return None
    
    try:
        from supabase import create_client, Client  # type: ignore
        supabase: Client = create_client(SUPABASE_URL, supabase_key)
        return supabase
    except ImportError:
        return None
    except Exception:
        return None

def download_csv_from_supabase(filename, return_error=False):
    """Download CSV file from Supabase Storage (supports both public and private buckets)"""
    supabase = get_supabase_client()
    if not supabase:
        if return_error:
            return None, "Supabase client not initialized (missing URL or keys)"
        return None
    
    try:
        # Download file from Supabase Storage
        # For private buckets, service key is required
        # For public buckets, anon key works
        response = supabase.storage.from_(SUPABASE_BUCKET).download(filename)
        if response:
            # Convert bytes to DataFrame
            df = pd.read_csv(io.BytesIO(response))
            if return_error:
                return df, None
            return df
    except Exception as e:
        error_msg = str(e)
        if return_error:
            return None, error_msg
        # Silently fail - will fallback to local filesystem
        pass
    if return_error:
        return None, "File not found in Supabase Storage"
    return None

def load_aggregated_csv(filename):
    """Load aggregated CSV file from Supabase Storage or local filesystem"""
    # First, try to download from Supabase
    df = download_csv_from_supabase(filename)
    if df is not None and not df.empty:
        return df
    
    # Fallback to local filesystem
    cwd = os.getcwd()
    
    # Try different possible file paths (in order of likelihood)
    file_paths = [
        os.path.join(cwd, 'data', filename),  # data/file.csv (when running from root)
        os.path.abspath(os.path.join(cwd, 'data', filename)),  # absolute path from root
        os.path.abspath(os.path.join(cwd, '..', 'data', filename)),  # ../data/file.csv (when running from script/)
        os.path.abspath(os.path.join(cwd, '..', '..', 'data', filename)),  # ../../data/file.csv
        f'data/{filename}',  # relative
        filename  # current dir
    ]
    
    for path in file_paths:
        try:
            abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
            if os.path.exists(abs_path) and os.path.getsize(abs_path) > 0:
                return pd.read_csv(abs_path)
        except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, Exception) as e:
            continue
    
    return None

# Prevent this file from being rendered as a Streamlit page
# This is a utility module, not a page - it should only be imported
# Check if this is being run as a page (has page config or is being accessed directly)
try:
    # If this file is accessed as a page, show a message and stop
    if hasattr(st, '_is_running_with_streamlit') and st._is_running_with_streamlit:
        # Check if we're in the main execution context (not imported)
        import inspect
        frame = inspect.currentframe()
        # If called directly (not imported), show message
        if frame and frame.f_back and 'streamlit' in str(frame.f_back.f_code.co_filename):
            st.info("ℹ️ **utils.py** is a utility module, not a page.\n\nPlease use the pages from the sidebar menu: Home, Bribes Analysis, Pool Classification, etc.")
            st.stop()
except:
    pass

def inject_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* --- ESTRUTURA GERAL --- */
        .stApp {
            background: linear-gradient(135deg, #0F1419 0%, #1A1F26 100%);
            font-family: 'Inter', sans-serif;
        }
        
        .block-container {
            padding-top: 3rem;
            padding-bottom: 2rem;
            max-width: 1400px;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            letter-spacing: -0.02em;
            color: #FFFFFF;
        }
        
        .page-title {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, #67A2E1 0%, #B1ACF1 50%, #E9A97B 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            letter-spacing: -0.03em;
            position: relative;
            display: inline-block;
        }
        
        .page-title::before {
            content: '';
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            width: 800px;
            height: 800px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.02) 30%, transparent 60%);
            border-radius: 50%;
            filter: blur(80px);
            mix-blend-mode: overlay;
            pointer-events: none;
            z-index: -1;
        }
        
        .page-subtitle {
            font-size: 1rem;
            color: #8B95A6;
            font-weight: 400;
            margin-bottom: 2rem;
        }
        
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1A1F26 0%, #151A20 100%);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
        }
        
        div[data-testid="metric-container"] {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
            padding: 1.5rem;
            backdrop-filter: blur(10px);
        }
        
        div[data-testid="metric-container"] label {
            color: #8B95A6 !important;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
            color: #FFFFFF !important;
            font-size: 1.75rem;
            font-weight: 700;
        }
        
        div[data-testid="metric-container"] div[data-testid="stMetricDelta"] {
            font-weight: 500;
        }
        
        .stSlider {
            position: relative;
        }
        
        .stSlider::before {
            content: '';
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            width: 800px;
            height: 800px;
            background: radial-gradient(circle, rgba(255, 255, 255, 0.04) 0%, rgba(255, 255, 255, 0.02) 30%, transparent 60%);
            border-radius: 50%;
            filter: blur(80px);
            mix-blend-mode: overlay;
            pointer-events: none;
            z-index: -1;
        }
        
        .stSlider > div > div > div[role="slider"] {
            background-color: #67A2E1 !important;
        }
        
        .stSlider > div > div > div > div {
            background-color: #FF4B4B !important;
        }
        
        hr {
            border: none;
            height: 1px;
            background: linear-gradient(90deg, transparent 0%, rgba(255, 255, 255, 0.1) 50%, transparent 100%);
            margin: 2rem 0;
        }
        
        section[data-testid="stSidebar"] hr {
            margin: 0.4rem 0 !important;
        }
        /* Saltinho on page change: same entrance animation for Date Filter as sidebar buttons */
        @keyframes sidebarSaltinho {
            0%   { transform: translateY(0) scale(1); }
            40%  { transform: translateY(-2px) scale(1.01); }
            100% { transform: translateY(0) scale(1); }
        }
        /* Date Filter: Year & Quarter — same color/weight as Top 20, keep default font-size */
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(div[data-baseweb="select"]:not(:has(span[role="listbox"] > span))) p,
        section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"]:has(div[data-baseweb="select"]:not(:has(span[role="listbox"] > span))) label {
            font-size: 0.8125rem !important; 
            font-family: inherit !important;
            font-weight: 600 !important;
            color: #8BB5F0 !important;
            letter-spacing: 0.03em !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child,
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) input {
            font-size: 0.8125rem !important;
            font-family: inherit !important;
            font-weight: 600 !important;
            color: #8BB5F0 !important;
            letter-spacing: 0.03em !important;
        }
        
        .stInfo {
            background: rgba(103, 162, 225, 0.1);
            border: 1px solid rgba(103, 162, 225, 0.2);
            border-radius: 8px;
        }
        
        .stCaption {
            color: #6B7280;
            font-size: 0.8125rem;
        }
        
        /* --- BOTÕES PADRÃO (fallback para outros botões) --- */
        /* Exclui explicitamente os botões com IDs específicos (genéricos e específicos) */
        .stButton > button:not([id^="btn_top20"]):not([id^="btn_worst20"]):not([id^="btn_select_all"]):not(#btn_performance_by_pool):not([id^="btn_login"]):not([id^="btn_logout"]):not(.logout-button):not([key="logout_btn"]):not([key="login_btn"]) {
            width: 110px;
            background-color: rgba(103, 162, 225, 0.1);
            border: 1px solid rgba(103, 162, 225, 0.3);
            color: #67A2E1;
            font-weight: 500;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            position: relative;
            overflow: visible;
        }
        
        .stButton > button:not([id^="btn_top20"]):not([id^="btn_worst20"]):not([id^="btn_select_all"]):not(#btn_performance_by_pool):not([id^="btn_login"]):not([id^="btn_logout"]):not(.logout-button):not([key="logout_btn"]):not([key="login_btn"]):hover {
            background-color: rgba(103, 162, 225, 0.2);
            border-color: rgba(103, 162, 225, 0.5);
        }
        
        /* --- BOTÃO TOP 20 (genérico para todas as páginas) --- */
        button[id^="btn_top20"],
        [id^="btn_top20"] {
            width: 110px !important;
            min-width: 110px !important;
            max-width: 110px !important;
            height: 44px !important;
            padding: 0.625rem 0.5rem !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.03em !important;
        }
        
        button[id^="btn_top20"]::before,
        [id^="btn_top20"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button[id^="btn_top20"]::after,
        [id^="btn_top20"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button[id^="btn_top20"]:hover,
        [id^="btn_top20"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button[id^="btn_top20"]:hover::before,
        [id^="btn_top20"]:hover::before {
            left: 100% !important;
        }
        
        button[id^="btn_top20"]:hover::after,
        [id^="btn_top20"]:hover::after {
            opacity: 1 !important;
        }
        
        button[id^="btn_top20"]:active,
        [id^="btn_top20"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- BOTÃO WORST 20 (genérico para todas as páginas) --- */
        button[id^="btn_worst20"],
        [id^="btn_worst20"] {
            width: 110px !important;
            min-width: 110px !important;
            max-width: 110px !important;
            height: 44px !important;
            padding: 0.625rem 0.5rem !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.03em !important;
        }
        
        button[id^="btn_worst20"]::before,
        [id^="btn_worst20"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button[id^="btn_worst20"]::after,
        [id^="btn_worst20"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button[id^="btn_worst20"]:hover,
        [id^="btn_worst20"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button[id^="btn_worst20"]:hover::before,
        [id^="btn_worst20"]:hover::before {
            left: 100% !important;
        }
        
        button[id^="btn_worst20"]:hover::after,
        [id^="btn_worst20"]:hover::after {
            opacity: 1 !important;
        }
        
        button[id^="btn_worst20"]:active,
        [id^="btn_worst20"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- BOTÃO SELECT ALL (genérico para todas as páginas) --- */
        button[id^="btn_select_all"],
        [id^="btn_select_all"] {
            width: 110px !important;
            min-width: 110px !important;
            max-width: 110px !important;
            height: 44px !important;
            padding: 0.625rem 0.5rem !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.03em !important;
        }
        
        button[id^="btn_select_all"]::before,
        [id^="btn_select_all"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button[id^="btn_select_all"]::after,
        [id^="btn_select_all"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button[id^="btn_select_all"]:hover,
        [id^="btn_select_all"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button[id^="btn_select_all"]:hover::before,
        [id^="btn_select_all"]:hover::before {
            left: 100% !important;
        }
        
        button[id^="btn_select_all"]:hover::after,
        [id^="btn_select_all"]:hover::after {
            opacity: 1 !important;
        }
        
        button[id^="btn_select_all"]:active,
        [id^="btn_select_all"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- BOTÕES DE VERSÃO (V2, V3, All Versions) --- */
        button[id^="btn_v2_"],
        button[id^="btn_v3_"],
        button[id^="btn_all_versions_"],
        [id^="btn_v2_"],
        [id^="btn_v3_"],
        [id^="btn_all_versions_"] {
            width: 110px !important;
            min-width: 110px !important;
            max-width: 110px !important;
            height: 44px !important;
            padding: 0.625rem 0.5rem !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.03em !important;
        }
        
        button[id^="btn_v2_"]::before,
        button[id^="btn_v3_"]::before,
        button[id^="btn_all_versions_"]::before,
        [id^="btn_v2_"]::before,
        [id^="btn_v3_"]::before,
        [id^="btn_all_versions_"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button[id^="btn_v2_"]::after,
        button[id^="btn_v3_"]::after,
        button[id^="btn_all_versions_"]::after,
        [id^="btn_v2_"]::after,
        [id^="btn_v3_"]::after,
        [id^="btn_all_versions_"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button[id^="btn_v2_"]:hover,
        button[id^="btn_v3_"]:hover,
        button[id^="btn_all_versions_"]:hover,
        [id^="btn_v2_"]:hover,
        [id^="btn_v3_"]:hover,
        [id^="btn_all_versions_"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button[id^="btn_v2_"]:hover::before,
        button[id^="btn_v3_"]:hover::before,
        button[id^="btn_all_versions_"]:hover::before,
        [id^="btn_v2_"]:hover::before,
        [id^="btn_v3_"]:hover::before,
        [id^="btn_all_versions_"]:hover::before {
            left: 100% !important;
        }
        
        button[id^="btn_v2_"]:hover::after,
        button[id^="btn_v3_"]:hover::after,
        button[id^="btn_all_versions_"]:hover::after,
        [id^="btn_v2_"]:hover::after,
        [id^="btn_v3_"]:hover::after,
        [id^="btn_all_versions_"]:hover::after {
            opacity: 1 !important;
        }
        
        button[id^="btn_v2_"]:active,
        button[id^="btn_v3_"]:active,
        button[id^="btn_all_versions_"]:active,
        [id^="btn_v2_"]:active,
        [id^="btn_v3_"]:active,
        [id^="btn_all_versions_"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- BOTÕES DE GAUGE (Gauge, No Gauge, Select All) --- */
        button[id^="btn_gauge_"],
        button[id^="btn_no_gauge_"],
        button[id^="btn_all_gauge_"],
        [id^="btn_gauge_"],
        [id^="btn_no_gauge_"],
        [id^="btn_all_gauge_"] {
            width: 110px !important;
            min-width: 110px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            position: relative !important;
            overflow: hidden !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            animation: sidebarSaltinho 0.35s ease-out both !important;
        }
        
        button[id^="btn_gauge_"]::before,
        button[id^="btn_no_gauge_"]::before,
        button[id^="btn_all_gauge_"]::before,
        [id^="btn_gauge_"]::before,
        [id^="btn_no_gauge_"]::before,
        [id^="btn_all_gauge_"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
            pointer-events: none !important;
            z-index: 1 !important;
        }
        
        button[id^="btn_gauge_"]::after,
        button[id^="btn_no_gauge_"]::after,
        button[id^="btn_all_gauge_"]::after,
        [id^="btn_gauge_"]::after,
        [id^="btn_no_gauge_"]::after,
        [id^="btn_all_gauge_"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
            pointer-events: none !important;
            z-index: 0 !important;
        }
        
        button[id^="btn_gauge_"]:hover,
        button[id^="btn_no_gauge_"]:hover,
        button[id^="btn_all_gauge_"]:hover,
        [id^="btn_gauge_"]:hover,
        [id^="btn_no_gauge_"]:hover,
        [id^="btn_all_gauge_"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
        }
        
        button[id^="btn_gauge_"]:hover::before,
        button[id^="btn_no_gauge_"]:hover::before,
        button[id^="btn_all_gauge_"]:hover::before,
        [id^="btn_gauge_"]:hover::before,
        [id^="btn_no_gauge_"]:hover::before,
        [id^="btn_all_gauge_"]:hover::before {
            left: 100% !important;
        }
        
        button[id^="btn_gauge_"]:hover::after,
        button[id^="btn_no_gauge_"]:hover::after,
        button[id^="btn_all_gauge_"]:hover::after,
        [id^="btn_gauge_"]:hover::after,
        [id^="btn_no_gauge_"]:hover::after,
        [id^="btn_all_gauge_"]:hover::after {
            opacity: 1 !important;
        }
        
        button[id^="btn_gauge_"]:active,
        button[id^="btn_no_gauge_"]:active,
        button[id^="btn_all_gauge_"]:active,
        [id^="btn_gauge_"]:active,
        [id^="btn_no_gauge_"]:active,
        [id^="btn_all_gauge_"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- BOTÃO SHOW PERFORMANCE BY POOL --- */
        /* Seletor usando atributo data customizado (mais confiável) */
        button[data-button-type="performance"],
        button[data-testid="stBaseButton-secondary"][data-button-type="performance"] {
            width: 250px !important;
            max-width: 250px !important;
            min-width: 250px !important;
            height: 56px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.02em !important;
        }
        
        /* Classe de fallback aplicada via JavaScript */
        button.performance-button-fallback,
        button[data-testid="stBaseButton-secondary"].performance-button-fallback,
        button[data-testid="stBaseButton-primary"].performance-button-fallback {
            width: 250px !important;
            max-width: 250px !important;
            min-width: 250px !important;
            height: 56px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.02em !important;
        }
        
        /* Múltiplos seletores com alta especificidade para garantir prioridade */
        /* Ordem: do mais específico ao menos específico */
        button[data-testid="stBaseButton-secondary"]#btn_performance_by_pool,
        button[data-testid="stBaseButton-primary"]#btn_performance_by_pool,
        button[data-testid*="stBaseButton"]#btn_performance_by_pool,
        .stButton > button#btn_performance_by_pool,
        div[data-testid="stButton"] > button#btn_performance_by_pool,
        button#btn_performance_by_pool,
        #btn_performance_by_pool {
            /* width precisa de !important porque pode ser sobrescrito por estilos inline do Streamlit */
            width: 250px !important;
            max-width: 250px !important;
            min-width: 250px !important;
            height: 56px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.02em !important;
        }
        
        /* Pseudo-elements para o botão de performance (atributo data) */
        button[data-button-type="performance"]::before,
        button[data-testid="stBaseButton-secondary"][data-button-type="performance"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button[data-button-type="performance"]::after,
        button[data-testid="stBaseButton-secondary"][data-button-type="performance"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button[data-button-type="performance"]:hover,
        button[data-testid="stBaseButton-secondary"][data-button-type="performance"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button[data-button-type="performance"]:hover::before,
        button[data-testid="stBaseButton-secondary"][data-button-type="performance"]:hover::before {
            left: 100% !important;
        }
        
        button[data-button-type="performance"]:hover::after,
        button[data-testid="stBaseButton-secondary"][data-button-type="performance"]:hover::after {
            opacity: 1 !important;
        }
        
        button[data-button-type="performance"]:active,
        button[data-testid="stBaseButton-secondary"][data-button-type="performance"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* Pseudo-elements para o botão de performance (classe de fallback) */
        button.performance-button-fallback::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button.performance-button-fallback::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button.performance-button-fallback:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button.performance-button-fallback:hover::before {
            left: 100% !important;
        }
        
        button.performance-button-fallback:hover::after {
            opacity: 1 !important;
        }
        
        button.performance-button-fallback:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* Pseudo-elements para o botão de performance (ID) */
        #btn_performance_by_pool::before,
        button#btn_performance_by_pool::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        #btn_performance_by_pool::after,
        button#btn_performance_by_pool::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        #btn_performance_by_pool:hover,
        button#btn_performance_by_pool:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        #btn_performance_by_pool:hover::before,
        button#btn_performance_by_pool:hover::before {
            left: 100% !important;
        }
        
        #btn_performance_by_pool:hover::after,
        button#btn_performance_by_pool:hover::after {
            opacity: 1 !important;
        }
        
        #btn_performance_by_pool:active,
        button#btn_performance_by_pool:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* Seletor adicional com máxima especificidade para garantir que o botão de performance nunca receba o estilo padrão */
        button[data-testid="stBaseButton-secondary"]#btn_performance_by_pool.st-emotion-cache-1anq8dj,
        button[data-testid="stBaseButton-primary"]#btn_performance_by_pool.st-emotion-cache-1anq8dj,
        button[data-testid*="stBaseButton"]#btn_performance_by_pool[class*="st-emotion"] {
            width: 250px !important;
            min-width: 250px !important;
            max-width: 250px !important;
            height: 56px !important;
        }

        /* --- BOTÃO LOGIN --- */
        button[id^="btn_login"],
        [id^="btn_login"],
        button[key="login_btn"],
        form button[type="submit"] {
            width: 110px !important;
            min-width: 110px !important;
            max-width: 110px !important;
            height: 44px !important;
            padding: 0.625rem 0.5rem !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.03em !important;
        }
        
        button[id^="btn_login"]::before,
        [id^="btn_login"]::before,
        button[key="login_btn"]::before,
        form button[type="submit"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button[id^="btn_login"]::after,
        [id^="btn_login"]::after,
        button[key="login_btn"]::after,
        form button[type="submit"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button[id^="btn_login"]:hover,
        [id^="btn_login"]:hover,
        button[key="login_btn"]:hover,
        form button[type="submit"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button[id^="btn_login"]:hover::before,
        [id^="btn_login"]:hover::before,
        button[key="login_btn"]:hover::before,
        form button[type="submit"]:hover::before {
            left: 100% !important;
        }
        
        button[id^="btn_login"]:hover::after,
        [id^="btn_login"]:hover::after,
        button[key="login_btn"]:hover::after,
        form button[type="submit"]:hover::after {
            opacity: 1 !important;
        }
        
        button[id^="btn_login"]:active,
        [id^="btn_login"]:active,
        button[key="login_btn"]:active,
        form button[type="submit"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- BOTÃO LOGOUT --- */
        button[id^="btn_logout"],
        [id^="btn_logout"],
        button[key="logout_btn"] {
            width: 110px !important;
            min-width: 110px !important;
            max-width: 110px !important;
            height: 44px !important;
            padding: 0.625rem 0.5rem !important;
            font-size: 0.8125rem !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            color: #8BB5F0 !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            position: relative !important;
            overflow: hidden !important;
            letter-spacing: 0.03em !important;
        }
        
        button[id^="btn_logout"]::before,
        [id^="btn_logout"]::before,
        button[key="logout_btn"]::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
        }
        
        button[id^="btn_logout"]::after,
        [id^="btn_logout"]::after,
        button[key="logout_btn"]::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
        }
        
        button[id^="btn_logout"]:hover,
        [id^="btn_logout"]:hover,
        button[key="logout_btn"]:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
            color: #A8C8F5 !important;
        }
        
        button[id^="btn_logout"]:hover::before,
        [id^="btn_logout"]:hover::before,
        button[key="logout_btn"]:hover::before {
            left: 100% !important;
        }
        
        button[id^="btn_logout"]:hover::after,
        [id^="btn_logout"]:hover::after,
        button[key="logout_btn"]:hover::after {
            opacity: 1 !important;
        }
        
        button[id^="btn_logout"]:active,
        [id^="btn_logout"]:active,
        button[key="logout_btn"]:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- SELECT / DROPDOWN STYLING (BASEWEB) — same glow and animation as other filters --- */
        div[data-baseweb="select"] {
            position: relative;
        }
        
        /* Main select container: glow and transition */
        div[data-baseweb="select"] > div:first-child {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.12) 0%, rgba(103, 162, 225, 0.06) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.35) !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            min-height: 40px !important;
            max-height: 120px !important;
            font-size: 1rem !important;
            font-weight: 500 !important;
            color: white !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            display: flex !important;
            align-items: flex-start !important;
            justify-content: flex-start !important;
            gap: 0.5rem !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
        }
        
        div[data-baseweb="select"] > div:first-child:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.2) 0%, rgba(103, 162, 225, 0.1) 100%) !important;
            border-color: rgba(103, 162, 225, 0.55) !important;
            box-shadow: 0 4px 16px rgba(103, 162, 225, 0.25) !important;
            transform: translateY(-1px) !important;
        }
        
        div[data-baseweb="select"] > div:first-child:focus,
        div[data-baseweb="select"] > div:first-child:focus-within {
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(103, 162, 225, 0.35), 0 4px 16px rgba(103, 162, 225, 0.2) !important;
        }
        
        /* --- SIDEBAR DATE FILTER (Year/Quarter): same brightness & animation as Pool Selection (Top 20) --- */
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%) !important;
            border: 1.5px solid rgba(103, 162, 225, 0.45) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.15) !important;
            border-radius: 12px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            position: relative !important;
            overflow: hidden !important;
            display: flex !important;
            align-items: center !important;
            cursor: pointer !important;
            animation: sidebarSaltinho 0.35s ease-out both !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child::before {
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: -100% !important;
            width: 100% !important;
            height: 100% !important;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent) !important;
            transition: left 0.6s ease !important;
            pointer-events: none !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child::after {
            content: '' !important;
            position: absolute !important;
            inset: 0 !important;
            border-radius: 12px !important;
            padding: 1.5px !important;
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.6), rgba(103, 162, 225, 0.2)) !important;
            -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0) !important;
            -webkit-mask-composite: xor !important;
            mask-composite: exclude !important;
            opacity: 0 !important;
            transition: opacity 0.3s !important;
            pointer-events: none !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child:hover {
            background: linear-gradient(135deg, rgba(103, 162, 225, 0.28) 0%, rgba(103, 162, 225, 0.15) 100%) !important;
            border-color: rgba(103, 162, 225, 0.7) !important;
            transform: translateY(-3px) scale(1.02) !important;
            box-shadow: 0 6px 20px rgba(103, 162, 225, 0.3) !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child:hover::before {
            left: 100% !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child:hover::after {
            opacity: 1 !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child:focus,
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child:focus-within {
            box-shadow: 0 0 0 3px rgba(103, 162, 225, 0.35), 0 6px 20px rgba(103, 162, 225, 0.3) !important;
        }
        /* Date Filter: same "pulo" (active) as Pool Selection when clicking */
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child:active {
            transform: translateY(-1px) scale(1.01) !important;
            box-shadow: 0 3px 12px rgba(103, 162, 225, 0.2) !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"]:not(:has(span[role="listbox"] > span)) > div:first-child > div:first-child {
            flex: 1 !important;
            min-width: 0 !important;
            text-align: center !important;
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
        }
        /* Prevent typing in sidebar selectbox: input is display-only; pointer on whole dropdown */
        section[data-testid="stSidebar"] div[data-baseweb="select"] > div:first-child {
            cursor: pointer !important;
        }
        section[data-testid="stSidebar"] div[data-baseweb="select"] input {
            caret-color: transparent !important;
            cursor: pointer !important;
        }
        
        /* Selected values display - scrollable container */
        div[data-baseweb="select"] span[role="listbox"] {
            display: flex !important;
            flex-wrap: wrap !important;
            gap: 0.25rem !important;
            width: 100% !important;
            align-items: flex-start !important;
        }
        
        /* Custom scrollbar for multiselect */
        div[data-baseweb="select"] > div:first-child::-webkit-scrollbar { width: 6px !important; }
        div[data-baseweb="select"] > div:first-child::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.1) !important; border-radius: 3px !important;
        }
        div[data-baseweb="select"] > div:first-child::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.3) !important; border-radius: 3px !important;
        }
        div[data-baseweb="select"] > div:first-child::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.5) !important;
        }
        
        /* Multiselect tags/chips */
        div[data-baseweb="select"] span[role="listbox"] > span,
        div[data-baseweb="select"] span[role="listbox"] > div {
            background-color: #B1ACF1 !important;
            color: white !important;
            border-radius: 9999px !important;
            padding: 0.25rem 0.75rem !important;
            font-size: 0.875rem !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
            margin: 0.125rem !important;
        }
        
        /* Placeholder text */
        div[data-baseweb="select"] div[data-baseweb="select"] > div > div[data-baseweb="select"] {
            color: rgba(255, 255, 255, 0.7) !important;
        }
        
        /* Input text color */
        div[data-baseweb="select"] input,
        div[data-baseweb="select"] div[data-baseweb="select"] input {
            color: white !important;
        }
        
        /* Multiselect dropdown */
        ul[role="listbox"],
        div[data-baseweb="popover"] {
            background-color: #1A1F26 !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 8px !important;
            padding: 0.5rem !important;
        }
        
        ul[role="listbox"] li, div[data-baseweb="popover"] li {
            color: white !important;
            padding: 0.5rem 0.75rem !important;
            border-radius: 4px !important;
        }
        
        ul[role="listbox"] li:hover, div[data-baseweb="popover"] li:hover {
            background-color: rgba(103, 162, 225, 0.1) !important;
        }
        
        ul[role="listbox"] li[aria-selected="true"], div[data-baseweb="popover"] li[aria-selected="true"] {
            background-color: rgba(103, 162, 225, 0.2) !important;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
    <script>
        console.log('[Button IDs] Script do utils.py carregado!');
        
        // Script de fallback para aplicar classe ao botão de performance
        (function() {
            function applyPerformanceButtonClass() {
                const contexts = [
                    document,
                    window.parent?.document || document,
                    window.top?.document || document
                ];
                
                contexts.forEach((doc, ctxIndex) => {
                    if (!doc) return;
                    
                    const buttons = doc.querySelectorAll('button[data-testid*="stBaseButton"]');
                    
                    buttons.forEach((button, index) => {
                        // Tenta pegar o texto de múltiplas formas
                        let text = '';
                        try {
                            text = (button.textContent || button.innerText || '').trim();
                            if (!text || text.length === 0) {
                                const markdownEl = button.querySelector('[data-testid="stMarkdownContainer"]');
                                if (markdownEl) {
                                    text = (markdownEl.textContent || markdownEl.innerText || '').trim();
                                }
                            }
                            if (!text || text.length === 0) {
                                const pEl = button.querySelector('p');
                                if (pEl) {
                                    text = (pEl.textContent || pEl.innerText || '').trim();
                                }
                            }
                        } catch(e) {}
                        
                        const textLower = text.toLowerCase();
                        
                        // Detecta botões "Top 20", "Worst 20" e "Select All" em todas as páginas
                        // Aplica IDs que começam com os prefixos corretos para que o CSS funcione
                        if (text === 'Top 20' || textLower === 'top 20') {
                            // Garante que o ID comece com btn_top20
                            if (!button.id || !button.id.startsWith('btn_top20')) {
                                button.id = 'btn_top20';
                            }
                        } else if (text === 'Worst 20' || textLower === 'worst 20') {
                            if (!button.id || !button.id.startsWith('btn_worst20')) {
                                button.id = 'btn_worst20';
                            }
                        } else if (text === 'Select All' || textLower === 'select all') {
                            if (!button.id || !button.id.startsWith('btn_select_all')) {
                                button.id = 'btn_select_all';
                            }
                        } else if (text === 'Login' || textLower === 'login') {
                            // Botão de login
                            if (!button.id || !button.id.startsWith('btn_login')) {
                                button.id = 'btn_login';
                            }
                        } else if (text.includes('Logout') || text.includes('🚪') || textLower.includes('logout')) {
                            // Botão de logout
                            if (!button.id || !button.id.startsWith('btn_logout')) {
                                button.id = 'btn_logout';
                            }
                        } else if (text.includes('Show Performance') || text.includes('Performance by Pool') || textLower.includes('performance') || text.includes('🔍')) {
                            // Aplica ID se ainda não tiver
                            if (!button.id || button.id !== 'btn_performance_by_pool') {
                                button.id = 'btn_performance_by_pool';
                            }
                            // Aplica atributo data customizado
                            button.setAttribute('data-button-type', 'performance');
                            // Aplica classe de fallback
                            button.classList.add('performance-button-fallback');
                            
                            // Aplica TODOS os estilos inline diretamente (máxima prioridade)
                            const styles = {
                                'width': '250px',
                                'min-width': '250px',
                                'max-width': '250px',
                                'height': '56px',
                                'padding': '0.625rem 1.5rem',
                                'font-weight': '600',
                                'background': 'linear-gradient(135deg, rgba(103, 162, 225, 0.18) 0%, rgba(103, 162, 225, 0.08) 100%)',
                                'border': '1.5px solid rgba(103, 162, 225, 0.45)',
                                'color': '#8BB5F0',
                                'border-radius': '12px',
                                'transition': 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                'box-shadow': '0 3px 12px rgba(103, 162, 225, 0.15)',
                                'position': 'relative',
                                'overflow': 'hidden',
                                'letter-spacing': '0.02em'
                            };
                            
                            Object.keys(styles).forEach(prop => {
                                button.style.setProperty(prop, styles[prop], 'important');
                            });
                            
                            console.log('[Button IDs] ✅ Botão performance estilizado via utils.py');
                        }
                    });
                });
            }
            
            // Sidebar selectbox: prevent typing (readonly), keep dropdown click working
            function makeSidebarSelectReadOnly() {
                const contexts = [document, window.parent?.document || document, window.top?.document || document];
                contexts.forEach(doc => {
                    if (!doc) return;
                    const sidebar = doc.querySelector('section[data-testid="stSidebar"]');
                    if (!sidebar) return;
                    sidebar.querySelectorAll('div[data-baseweb="select"] input').forEach(input => {
                        if (!input.readOnly) {
                            input.readOnly = true;
                            input.setAttribute('readonly', 'readonly');
                        }
                    });
                });
            }
            
            // Executa imediatamente
            applyPerformanceButtonClass();
            makeSidebarSelectReadOnly();
            
            // Executa após delays
            setTimeout(applyPerformanceButtonClass, 100);
            setTimeout(applyPerformanceButtonClass, 300);
            setTimeout(applyPerformanceButtonClass, 500);
            setTimeout(applyPerformanceButtonClass, 1000);
            setTimeout(makeSidebarSelectReadOnly, 200);
            setTimeout(makeSidebarSelectReadOnly, 600);
            
            // Executa repetidamente
            setInterval(applyPerformanceButtonClass, 2000);
            setInterval(makeSidebarSelectReadOnly, 1500);
            
            // Observa mudanças no DOM
            if (window.MutationObserver) {
                const observer = new MutationObserver(() => {
                    setTimeout(applyPerformanceButtonClass, 50);
                    setTimeout(makeSidebarSelectReadOnly, 50);
                });
                
                const contexts = [
                    document,
                    window.parent?.document || document,
                    window.top?.document || document
                ];
                
                contexts.forEach(doc => {
                    if (doc && doc.body) {
                        observer.observe(doc.body, { childList: true, subtree: true });
                    }
                });
            }
        })();
    </script>
    """, unsafe_allow_html=True)

def check_authentication():
    """Check if user is authenticated, show login page if not"""
    # Credentials from environment variables (required)
    CORRECT_USERNAME = os.getenv("LOGIN_USERNAME")
    CORRECT_PASSWORD = os.getenv("LOGIN_PASSWORD")
    
    # Validate that credentials are set
    if not CORRECT_USERNAME or not CORRECT_PASSWORD:
        st.error("Authentication credentials not configured. Please set LOGIN_USERNAME and LOGIN_PASSWORD in your .env file.")
        st.stop()
        return False
    
    # Initialize authentication state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    # If already authenticated, allow access
    if st.session_state.authenticated:
        return True
    
    # Show login page
    st.markdown("""
    <style>
        .login-title {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #67A2E1 0%, #B1ACF1 50%, #E9A97B 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            color: #8B95A6;
            text-align: center;
            margin-bottom: 2rem;
            font-size: 0.9rem;
        }
        .stTextInput > div > div > input {
            background-color: rgba(26, 31, 38, 0.6) !important;
            border: 1px solid rgba(103, 162, 225, 0.3) !important;
            color: white !important;
            border-radius: 8px !important;
        }
        .stTextInput > div > div > input:focus {
            border-color: #67A2E1 !important;
            box-shadow: 0 0 0 3px rgba(103, 162, 225, 0.2) !important;
        }
        /* CSS do botão de login já está no inject_css() */
        /* Mantém apenas estilos específicos para outros botões na página de login se necessário */
    </style>
    """, unsafe_allow_html=True)
    
    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-title">🔐 Authentication Required</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Please enter your credentials to access the dashboard</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username", key="login_username")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            
            submitted = st.form_submit_button("Login", use_container_width=True, key="login_btn")
            
            if submitted:
                if username == CORRECT_USERNAME and password == CORRECT_PASSWORD:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password. Please try again.")
    
    # Hide sidebar and menu when showing login
    st.markdown("""
    <style>
        section[data-testid="stSidebar"] {
            display: none;
        }
        #MainMenu {
            visibility: hidden;
        }
    </style>
    """, unsafe_allow_html=True)
    
    return False

def show_logout_button():
    """Show logout button in top right corner"""
    # Create button (will be positioned in the column passed to this function)
    # CSS já está aplicado no inject_css()
    if st.button("🚪 Logout", key="logout_btn"):
        st.session_state.authenticated = False
        st.rerun()

def show_version_filter(session_key='version_filter', on_change_callback=None):
    """
    Display version filter buttons at the top of the sidebar
    
    Args:
        session_key: Session state key for storing version filter (default: 'version_filter')
        on_change_callback: Optional callback function to call when filter changes
    """
    # Initialize session state
    if session_key not in st.session_state:
        st.session_state[session_key] = 'all'
    
    # Create filter container at the top of sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Select Version")
    
    col_v2, col_v3 = st.sidebar.columns(2)
    
    with col_v2:
        if st.button("V2", key=f"btn_v2_{session_key}", use_container_width=True):
            st.session_state[session_key] = 'v2'
            if on_change_callback:
                on_change_callback()
            st.rerun()
    
    with col_v3:
        if st.button("V3", key=f"btn_v3_{session_key}", use_container_width=True):
            st.session_state[session_key] = 'v3'
            if on_change_callback:
                on_change_callback()
            st.rerun()
    
    # Show "All Versions" button only when a filter is active
    if st.session_state[session_key] in ['v2', 'v3']:
        if st.sidebar.button("Select All", key=f"btn_all_versions_{session_key}", use_container_width=True):
            st.session_state[session_key] = 'all'
            if on_change_callback:
                on_change_callback()
            st.rerun()


def get_balancer_ui_url(blockchain, pool_address, version=None):
    """
    Generate Balancer UI URL for a pool
    
    Args:
        blockchain: Chain name (ethereum, arbitrum, polygon, etc.)
        pool_address: Pool contract address / poolId
        version: Pool version (2 or 3), optional - will auto-detect from address length
        
    Returns:
        URL string to Balancer UI pool page
    """
    if pd.isna(pool_address) or not pool_address or str(pool_address).strip() == '':
        return ''
    
    address = str(pool_address).strip()
    
    # Determine version from address length if not provided
    # V3 pools: 42 characters (0x + 40 hex chars)
    # V2 pools: 66 characters (0x + 64 hex chars - includes pool ID)
    if version is None:
        if len(address) > 42:
            version = 2
        else:
            version = 3
    
    # Convert version to v2/v3 string
    version_str = f"v{version}" if version in [2, 3] else "v2"
    
    # Use blockchain name directly (ethereum, arbitrum, etc.)
    chain = str(blockchain).lower()
    
    return f"https://balancer.fi/pools/{chain}/{version_str}/{address}"


def get_explorer_url(blockchain, address):
    """
    Generate block explorer URL for an address
    
    Args:
        blockchain: Chain name (ethereum, arbitrum, polygon, etc.)
        address: Contract address
        
    Returns:
        URL string to block explorer
    """
    if pd.isna(address) or not address or str(address).strip() == '':
        return ''
    
    # Map blockchain names to explorer URLs
    explorer_map = {
        'ethereum': 'https://etherscan.io/address',
        'arbitrum': 'https://arbiscan.io/address',
        'polygon': 'https://polygonscan.com/address',
        'optimism': 'https://optimistic.etherscan.io/address',
        'avalanche_c': 'https://snowtrace.io/address',
        'avalanche': 'https://snowtrace.io/address',
        'base': 'https://basescan.org/address',
        'gnosis': 'https://gnosisscan.io/address',
        'zkevm': 'https://zkevm.polygonscan.com/address'
    }
    
    explorer_base = explorer_map.get(str(blockchain).lower(), 'https://etherscan.io/address')
    addr = str(address).strip()
    
    return f"{explorer_base}/{addr}"


def apply_version_filter(df, session_key='version_filter'):
    """
    Apply version filter to the dataframe
    
    Args:
        df: DataFrame to filter
        session_key: Session state key for version filter
        
    Returns:
        Filtered DataFrame
    """
    if df.empty or 'version' not in df.columns:
        return df

    if session_key not in st.session_state:
        st.session_state[session_key] = 'all'

    version_filter = st.session_state[session_key]

    if version_filter == 'all':
        return df
    # Coerce to numeric so view data (version as "2"/"3") and full data (2/3) both work
    version_num = pd.to_numeric(df['version'], errors='coerce').fillna(0).astype(int)
    if version_filter == 'v2':
        return df.loc[version_num == 2].copy()
    elif version_filter == 'v3':
        return df.loc[version_num == 3].copy()

    return df


def show_gauge_filter(session_key='gauge_filter', on_change_callback=None):
    """
    Display gauge address filter buttons in the sidebar
    
    Args:
        session_key: Session state key for storing filter mode (default: 'gauge_filter')
        on_change_callback: Optional callback function to call when filter changes
    """
    # Initialize session state
    if session_key not in st.session_state:
        st.session_state[session_key] = 'all'
    
    # Create filter container in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎯 Gauge Filter")
    
    col_btn1, col_btn2 = st.sidebar.columns(2)
    
    with col_btn1:
        if st.button("Gauge", key=f"btn_gauge_{session_key}", use_container_width=True):
            st.session_state[session_key] = 'gauge'
            if on_change_callback:
                on_change_callback()
            st.rerun()
    
    with col_btn2:
        if st.button("No Gauge", key=f"btn_no_gauge_{session_key}", use_container_width=True):
            st.session_state[session_key] = 'no_gauge'
            if on_change_callback:
                on_change_callback()
            st.rerun()
    
    # Show "Select All" button only when a filter is active
    if st.session_state[session_key] in ['gauge', 'no_gauge']:
        if st.sidebar.button("Select All", key=f"btn_all_gauge_{session_key}", use_container_width=True):
            st.session_state[session_key] = 'all'
            if on_change_callback:
                on_change_callback()
            st.rerun()


def apply_gauge_filter(df, session_key='gauge_filter'):
    """
    Apply gauge address filter to the dataframe
    
    Args:
        df: DataFrame to filter
        session_key: Session state key for gauge filter
        
    Returns:
        Filtered DataFrame
    """
    if df.empty or 'gauge_address' not in df.columns:
        return df

    if session_key not in st.session_state:
        st.session_state[session_key] = 'all'

    gauge_filter = st.session_state[session_key]

    if gauge_filter == 'all':
        return df

    has_gauge = (
        df['gauge_address'].notna()
        & (df['gauge_address'].astype(str).str.strip() != '')
        & (df['gauge_address'].astype(str).str.lower() != 'nan')
    )
    # When no rows have gauge (e.g. view data: we set gauge_address to ""), don't empty the table
    if has_gauge.sum() == 0:
        return df

    if gauge_filter == 'gauge':
        return df.loc[has_gauge].copy()
    elif gauge_filter == 'no_gauge':
        return df.loc[~has_gauge].copy()

    return df


def show_pool_filters(session_key='pool_filter_mode', on_change_callback=None):
    """
    Display pool filter buttons at the top of the sidebar
    
    Args:
        session_key: Session state key for storing filter mode (default: 'pool_filter_mode')
        on_change_callback: Optional callback function to call when filter changes
    """
    # Initialize session state
    if session_key not in st.session_state:
        st.session_state[session_key] = 'all'
    
    # Create filter container at the top of sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Pool Selection")
    
    col_btn1, col_btn2 = st.sidebar.columns(2)
    
    with col_btn1:
        if st.button("Top 20", key=f"btn_top20_{session_key}"):
            st.session_state[session_key] = 'top20'
            if on_change_callback:
                on_change_callback()
            st.rerun()
    
    with col_btn2:
        if st.button("Worst 20", key=f"btn_worst20_{session_key}"):
            st.session_state[session_key] = 'worst20'
            if on_change_callback:
                on_change_callback()
            st.rerun()
    
    # Show "Select All" button only when a filter is active
    if st.session_state[session_key] in ['top20', 'worst20']:
        if st.sidebar.button("Select All", key=f"btn_select_all_{session_key}"):
            st.session_state[session_key] = 'all'
            if on_change_callback:
                on_change_callback()
            st.rerun()


# Quarters: 1Q (Jan–Mar), 2Q (Apr–Jun), 3Q (Jul–Sep), 4Q (Oct–Dec)
QUARTER_OPTIONS = [
    ("All", None),
    ("1Q (Jan–Mar)", [1, 2, 3]),
    ("2Q (Apr–Jun)", [4, 5, 6]),
    ("3Q (Jul–Sep)", [7, 8, 9]),
    ("4Q (Oct–Dec)", [10, 11, 12]),
]


def show_date_filter_sidebar(df, key_prefix="date_filter"):
    """
    Date filter in sidebar using streamlit-dynamic-filters with quarter descriptions.
    Returns the filtered dataframe.
    """
    if df is None or df.empty or "block_date" not in df.columns:
        return df
    
    try:
        from streamlit_dynamic_filters import DynamicFilters
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📅 Date Filter")
        
        # Prepare dataframe for filtering - add year and quarter columns with descriptions
        df_filter = df.copy()
        dt = pd.to_datetime(df_filter["block_date"], errors="coerce")
        
        # Filter out rows with invalid dates
        valid_dates_mask = dt.notna()
        df_filter = df_filter[valid_dates_mask].copy()
        dt = dt[valid_dates_mask]
        
        # Add Year column
        df_filter['Year'] = dt.dt.year.fillna(0).astype(int).astype(str)
        
        # Map quarter to descriptive labels
        quarter_map = {
            1: '1Q (Jan-Mar)',
            2: '2Q (Apr-Jun)',
            3: '3Q (Jul-Sep)',
            4: '4Q (Oct-Dec)'
        }
        df_filter['Quarter'] = dt.dt.quarter.fillna(0).astype(int).map(quarter_map).fillna('Unknown')
        
        # Remove any rows with 'Unknown' quarter
        df_filter = df_filter[df_filter['Quarter'] != 'Unknown'].copy()
        
        if df_filter.empty:
            st.sidebar.warning("⚠️ No valid dates found in the data")
            return df
        
        # Create dynamic filters - use unique column names to avoid conflicts
        dynamic_filters = DynamicFilters(
            df_filter, 
            filters=['Year', 'Quarter']
        )
        
        # Display filters in sidebar
        dynamic_filters.display_filters(location='sidebar')
        
        # Get filtered dataframe and remove temporary columns
        filtered_df = dynamic_filters.filter_df()
        filtered_df = filtered_df.drop(columns=['Year', 'Quarter'], errors='ignore')
        
        return filtered_df
        
    except ImportError:
        st.sidebar.warning("⚠️ streamlit-dynamic-filters not installed. Install with: pip install streamlit-dynamic-filters")
        return df
    except Exception as e:
        st.sidebar.error(f"⚠️ Error with dynamic filters: {str(e)}")
        import traceback
        st.sidebar.code(traceback.format_exc())
        return df


def apply_date_filter(df, year, quarter_months):
    """
    Filter df by year and quarter (block_date).
    year: int or None (all). quarter_months: list [1,2,3] or None (all).
    """
    if df is None or df.empty or (year is None and quarter_months is None):
        return df
    df = df.copy()
    dt = pd.to_datetime(df["block_date"], errors="coerce")
    if year is not None:
        df = df.loc[dt.dt.year == year]
    if quarter_months is not None:
        df = df.loc[dt.dt.month.isin(quarter_months)]
    return df


# Primary data source: Balancer-All-Tokenomics.csv (merge of financial + votes). Fallback: balancer_v2_merged / master.
MAIN_DATA_FILENAME = 'Balancer-All-Tokenomics.csv'
BAL_EMISSIONS_FILENAME = 'BAL_Emissions_by_GaugePool.csv'

# NEON/Postgres: table name. Override with env NEON_TABLE (e.g. NEON_TABLE=balancer_data if you \copy into balancer_data).
NEON_TABLE_MAIN = os.getenv("NEON_TABLE", "tokenomics").strip() or "tokenomics"

# Load from materialized views (mv_pool_summary, mv_monthly_series) when we have a DB, unless explicitly disabled.
# Default: use views when DATABASE_URL is set (avoids full-table load on Streamlit Cloud). Set USE_NEON_VIEWS=0 to use full table.
_use_views_env = os.getenv("USE_NEON_VIEWS", "").strip().lower()
if _use_views_env in ("0", "false", "no"):
    USE_NEON_VIEWS = False
elif _use_views_env in ("1", "true", "yes"):
    USE_NEON_VIEWS = True
else:
    USE_NEON_VIEWS = bool(os.getenv("DATABASE_URL", "").strip())


def _load_data_from_neon_views():
    """
    Load from NEON materialized views (mv_pool_summary, mv_monthly_series) so the app
    only fetches pre-aggregated data. Returns a DataFrame with one row per (month, pool);
    block_date is set to first of month. Returns None if views are missing or on error.
    Raises a clear error if USE_NEON_VIEWS is set but views don't exist (caller should handle).
    """
    url = os.getenv("DATABASE_URL")
    if not url or not url.strip():
        _log("[Data load] NEON views: DATABASE_URL not set, skipping")
        return None
    try:
        from sqlalchemy import create_engine
    except ImportError:
        _log("[Data load] NEON views: sqlalchemy not available")
        return None
    views_help = (
        "Create the materialized views in NEON: open your NEON project → SQL Editor, "
        "then run the script in sql/neon_materialized_views.sql (replace 'balancer_data' with your table name if needed)."
    )
    try:
        if "sslmode" not in url:
            url = url.rstrip("/") + ("&" if "?" in url else "?") + "sslmode=require"
        engine = create_engine(url)
        _log("[Data load] NEON views: querying mv_pool_summary...")
        pools = pd.read_sql('SELECT * FROM mv_pool_summary', engine)
        _log("[Data load] NEON views: querying mv_monthly_series...")
        monthly = pd.read_sql('SELECT * FROM mv_monthly_series', engine)
        if pools.empty or monthly.empty:
            raise RuntimeError(
                "Materialized views exist but returned no data. Populate your base table and run "
                "REFRESH MATERIALIZED VIEW mv_pool_summary; REFRESH MATERIALIZED VIEW mv_monthly_series; in NEON. "
                + views_help
            )
        # Merge so we have month + pool + category + metrics (only bring pool-level cols from pools to avoid duplicate column names)
        pool_cols = [c for c in ["pool_symbol", "pool_category", "blockchain", "version", "is_core_pool", "gauge_address"] if c in pools.columns]
        if "pool_symbol" not in pool_cols:
            raise RuntimeError("mv_pool_summary must have column pool_symbol. " + views_help)
        df = monthly.merge(pools[pool_cols], on="pool_symbol", how="left", suffixes=("", "_pool"))
        # After merge, we may have is_core_pool from monthly and is_core_pool_pool from pools; prefer one
        if "is_core_pool_pool" in df.columns:
            df["is_core_pool"] = df["is_core_pool_pool"].fillna(df.get("is_core_pool", 0))
            df = df.drop(columns=["is_core_pool_pool"], errors="ignore")
        if "is_core_pool" not in df.columns:
            df["is_core_pool"] = 0
        # Coerce to 0/1 so simulation mask_core (is_core_pool == 1) and incentives revenue work
        df["is_core_pool"] = pd.to_numeric(df["is_core_pool"], errors="coerce").fillna(0).astype(int).clip(0, 1)
        df["block_date"] = pd.to_datetime(df["year_month"], errors="coerce")
        # Timezone-naive for consistent date filtering (Year/Quarter)
        try:
            if pd.api.types.is_datetime64tz_dtype(df["block_date"]):
                df["block_date"] = df["block_date"].dt.tz_localize(None)
        except Exception:
            pass
        df["direct_incentives"] = pd.to_numeric(df.get("bribe_amount_usd", 0), errors="coerce").fillna(0)
        df["protocol_fee_amount_usd"] = pd.to_numeric(df.get("protocol_fee_amount_usd", 0), errors="coerce").fillna(0)
        df["dao_profit_usd"] = df["protocol_fee_amount_usd"] - df["direct_incentives"]
        df["bal_emited_votes"] = pd.to_numeric(df.get("bal_emited_votes", 0), errors="coerce").fillna(0)
        df["votes_received"] = pd.to_numeric(df.get("votes_received", 0), errors="coerce").fillna(0)
        df["pool_category"] = df["pool_category"].fillna("Undefined")
        df["has_gauge"] = False  # views don't have gauge
        if "core_non_core" not in df.columns:
            df["core_non_core"] = df["is_core_pool"]
        # Simulation expects total_protocol_fee_usd; view rows are per-month so use protocol_fee_amount_usd
        if "total_protocol_fee_usd" not in df.columns and "protocol_fee_amount_usd" in df.columns:
            df["total_protocol_fee_usd"] = df["protocol_fee_amount_usd"]
        # Placeholders so filters and other code don't break (views are pool+month only)
        if "project_contract_address" not in df.columns:
            df["project_contract_address"] = ""
        if "gauge_address" not in df.columns:
            df["gauge_address"] = ""
        if "pool_type" not in df.columns:
            df["pool_type"] = ""
        # Prefer pool-level gauge_address if we have it from merge (gauge_address_pool)
        if "gauge_address_pool" in df.columns:
            ga = df["gauge_address_pool"].fillna(df.get("gauge_address", "")).astype(str).str.strip()
            df["gauge_address"] = ga.where(ga != "", df.get("gauge_address", ""))
            df = df.drop(columns=["gauge_address_pool"], errors="ignore")
        if "gauge_address" not in df.columns:
            df["gauge_address"] = ""
        return df
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Could not load from NEON materialized views (mv_pool_summary, mv_monthly_series). "
            f"Original error: {e}. {views_help}"
        ) from e


def _load_data_from_neon():
    """Load main tokenomics data from NEON (or any Postgres) if DATABASE_URL is set. Returns DataFrame or None."""
    url = os.getenv("DATABASE_URL")
    if not url or not url.strip():
        return None
    table = NEON_TABLE_MAIN
    try:
        from sqlalchemy import create_engine
    except ImportError:
        return None
    try:
        if "sslmode" not in url:
            url = url.rstrip("/") + ("&" if "?" in url else "?") + "sslmode=require"
        engine = create_engine(url)
        _log(f"[Data load] NEON full table: SELECT * FROM \"{table}\" (this can be large)")
        df = pd.read_sql(f'SELECT * FROM "{table}"', engine)
        if df is not None and not df.empty:
            return df
    except Exception:
        pass
    return None


@st.cache_data
def load_bal_emissions_daily(_merge_by_gauge=True):
    """
    Load BAL_Emissions_by_GaugePool.csv and compute daily direct_incentives (round_emissions_usd / duration).
    Uses gauge_address for merge key so Balancer-Tokenomics (votes = gauge) matches. Returns DataFrame with
    columns: blockchain, project_contract_address, block_date, direct_incentives.
    """
    df = load_aggregated_csv(BAL_EMISSIONS_FILENAME)
    if df is None or df.empty:
        return pd.DataFrame()
    for c in ['start_date', 'end_date', 'blockchain', 'round_emissions_usd']:
        if c not in df.columns:
            return pd.DataFrame()
    # Main data (Balancer-Tokenomics) uses project_contract_address from votes = gauge address; merge on gauge_address
    addr_col = 'gauge_address' if 'gauge_address' in df.columns else 'pool_address'
    if addr_col not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df['start_date'] = pd.to_datetime(df['start_date'], errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date'], errors='coerce')
    df['round_emissions_usd'] = pd.to_numeric(df['round_emissions_usd'], errors='coerce').fillna(0)
    df = df.dropna(subset=['start_date', 'end_date', 'blockchain'])
    df = df[df[addr_col].notna() & (df[addr_col].astype(str).str.strip() != '')].copy()
    df['duration_days'] = (df['end_date'] - df['start_date']).dt.days
    df.loc[df['duration_days'] < 1, 'duration_days'] = 1
    df['daily_incentive_usd'] = df['round_emissions_usd'] / df['duration_days']
    df['project_contract_address'] = df[addr_col].astype(str).str.strip().str.lower()
    rows = []
    for _, r in df.iterrows():
        try:
            for d in pd.date_range(r['start_date'], r['end_date'], inclusive='left'):
                rows.append({
                    'blockchain': r['blockchain'],
                    'project_contract_address': r['project_contract_address'],
                    'block_date': d,
                    'direct_incentives': r['daily_incentive_usd'],
                })
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out = out.groupby(['blockchain', 'project_contract_address', 'block_date'], as_index=False)['direct_incentives'].sum()
    return out


def _process_main_data(df):
    """
    Process Balancer-All-Tokenomics.csv for Streamlit: align types, merge direct_incentives from BAL_Emissions,
    compute dao_profit_usd, emissions_roi, then classify_pools. Main data has: blockchain, project,
    version, block_date, project_contract_address, pool_symbol, pool_type, swap_amount_usd, tvl_usd,
    tvl_eth, total_protocol_fee_usd, protocol_fee_amount_usd, swap_fee_usd, yield_fee_usd, swap_fee_percent,
    core_non_core (0/1), bal_emited_votes, votes_received.
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'block_date' in df.columns:
        # Normalize dates: convert to datetime with UTC, then extract date only (YYYY-MM-DD)
        # This handles mixed formats and timezones consistently (same as user did in notebook)
        # Store original info for debugging
        original_non_null = df['block_date'].notna().sum()
        original_dtype = df['block_date'].dtype
        
        # Step 1: Convert to datetime with UTC (exactly as user did in notebook)
        # Using errors='coerce' means invalid dates become NaT
        df['block_date'] = pd.to_datetime(df['block_date'], format='mixed', utc=True, errors='coerce')
        
        # Step 2: Normalize to date only (removes time and timezone, but keeps as datetime)
        # Only process non-NaT values to avoid issues
        mask_valid = df['block_date'].notna()
        if mask_valid.any():
            # Use normalize() instead of .dt.date to keep it as datetime
            # normalize() sets time to 00:00:00 and removes timezone, keeping datetime type
            df.loc[mask_valid, 'block_date'] = pd.to_datetime(df.loc[mask_valid, 'block_date']).dt.normalize()
        
        # Final check
        final_non_null = df['block_date'].notna().sum()
        # Note: If dates were lost, it means some values in CSV couldn't be parsed
        # This is expected if CSV has invalid date formats, but shouldn't happen if all are valid
    numeric_cols = [
        'swap_amount_usd', 'tvl_usd', 'tvl_eth',
        'total_protocol_fee_usd', 'protocol_fee_amount_usd',
        'swap_fee_usd', 'yield_fee_usd', 'swap_fee_percent',
        'bal_emited_votes', 'bal_emited_usd', 'votes_received',
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['is_core_pool'] = pd.to_numeric(df.get('core_non_core', 0), errors='coerce').fillna(0).astype(int)
    # direct_incentives: prefer column from CSV (e.g. from daily_emissions_usd in Balancer-Tokenomics); else use bribe_amount_usd; else merge from BAL_Emissions_by_GaugePool
    has_inc = 'direct_incentives' in df.columns and pd.to_numeric(df['direct_incentives'], errors='coerce').fillna(0).gt(0).any()
    has_bribes = 'bribe_amount_usd' in df.columns and pd.to_numeric(df['bribe_amount_usd'], errors='coerce').fillna(0).gt(0).any()
    
    if has_inc:
        df['direct_incentives'] = pd.to_numeric(df['direct_incentives'], errors='coerce').fillna(0)
    elif has_bribes:
        # Use bribe_amount_usd as direct_incentives (bribes are incentives for votes)
        df['direct_incentives'] = pd.to_numeric(df['bribe_amount_usd'], errors='coerce').fillna(0)
    else:
        df['project_contract_address_norm'] = df['project_contract_address'].astype(str).str.strip().str.lower()
        df_inc = load_bal_emissions_daily()
        if not df_inc.empty:
            df_inc = df_inc.rename(columns={'block_date': '_inc_date'})
            df_inc['project_contract_address_norm'] = df_inc['project_contract_address'].astype(str).str.strip().str.lower()
            df['_date_only'] = pd.to_datetime(df['block_date'], errors='coerce').dt.strftime('%Y-%m-%d')
            df_inc['_date_only'] = pd.to_datetime(df_inc['_inc_date'], errors='coerce').dt.strftime('%Y-%m-%d')
            df = df.merge(
                df_inc[['blockchain', 'project_contract_address_norm', '_date_only', 'direct_incentives']],
                on=['blockchain', 'project_contract_address_norm', '_date_only'],
                how='left',
            )
            df = df.drop(columns=['_date_only', 'project_contract_address_norm'], errors='ignore')
            df['direct_incentives'] = pd.to_numeric(df['direct_incentives'], errors='coerce').fillna(0)
        else:
            df['direct_incentives'] = 0.0
            df = df.drop(columns=['project_contract_address_norm'], errors='ignore')
    rev = df['protocol_fee_amount_usd'] if 'protocol_fee_amount_usd' in df.columns else 0
    inc = df['direct_incentives']
    df['dao_profit_usd'] = rev - inc
    df['emissions_roi'] = np.where(inc > 0, rev / inc, 0.0)
    
    # Add has_gauge column (True if gauge_address exists and is not empty/nan)
    if 'gauge_address' in df.columns:
        df['has_gauge'] = (
            df['gauge_address'].notna() & 
            (df['gauge_address'] != '') &
            (df['gauge_address'].astype(str).str.lower() != 'nan')
        )
    else:
        df['has_gauge'] = False
    
    return classify_pools(df)


def _process_merged_data(df):
    """Process balancer_v2_merged (or master) for Streamlit: align columns, Legitimate/Mercenary via classify_pools."""
    if df is None or df.empty:
        return df
    df = df.copy()
    if 'block_date' in df.columns:
        df['block_date'] = pd.to_datetime(df['block_date'], errors='coerce')
    numeric_cols = [
        'swap_amount_usd', 'tvl_usd', 'tvl_eth',
        'total_protocol_fee_usd', 'protocol_fee_amount_usd',
        'swap_fee_usd', 'yield_fee_usd', 'swap_fee_percent',
        'bal_emited_votes', 'bal_emited_usd', 'votes_received', 'direct_incentives'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Use bribe_amount_usd as direct_incentives if direct_incentives doesn't exist
    if 'direct_incentives' not in df.columns:
        if 'bribe_amount_usd' in df.columns:
            df['direct_incentives'] = pd.to_numeric(df['bribe_amount_usd'], errors='coerce').fillna(0)
        else:
            df['direct_incentives'] = 0.0
    
    if 'core_non_core' in df.columns:
        df['is_core_pool'] = pd.to_numeric(df['core_non_core'], errors='coerce').fillna(0).astype(int)
    else:
        df['is_core_pool'] = 0
    rev = df['protocol_fee_amount_usd'] if 'protocol_fee_amount_usd' in df.columns else 0
    inc = df['direct_incentives']
    df['dao_profit_usd'] = rev - inc
    df['emissions_roi'] = np.where(inc > 0, rev / inc, 0.0)
    
    # Add has_gauge column (True if gauge_address exists and is not empty/nan)
    if 'gauge_address' in df.columns:
        df['has_gauge'] = (
            df['gauge_address'].notna() & 
            (df['gauge_address'] != '') &
            (df['gauge_address'].astype(str).str.lower() != 'nan')
        )
    else:
        df['has_gauge'] = False
    
    df = classify_pools(df)
    return df


def _get_possible_data_dirs():
    """Same dirs as load_data() for local Balancer-All-Tokenomics.csv."""
    cwd = os.getcwd()
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
    except Exception:
        script_dir = cwd
        project_root = os.path.dirname(cwd) if os.path.basename(cwd) == 'script' else cwd
    return [
        os.path.join(project_root, 'data'),
        os.path.join(cwd, 'data'),
        os.path.join(cwd, '..', 'data'),
        os.path.join(script_dir, 'data'),
        'data',
    ]


def _set_data_source(source: str):
    """Record data source in session state so UI can show it."""
    try:
        st.session_state["tokenomics_data_source"] = source
    except Exception:
        pass


def _set_data_load_debug(use_neon_views: bool, database_url_set: bool, source: str, rows: int, message: str = ""):
    """Store data-load debug info for sidebar (Streamlit Cloud debugging)."""
    try:
        st.session_state["data_load_debug"] = {
            "use_neon_views": use_neon_views,
            "database_url_set": database_url_set,
            "source": source,
            "rows": rows,
            "message": message,
        }
    except Exception:
        pass


@st.cache_data
def load_data():
    """Load main data: Balancer-All-Tokenomics. Prefer NEON (DATABASE_URL) if set; then local CSV; else Supabase; fallback: balancer_v2_merged / master."""
    database_url_set = bool(os.getenv("DATABASE_URL", "").strip())
    _log(f"[Data load] USE_NEON_VIEWS={USE_NEON_VIEWS!r}, DATABASE_URL set={database_url_set}")
    _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "", 0, "loading...")
    try:
        # 1a) NEON materialized views (low memory: only pool summary + monthly series)
        if USE_NEON_VIEWS:
            _log("[Data load] Attempting NEON materialized views (mv_pool_summary, mv_monthly_series)")
            df = _load_data_from_neon_views()
            if df is not None and not df.empty:
                n = len(df)
                _log(f"[Data load] Loaded from NEON (views), rows={n}")
                _set_data_source("NEON (views)")
                _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "NEON (views)", n, "")
                return _process_main_data(df)
        # 1b) NEON/Postgres full table (or when views not used)
        _log(f"[Data load] Attempting NEON full table ({NEON_TABLE_MAIN!r})")
        df = _load_data_from_neon()
        if df is not None and not df.empty:
            n = len(df)
            _log(f"[Data load] Loaded from NEON full table, rows={n}")
            _set_data_source("NEON")
            _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "NEON (full table)", n, "")
            return _process_main_data(df)

        cwd = os.getcwd()
        possible_data_dirs = _get_possible_data_dirs()
        # 2) Prefer local Balancer-All-Tokenomics.csv so Total BAL Emitted (and other metrics) match notebook / CSV totals
        for data_dir in possible_data_dirs:
            path = os.path.join(os.path.abspath(data_dir), MAIN_DATA_FILENAME)
            if os.path.exists(path) and os.path.getsize(path) > 100:
                df = pd.read_csv(path)
                if df is not None and not df.empty:
                    n = len(df)
                    _log(f"[Data load] Loaded from Local CSV, rows={n}")
                    _set_data_source("Local CSV")
                    _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "Local CSV", n, "")
                    return _process_main_data(df)

        df = download_csv_from_supabase(MAIN_DATA_FILENAME)
        if df is not None and not df.empty:
            n = len(df)
            _log(f"[Data load] Loaded from Supabase, rows={n}")
            _set_data_source("Supabase")
            _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "Supabase", n, "")
            return _process_main_data(df)

        filenames = ['balancer_v2_merged.csv', 'balancer_v2_master.csv']
        df = None
        for fn in filenames:
            df = download_csv_from_supabase(fn)
            if df is not None and not df.empty:
                break
        if df is not None and not df.empty:
            n = len(df)
            _log(f"[Data load] Loaded from Supabase (fallback), rows={n}")
            _set_data_source("Supabase (fallback)")
            _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "Supabase (fallback)", n, "")
            return _process_merged_data(df)

        file_paths = []
        for data_dir in possible_data_dirs:
            abs_d = os.path.abspath(data_dir)
            for fn in filenames:
                file_paths.append(os.path.join(abs_d, fn))
        file_paths.extend([
            os.path.abspath(os.path.join(cwd, '..', 'data', 'balancer_v2_merged.csv')),
            os.path.join(cwd, 'data', 'balancer_v2_merged.csv'),
            'data/balancer_v2_merged.csv',
            'data/balancer_v2_master.csv',
        ])
        df = None
        for path in file_paths:
            try:
                abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
                if os.path.exists(abs_path) and os.path.getsize(abs_path) > 100:
                    df = pd.read_csv(abs_path)
                    if df is not None and not df.empty:
                        n = len(df)
                        _log(f"[Data load] Loaded from Local CSV (fallback), rows={n}")
                        _set_data_source("Local CSV (fallback)")
                        _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "Local CSV (fallback)", n, "")
                        return _process_merged_data(df)
            except Exception:
                continue

        _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "", 0, "No data source found")
        _log("[Data load] No data source found")
        st.error("❌ Balancer-All-Tokenomics.csv not found. Ensure it is in the `data/` folder (or balancer_v2_merged.csv as fallback).")
        with st.expander("🔍 Debug"):
            st.write(f"**CWD:** `{cwd}`")
            for d in possible_data_dirs:
                ad = os.path.abspath(d)
                if os.path.exists(ad):
                    st.write(f"**{ad}:** {[f for f in os.listdir(ad) if f.endswith('.csv')][:15]}")
        return pd.DataFrame()
    except Exception as e:
        _set_data_load_debug(USE_NEON_VIEWS, database_url_set, "", 0, str(e))
        _log(f"[Data load] Error: {e}")
        st.error(f"❌ Error loading data: {str(e)}")
        return pd.DataFrame()


def show_data_source_badge():
    """Show in the sidebar where the main tokenomics data was loaded from (NEON, Local CSV, Supabase)."""
    source = st.session_state.get("tokenomics_data_source")
    if not source:
        return
    if source in ("NEON", "NEON (views)"):
        st.sidebar.success(f"📊 **Data:** {source}")
    else:
        st.sidebar.caption(f"📊 Data: {source}")


def show_data_load_debug():
    """Show data-load debug info in sidebar (for Streamlit Cloud: confirm USE_NEON_VIEWS and which source was used)."""
    info = st.session_state.get("data_load_debug")
    if not info:
        return
    with st.sidebar.expander("🔍 Data load debug", expanded=False):
        st.write(f"**USE_NEON_VIEWS:** `{info.get('use_neon_views', '?')}`")
        st.write(f"**DATABASE_URL set:** `{info.get('database_url_set', '?')}`")
        st.write(f"**Source:** {info.get('source') or '(none)'}")
        st.write(f"**Rows:** {info.get('rows', 0):,}")
        if info.get("message"):
            st.caption(f"Message: {info['message']}")
        if info.get("database_url_set") and not info.get("use_neon_views") and info.get("source") == "NEON (full table)":
            st.warning("Set **USE_NEON_VIEWS=1** in Streamlit Cloud secrets to use materialized views and avoid memory limits.")
        st.caption("Check Streamlit Cloud logs for [Data load] lines.")


def classify_pools(df):
    """Build pool_category (Legitimate / Mercenary / Undefined) from dao_profit, revenue, incentives, ROI."""
    if 'pool_category' in df.columns and df['pool_category'].notna().any():
        return df
    required = ['dao_profit_usd', 'protocol_fee_amount_usd', 'direct_incentives', 'emissions_roi', 'is_core_pool']
    if not all(c in df.columns for c in required):
        return df
    pool_agg = df.groupby('pool_symbol').agg({
        'dao_profit_usd': 'sum',
        'protocol_fee_amount_usd': 'sum',
        'direct_incentives': 'sum',
        'emissions_roi': 'mean',
        'is_core_pool': 'max'
    }).reset_index()
    
    pool_agg.columns = ['pool_symbol', 'total_dao_profit', 'total_revenue', 'total_incentives', 'avg_roi', 'is_core_pool']
    
    pool_agg['incentive_dependency'] = np.where(
        pool_agg['total_revenue'] > 0,
        pool_agg['total_incentives'] / pool_agg['total_revenue'],
        1.0
    )
    
    def classify_pool(row):
        # No incentives at all
        if row['total_incentives'] == 0:
            if row['total_revenue'] > 10000:
                return 'Legitimate'
            return 'Undefined'
        
        # Has incentives but no revenue → definitely mercenary
        if row['total_revenue'] == 0:
            return 'Mercenary'
        
        # Very poor ROI (revenue/incentives < 0.5) → mercenary
        if row['avg_roi'] < 0.5:
            return 'Mercenary'
        
        # Large negative DAO profit → mercenary
        if row['total_dao_profit'] < -1000:
            return 'Mercenary'
        
        # High dependency on incentives (>80% of revenue from incentives) → mercenary
        if row['incentive_dependency'] > 0.8:
            return 'Mercenary'
        
        # Good profitability → legitimate
        if row['total_dao_profit'] > 0 and row['avg_roi'] > 1.0:
            return 'Legitimate'
        
        # Core pools with decent ROI → legitimate
        if row['is_core_pool'] == 1 and row['avg_roi'] > 0.7:
            return 'Legitimate'
        
        # Low revenue pools with incentives that didn't match other criteria
        # These are likely mercenary if revenue is too low
        if row['total_revenue'] < 5000:
            return 'Mercenary'
        
        # Moderate performance pools → undefined
        return 'Undefined'
    
    pool_agg['pool_category'] = pool_agg.apply(classify_pool, axis=1)
    
    df = df.merge(
        pool_agg[['pool_symbol', 'pool_category']],
        on='pool_symbol',
        how='left'
    )
    
    df['pool_category'] = df['pool_category'].fillna('Undefined')
    
    return df

def _normalize_gauge(addr):
    if pd.isna(addr):
        return None
    s = str(addr).strip().lower()
    if s in ("", "nan"):
        return None
    return s


def get_votes_by_pool_from_main_df(df):
    """
    Build votes-by-pool summary from main dataframe (Balancer-Tokenomics via load_data()).
    Returns one row per pool with: pool_symbol, votes, pct_votes, ranking, symbol_clean, project_contract_address, gauge_address.
    """
    if df is None or df.empty:
        return pd.DataFrame()
    if 'votes_received' not in df.columns or 'pool_symbol' not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    df['votes_received'] = pd.to_numeric(df['votes_received'], errors='coerce').fillna(0)
    
    # Prepare aggregation dict - include gauge_address if available
    agg_dict = {
        'votes_received': ('votes_received', 'sum'),
        'project_contract_address': ('project_contract_address', 'first'),
    }
    if 'gauge_address' in df.columns:
        agg_dict['gauge_address'] = ('gauge_address', 'first')
    
    agg = df.groupby('pool_symbol', as_index=False).agg(**agg_dict)
    
    total = agg['votes_received'].sum()
    agg['votes'] = agg['votes_received']
    agg['pct_votes'] = (agg['votes_received'] / total) if total else 0.0
    agg['ranking'] = agg['votes_received'].rank(method='min', ascending=False).astype(int)
    agg['symbol_clean'] = agg['pool_symbol'].fillna('').astype(str)
    agg['symbol'] = agg['pool_symbol']
    
    # If gauge_address was not in original df, use project_contract_address as fallback
    if 'gauge_address' not in agg.columns:
        agg['gauge_address'] = agg['project_contract_address'].fillna('').astype(str)
    else:
        agg['gauge_address'] = agg['gauge_address'].fillna('').astype(str)
    
    agg['gauge'] = agg['gauge_address']
    return agg


@st.cache_data
def load_vebal_votes_from_premerge():
    """Legacy: votes from veBAL_pre_merge_2 + balancer_v2_pre_final_merge. Prefer using load_data() + get_votes_by_pool_from_main_df()."""
    try:
        cwd = os.getcwd()
        data_paths = [
            os.path.abspath(os.path.join(cwd, '..', 'data')),
            os.path.abspath(os.path.join(cwd, 'data')),
            os.path.join(cwd, 'data'),
            'data',
        ]
        vebal_path = b2_path = None
        for d in data_paths:
            vp = os.path.join(d, 'veBAL_pre_merge_2.csv')
            bp = os.path.join(d, 'balancer_v2_pre_final_merge.csv')
            if os.path.exists(vp) and os.path.exists(bp):
                vebal_path, b2_path = vp, bp
                break
        if not vebal_path or not b2_path:
            return pd.DataFrame(), pd.DataFrame()

        vebal = pd.read_csv(vebal_path)
        b2 = pd.read_csv(b2_path)
        if vebal.empty or b2.empty or 'gauge_address' not in vebal.columns or 'gauge_address' not in b2.columns or 'total_votes' not in b2.columns:
            return pd.DataFrame(), pd.DataFrame()

        vebal['block_date_dt'] = pd.to_datetime(vebal['block_date'], errors='coerce')
        vebal['_date'] = vebal['block_date_dt'].dt.date
        vebal['_gauge_norm'] = vebal['gauge_address'].apply(_normalize_gauge)
        vebal_metrics = vebal.dropna(subset=['_gauge_norm']).drop_duplicates(subset=['_gauge_norm', '_date'], keep='first')
        vebal_metrics = vebal_metrics[['_gauge_norm', '_date', 'pool_symbol', 'total_protocol_fee_usd']].copy()

        b2['_date'] = pd.to_datetime(b2['day'], errors='coerce').dt.date
        b2['_gauge_norm'] = b2['gauge_address'].apply(_normalize_gauge)
        b2 = b2.dropna(subset=['_gauge_norm']).copy()

        merged = b2.merge(vebal_metrics, on=['_gauge_norm', '_date'], how='left')
        merged['total_votes'] = pd.to_numeric(merged['total_votes'], errors='coerce').fillna(0)
        merged['pool_symbol'] = merged['pool_symbol'].fillna(merged.get('symbol', pd.Series(dtype=object)))

        latest = merged['_date'].max()
        sub = merged[merged['_date'] == latest].copy()
        sub = sub.dropna(subset=['pool_symbol'])

        agg = sub.groupby('pool_symbol', as_index=False).agg(
            total_votes=('total_votes', 'sum'),
            gauge_address=('gauge_address', 'first'),
        )
        total = agg['total_votes'].sum()
        agg['votes'] = agg['total_votes']
        agg['pct_votes'] = (agg['total_votes'] / total) if total else 0.0
        agg['ranking'] = agg['total_votes'].rank(method='min', ascending=False).astype(int)
        agg['symbol_clean'] = agg['pool_symbol'].fillna('').astype(str)
        agg['symbol'] = agg['pool_symbol']
        g = agg['gauge_address'].fillna('')
        agg['gauge'] = g
        agg['gauge_address'] = g.astype(str)
        df_votes = agg

        df_vebal = vebal.copy()
        if 'total_protocol_fee_usd' not in df_vebal.columns:
            df_vebal['total_protocol_fee_usd'] = 0.0
        return df_votes, df_vebal
    except Exception:
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data
def load_vebal_votes_data():
    """Load veBAL votes: veBAL_votes.csv if available, else derive from balancer_v2_merged (load_data)."""
    try:
        df_votes = download_csv_from_supabase('veBAL_votes.csv')
        if df_votes is not None and not df_votes.empty:
            for col in ['votes', 'pct_votes', 'ranking']:
                if col in df_votes.columns:
                    df_votes[col] = pd.to_numeric(df_votes[col], errors='coerce').fillna(0)
            return df_votes

        cwd = os.getcwd()
        for path in [
            os.path.abspath(os.path.join(cwd, '..', 'data', 'veBAL_votes.csv')),
            os.path.abspath(os.path.join(cwd, 'data', 'veBAL_votes.csv')),
            'data/veBAL_votes.csv',
            'veBAL_votes.csv'
        ]:
            try:
                ap = os.path.abspath(path) if not os.path.isabs(path) else path
                if os.path.exists(ap) and os.path.getsize(ap) > 0:
                    df_votes = pd.read_csv(ap)
                    if not df_votes.empty:
                        for col in ['votes', 'pct_votes', 'ranking']:
                            if col in df_votes.columns:
                                df_votes[col] = pd.to_numeric(df_votes[col], errors='coerce').fillna(0)
                        return df_votes
            except Exception:
                continue

        # Derive from merged (single source)
        df = load_data()
        if df.empty or 'votes_received' not in df.columns or 'pool_symbol' not in df.columns:
            return pd.DataFrame()
        latest = df['block_date'].max()
        sub = df[df['block_date'] == latest].copy()
        agg = sub.groupby('pool_symbol', as_index=False).agg(
            votes_received=('votes_received', 'sum'),
            project_contract_address=('project_contract_address', 'first'),
        )
        total = agg['votes_received'].sum()
        agg['votes'] = agg['votes_received']
        agg['pct_votes'] = (agg['votes_received'] / total) if total else 0
        agg['ranking'] = agg['votes_received'].rank(method='min', ascending=False).astype(int)
        agg['symbol_clean'] = agg['pool_symbol'].fillna('').astype(str)
        agg['symbol'] = agg['pool_symbol']
        agg['gauge'] = agg['project_contract_address'].fillna('')
        agg['gauge_address'] = agg['project_contract_address'].fillna('').astype(str)
        return agg
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_bribes_data():
    """Load bribes and gauges enriched data from Supabase Storage or local filesystem"""
    try:
        # First, try to download from Supabase (try different possible filenames)
        filenames = [
            'Balancer_Bribes_Gauges_enriched.csv',
            'balancer_bribes_gauges_enriched.csv',
            'Balancer_Bribes_Gauges.csv'
        ]
        
        df_bribes = None
        for filename in filenames:
            df_bribes = download_csv_from_supabase(filename)
            if df_bribes is not None and not df_bribes.empty:
                break
        
        if df_bribes is not None and not df_bribes.empty:
            # Process the data
            date_cols = ['date', 'block_date', 'timestamp', 'week', 'period']
            for col in date_cols:
                if col in df_bribes.columns:
                    # Clean date strings: remove time and UTC suffix, keep only YYYY-MM-DD
                    df_bribes[col] = df_bribes[col].astype(str).str.replace(r'\s+\d{2}:\d{2}:\d{2}\.\d+\s+UTC', '', regex=True)
                    df_bribes[col] = df_bribes[col].astype(str).str.replace(r'\s+\d{2}:\d{2}:\d{2}\s+UTC', '', regex=True)
                    df_bribes[col] = df_bribes[col].astype(str).str.replace(r'\s+UTC', '', regex=True)
                    df_bribes[col] = df_bribes[col].astype(str).str.strip()
                    # Convert to datetime
                    df_bribes[col] = pd.to_datetime(df_bribes[col], errors='coerce')
            
            numeric_cols = [
                'bribe_amount_usd', 'bribe_amount', 'total_bribes_usd',
                'votes_received', 'bal_received', 'bal_emitted',
                'bribe_efficiency', 'bribe_per_vote', 'votes_per_bribe',
                'gauge_weight', 'gauge_share', 'bribe_count'
            ]
            
            for col in numeric_cols:
                if col in df_bribes.columns:
                    df_bribes[col] = pd.to_numeric(df_bribes[col], errors='coerce').fillna(0)
            
            return df_bribes
        
        # Fallback to local filesystem
        # Get current working directory (where streamlit is run from)
        cwd = os.getcwd()
        
        # Try different possible file names and paths (in order of likelihood)
        file_paths = [
            os.path.abspath(os.path.join(cwd, '..', 'data', 'Balancer_Bribes_Gauges_enriched.csv')),  # ../data/file.csv
            os.path.abspath(os.path.join(cwd, '..', 'data', 'balancer_bribes_gauges_enriched.csv')),
            os.path.abspath(os.path.join(cwd, '..', 'data', 'Balancer_Bribes_Gauges.csv')),
            os.path.abspath(os.path.join(cwd, 'data', 'Balancer_Bribes_Gauges_enriched.csv')),  # data/file.csv
            os.path.abspath(os.path.join(cwd, 'data', 'balancer_bribes_gauges_enriched.csv')),
            'data/Balancer_Bribes_Gauges_enriched.csv',  # relative
            'data/balancer_bribes_gauges_enriched.csv',
            'Balancer_Bribes_Gauges_enriched.csv'  # current dir
        ]
        
        df_bribes = None
        for path in file_paths:
            try:
                abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
                if os.path.exists(abs_path) and os.path.getsize(abs_path) > 0:
                    df_bribes = pd.read_csv(abs_path)
                    if not df_bribes.empty:
                        break
            except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError, Exception):
                continue
        
        if df_bribes is None or df_bribes.empty:
            return pd.DataFrame()
        
        # Convert date columns if they exist
        date_cols = ['date', 'block_date', 'timestamp', 'week', 'period']
        for col in date_cols:
            if col in df_bribes.columns:
                # Clean date strings: remove time and UTC suffix, keep only YYYY-MM-DD
                df_bribes[col] = df_bribes[col].astype(str).str.replace(r'\s+\d{2}:\d{2}:\d{2}\.\d+\s+UTC', '', regex=True)
                df_bribes[col] = df_bribes[col].astype(str).str.replace(r'\s+\d{2}:\d{2}:\d{2}\s+UTC', '', regex=True)
                df_bribes[col] = df_bribes[col].astype(str).str.replace(r'\s+UTC', '', regex=True)
                df_bribes[col] = df_bribes[col].astype(str).str.strip()
                # Convert to datetime
                df_bribes[col] = pd.to_datetime(df_bribes[col], errors='coerce')
        
        # Convert numeric columns
        numeric_cols = [
            'bribe_amount_usd', 'bribe_amount', 'total_bribes_usd',
            'votes_received', 'bal_received', 'bal_emitted',
            'bribe_efficiency', 'bribe_per_vote', 'votes_per_bribe',
            'gauge_weight', 'gauge_share', 'bribe_count'
        ]
        
        for col in numeric_cols:
            if col in df_bribes.columns:
                df_bribes[col] = pd.to_numeric(df_bribes[col], errors='coerce').fillna(0)
        
        return df_bribes
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading bribes data: {str(e)}")
        return pd.DataFrame()

def get_top_pools(df, n=20):
    """Top N pools by sum(dao_profit_usd) per pool. dao_profit_usd = protocol_fee - direct_incentives."""
    if 'dao_profit_usd' not in df.columns or 'pool_symbol' not in df.columns:
        return []
    return df.groupby('pool_symbol')['dao_profit_usd'].sum().nlargest(n).index.tolist()

def get_worst_pools(df, n=20):
    """Worst N pools by sum(dao_profit_usd) per pool (most negative first)."""
    if 'dao_profit_usd' not in df.columns or 'pool_symbol' not in df.columns:
        return []
    return df.groupby('pool_symbol')['dao_profit_usd'].sum().nsmallest(n).index.tolist()

def run_simulation_sidebar(df):
    st.sidebar.markdown("### ⚖️ Simulation Controls")
    
    st.sidebar.markdown("**1. Protocol Fee Percentage**")
    protocol_fee_pct = st.sidebar.slider(
        "Protocol Fee (%)",
        min_value=0,
        max_value=100,
        value=50,
        step=5,
        help="Percentage of total fees that goes to the protocol before distribution"
    )
    st.sidebar.markdown("**2. Revenue Share**")
    st.sidebar.caption("Division of remaining revenue after protocol fee")
    
    with st.sidebar.expander("📊 Non-Core Pools", expanded=True):
        nc_dao_pct = st.slider(
            "DAO Share (%)",
            min_value=0.0,
            max_value=100.0,
            value=17.5,
            step=0.5,
            key="nc_dao"
        )
        nc_holders_pct = 100 - nc_dao_pct
        st.caption(f"veBAL Holders: {nc_holders_pct}%")
    
    with st.sidebar.expander("⭐ Core Pools", expanded=True):
        c_dao_pct = st.slider(
            "DAO Share (%)",
            min_value=0.0,
            max_value=100.0,
            value=17.5,
            step=0.5,
            key="c_dao"
        )
        remaining_core = 100 - c_dao_pct
        c_holders_pct = st.slider(
            "veBAL Holders (%)",
            min_value=0.0,
            max_value=remaining_core,
            value=12.5,
            step=0.5,
            key="c_holders"
        )
        c_incentives_pct = 100 - c_dao_pct - c_holders_pct
        st.caption(f"Bribes: {c_incentives_pct}%")
    
    st.sidebar.markdown("**3. Emissions**")
    decrease_pct = st.sidebar.number_input(
        "Decrease emission by (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
        help="Decrease BAL emission by this percentage (e.g. 50 = −50%)."
    )
    increase_pct = st.sidebar.number_input(
        "Increase emission by (%)",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
        help="Increase BAL emission by this percentage (e.g. 20 = +20%)."
    )
    df_sim = df.copy()

    # Base BAL/week from data: total BAL emitted in selected period ÷ number of weeks
    if not pd.api.types.is_datetime64_any_dtype(df_sim['block_date']):
        df_sim['block_date'] = pd.to_datetime(df_sim['block_date'], errors='coerce')
    mask_valid_date = df_sim['block_date'].notna()
    df_sim['week'] = pd.NaT
    if mask_valid_date.any():
        df_sim.loc[mask_valid_date, 'week'] = df_sim.loc[mask_valid_date, 'block_date'].dt.to_period('W').dt.start_time
    num_weeks = max(1, df_sim['week'].nunique())
    if 'bal_emited_votes' in df_sim.columns:
        total_bal_from_data = pd.to_numeric(df_sim['bal_emited_votes'], errors='coerce').fillna(0).sum()
    else:
        total_bal_from_data = 0.0
    base_bal_per_week = total_bal_from_data / num_weeks

    emission_factor = (1 - decrease_pct / 100) * (1 + increase_pct / 100)
    effective_emissions = base_bal_per_week * emission_factor

    mask_core = df_sim['is_core_pool'] == 1
    mask_noncore = df_sim['is_core_pool'] == 0

    # Use total_protocol_fee_usd if present (full data), else protocol_fee_amount_usd (view data)
    rev_col = "total_protocol_fee_usd" if "total_protocol_fee_usd" in df_sim.columns else "protocol_fee_amount_usd"
    protocol_fee = pd.to_numeric(df_sim[rev_col], errors="coerce").fillna(0)
    df_sim['sim_protocol_fee'] = protocol_fee * (protocol_fee_pct / 100)
    df_sim['remaining_revenue'] = protocol_fee - df_sim['sim_protocol_fee']
    
    df_sim['sim_dao_revenue'] = 0.0
    df_sim['sim_holders_revenue'] = 0.0
    df_sim['sim_incentives_revenue'] = 0.0
    
    df_sim.loc[mask_noncore, 'sim_dao_revenue'] = (
        df_sim.loc[mask_noncore, 'remaining_revenue'] * (nc_dao_pct / 100)
    )
    df_sim.loc[mask_noncore, 'sim_holders_revenue'] = (
        df_sim.loc[mask_noncore, 'remaining_revenue'] * (nc_holders_pct / 100)
    )
    
    df_sim.loc[mask_core, 'sim_dao_revenue'] = (
        df_sim.loc[mask_core, 'remaining_revenue'] * (c_dao_pct / 100)
    )
    df_sim.loc[mask_core, 'sim_holders_revenue'] = (
        df_sim.loc[mask_core, 'remaining_revenue'] * (c_holders_pct / 100)
    )
    df_sim.loc[mask_core, 'sim_incentives_revenue'] = (
        df_sim.loc[mask_core, 'remaining_revenue'] * (c_incentives_pct / 100)
    )
    
    # Link BAL emission to all revenue: scale by emission scenario (effective ÷ base from data)
    df_sim['sim_dao_revenue'] = df_sim['sim_dao_revenue'] * emission_factor
    df_sim['sim_holders_revenue'] = df_sim['sim_holders_revenue'] * emission_factor
    df_sim['sim_incentives_revenue'] = df_sim['sim_incentives_revenue'] * emission_factor
    
    # Vote share and sim_bal_emitted (effective_emissions already computed above)
    weekly_votes = df_sim.groupby('week')['votes_received'].sum()
    df_sim['weekly_total_votes'] = df_sim['week'].map(weekly_votes)
    df_sim['vote_share'] = np.where(
        df_sim['weekly_total_votes'] > 0,
        df_sim['votes_received'] / df_sim['weekly_total_votes'],
        0
    )
    df_sim['sim_bal_emitted'] = df_sim['vote_share'] * effective_emissions

    # Scale so sum(sim_bal_emitted) = total_bal_from_data * emission_factor (matches soma bruta when factor=1)
    # Rows with 0 votes get 0 from vote_share, so raw sum can be lower; scaling fixes the metric.
    sim_sum = df_sim['sim_bal_emitted'].sum()
    target_total = total_bal_from_data * emission_factor
    if sim_sum > 0 and abs(sim_sum - target_total) > 0.01:
        df_sim['sim_bal_emitted'] = df_sim['sim_bal_emitted'] * (target_total / sim_sum)
    
    df_sim.attrs['protocol_fee_pct'] = protocol_fee_pct
    df_sim.attrs['emissions_per_week'] = effective_emissions
    df_sim.attrs['base_bal_per_week'] = base_bal_per_week
    df_sim.attrs['num_weeks'] = num_weeks
    df_sim.attrs['total_bal_from_data'] = total_bal_from_data
    df_sim.attrs['emission_decrease_pct'] = decrease_pct
    df_sim.attrs['emission_increase_pct'] = increase_pct
    df_sim.attrs['nc_dao_pct'] = nc_dao_pct
    df_sim.attrs['nc_holders_pct'] = nc_holders_pct
    df_sim.attrs['c_dao_pct'] = c_dao_pct
    df_sim.attrs['c_holders_pct'] = c_holders_pct
    df_sim.attrs['c_incentives_pct'] = c_incentives_pct
    
    return df_sim

def create_minimalist_chart(x, y, name, color, height=400):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        mode='lines',
        name=name,
        line=dict(color=color, width=1.5),
        hovertemplate='%{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=height,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor='rgba(255,255,255,0.1)',
            title="",
            tickfont=dict(size=11, color='#8B95A6')
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255,255,255,0.05)',
            showline=False,
            title="",
            tickfont=dict(size=11, color='#8B95A6')
        ),
        hovermode='x unified',
        showlegend=False
    )
    
    return fig

def _normalize_is_core_pool(series):
    """Convert core_non_core or is_core_pool to 0/1 (handles bool, str 'True'/'False', numeric)."""
    if series is None or len(series) == 0:
        return pd.Series(dtype=int)
    s = series.astype(object)
    def to_int(x):
        try:
            if pd.isna(x):
                return 0
            if x is True or x == 1:
                return 1
            if isinstance(x, str) and x.strip().lower() in ('true', '1', 'yes'):
                return 1
            if isinstance(x, (int, float)) and x == 1:
                return 1
            return 0
        except Exception:
            return 0
    return s.map(to_int).astype(int)


def calculate_emission_reduction_impact(df, reduction_factor, core_only=False, revenue_sensitivity=0.0):
    """
    Calculate the impact of emission reduction on pools.
    
    Args:
        df: DataFrame with pool data
        reduction_factor: Factor to reduce emissions (0.5 = 50% reduction, keep 50%)
        core_only: If True, only core pools receive emissions (non-core get 0)
        revenue_sensitivity: 0-1. When > 0, revenue is assumed to drop with emissions
            (e.g. 0.5 = 50% emission cut → 25% revenue cut). 0 = revenue unchanged.
    
    Returns:
        DataFrame with reduced emissions and updated profits
    """
    df_scenario = df.copy()
    
    # Ensure is_core_pool exists and is 0/1 (data may have core_non_core as bool or string)
    if 'is_core_pool' not in df_scenario.columns and 'core_non_core' in df_scenario.columns:
        df_scenario['is_core_pool'] = _normalize_is_core_pool(df_scenario['core_non_core'])
    elif 'is_core_pool' in df_scenario.columns:
        df_scenario['is_core_pool'] = _normalize_is_core_pool(df_scenario['is_core_pool'])
    else:
        df_scenario['is_core_pool'] = 0
    
    # Determine which pools get emissions
    if core_only:
        # Only core pools get emissions, non-core get 0
        emission_mask = (df_scenario['is_core_pool'] == 1)
    else:
        # All pools get emissions (reduced by factor)
        emission_mask = pd.Series([True] * len(df_scenario), index=df_scenario.index)
    
    # Calculate reduced BAL emissions (use bal_emited_votes from data, same as home page)
    bal_col = df_scenario['bal_emited_votes'] if 'bal_emited_votes' in df_scenario.columns else pd.Series(0, index=df_scenario.index)
    bal = pd.to_numeric(bal_col, errors='coerce').fillna(0)
    df_scenario['reduced_bal_emitted'] = (bal.where(emission_mask, 0) * reduction_factor)
    
    # Calculate reduced incentives (proportional to BAL emissions)
    if 'direct_incentives' in df_scenario.columns:
        # For core_only mode, non-core pools get 0 incentives
        # For normal mode, reduce incentives proportionally to BAL reduction
        if core_only:
            # Non-core pools get 0, core pools get reduced by factor
            df_scenario['reduced_incentives'] = df_scenario['direct_incentives'].where(
                emission_mask, 0
            ) * reduction_factor
        else:
            # Reduce incentives proportionally to BAL reduction
            bal_reduction_ratio = df_scenario['reduced_bal_emitted'] / bal.replace(0, 1)
            bal_reduction_ratio = bal_reduction_ratio.fillna(0).replace([float('inf'), -float('inf')], 0)
            df_scenario['reduced_incentives'] = df_scenario['direct_incentives'] * bal_reduction_ratio
    else:
        df_scenario['reduced_incentives'] = 0
    
    # Scenario revenue: when revenue_sensitivity > 0, assume revenue drops with emissions
    # revenue_scenario = revenue_baseline * (1 - (1 - reduction_factor) * revenue_sensitivity)
    # e.g. 50% emission cut (reduction_factor=0.5), sensitivity=0.5 → revenue * 0.75 (25% drop)
    rev_col = 'protocol_fee_amount_usd' if 'protocol_fee_amount_usd' in df_scenario.columns else 'sim_dao_revenue'
    if rev_col in df_scenario.columns:
        base_rev = pd.to_numeric(df_scenario[rev_col], errors='coerce').fillna(0)
        if revenue_sensitivity > 0:
            rev_factor = 1 - (1 - reduction_factor) * float(revenue_sensitivity)
            df_scenario['scenario_revenue'] = base_rev * rev_factor
        else:
            df_scenario['scenario_revenue'] = base_rev
    else:
        df_scenario['scenario_revenue'] = 0
    
    # Calculate new DAO profit: scenario_revenue - reduced_incentives
    df_scenario['new_dao_profit'] = df_scenario['scenario_revenue'] - df_scenario['reduced_incentives']
    
    return df_scenario
