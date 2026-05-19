import streamlit as st
import streamlit.components.v1 as components
import json
import io
import zipfile
import re
import os
import sys
import base64
import unicodedata
from difflib import SequenceMatcher
from PIL import Image

# Garante que o Python encontra src/ independente de onde o Streamlit é iniciado
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from src.drive_sync import (
        conectar_planilha,
        buscar_mapeamento_contas,
        buscar_cores_linhas,
    )
except Exception as e:
    import streamlit as st
    st.error(f"Erro ao importar drive_sync.py: {e}")
    st.stop()
    
from src.core import processar_curso, obter_template_whatsapp, processar_instagram, normalizar_chave

# Configuração da Interface
favicon_path = os.path.join(BASE_DIR, "logo-site.png")

if os.path.exists(favicon_path):
    favicon = Image.open(favicon_path)
else:
    favicon = "⚙️"

st.set_page_config(
    page_title="CESS Automation Web",
    page_icon=favicon,
    layout="centered"
)

# Diretório base sempre relativo ao próprio app.py (resolve problema de cwd)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def template_path(nome_arquivo):
    return os.path.join(BASE_DIR, "templates", nome_arquivo)


def image_to_base64(path):
    try:
        with open(path, "rb") as img:
            return base64.b64encode(img.read()).decode()
    except FileNotFoundError:
        return ""

LOGO_PATH = os.path.join(BASE_DIR, "logo_automacao_fluxo.png")
LOGO_B64 = image_to_base64(LOGO_PATH)


def aplicar_design():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {{
            --bg:#05080f;
            --panel:rgba(10,26,48,.84);
            --line:rgba(61,151,255,.28);
            --text:#f3f7ff;
            --muted:#a8b8d8;
            --blue:#2f9bff;
        }}

        html, body, [data-testid="stAppViewContainer"] {{
            background:
                radial-gradient(circle at 12% 88%, rgba(0,78,190,.34), transparent 18rem),
                radial-gradient(circle at 82% 15%, rgba(0,125,255,.12), transparent 20rem),
                linear-gradient(135deg,#030508 0%,#07101f 42%,#020409 100%) !important;
            color:var(--text);
            font-family:'Inter',sans-serif;
        }}

        [data-testid="stHeader"], [data-testid="stToolbar"] {{
            background:transparent !important;
        }}

        /* Moldura principal dinâmica: cresce junto com o conteúdo da página */
        .block-container,
        [data-testid="stMainBlockContainer"] {{
            max-width:1040px !important;
            width:100% !important;
            padding-top:3.2rem !important;
            padding-left:1.5rem !important;
            padding-right:1.5rem !important;
            padding-bottom:2.4rem !important;
            margin:3.5rem auto 2.5rem auto !important;
            position:relative;
            z-index:1;
            border:1px solid rgba(28,113,255,.35);
            border-radius:18px;
            background:rgba(3,10,22,.22);
            box-shadow:0 0 42px rgba(0,91,255,.20), inset 0 0 70px rgba(10,88,180,.08);
        }}

        .cess-panel {{
            width:100%;
            padding:32px 38px 28px;
            border:1px solid var(--line);
            border-radius:18px;
            background:
                linear-gradient(180deg,rgba(15,41,73,.90),rgba(8,20,36,.84)),
                repeating-linear-gradient(90deg,rgba(255,255,255,.018) 0 1px,transparent 1px 8px);
            box-shadow:0 30px 90px rgba(0,0,0,.52), inset 0 1px 0 rgba(255,255,255,.06);
            backdrop-filter:blur(14px);
            margin-bottom:24px;
        }}

        .cess-top {{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:22px;
            margin-bottom:26px;
        }}

        .cess-brand {{
            display:flex;
            align-items:center;
            gap:22px;
        }}
        .cess-logo-wrap {{
            width:76px;
            height:76px;
            display:flex;
            align-items:center;
            justify-content:center;
            flex:0 0 76px;
        }}
        .cess-brand img {{
            width:70px;
            height:70px;
            object-fit:contain;
            display:block;
            filter:drop-shadow(0 0 18px rgba(46,155,255,.42));
            transform: translateY(-13px);
        }}

        .cess-title {{
            font-size:2.15rem;
            font-weight:800;
            letter-spacing:-.045em;
            margin:0;
            line-height:1.05;
        }}

        .cess-subtitle {{
            color:var(--muted);
            font-size:.92rem;
            margin-top:8px;
        }}

        .cess-badge {{
            border:1px solid rgba(77,159,255,.24);
            background:rgba(5,12,25,.55);
            color:#dceaff;
            padding:8px 14px;
            border-radius:999px;
            font-size:.76rem;
            font-weight:700;
            white-space:nowrap;
        }}

        .steps {{
            display:grid;
            grid-template-columns:repeat(3, 1fr);
            gap:18px;
            padding:8px 0 22px;
            border-bottom:1px solid rgba(73,150,255,.30);
            margin-bottom:24px;
        }}

        .step {{
            display:flex;
            align-items:center;
            justify-content:center;
            gap:10px;
            color:#c7d6ef;
            font-weight:600;
        }}

        .step span {{
            width:30px;
            height:30px;
            display:inline-flex;
            align-items:center;
            justify-content:center;
            border-radius:50%;
            border:1px solid rgba(120,168,255,.36);
            background:rgba(0,0,0,.28);
            color:#dce9ff;
            font-weight:800;
        }}

        .step.active span {{
            background:linear-gradient(135deg,#5ab2ff,#166fd5);
            border-color:transparent;
            color:white;
            box-shadow:0 0 20px rgba(47,155,255,.45);
        }}

        .section-title {{ font-size:1.28rem; font-weight:800; margin-bottom:6px; }}
        .section-copy {{ color:var(--muted); margin-bottom:0; }}

        label, [data-testid="stWidgetLabel"] p {{
            color:#eef5ff !important;
            font-weight:600 !important;
        }}

        [data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {{
            background:rgba(8,15,32,.78) !important;
            border:1px solid rgba(109,154,220,.34) !important;
            border-radius:10px !important;
            color:white !important;
            min-height:48px;
            box-shadow:inset 0 0 0 1px rgba(255,255,255,.02);
        }}

        [data-testid="stTextInput"] input:focus {{
            border-color:rgba(58,156,255,.85) !important;
            box-shadow:0 0 0 3px rgba(58,156,255,.18) !important;
        }}

        .stButton > button,
        [data-testid="stDownloadButton"] button {{
            min-height:54px;
            border-radius:12px !important;
            border:1px solid rgba(91,84,255,.65) !important;
            background:linear-gradient(90deg,rgba(44,28,127,.96),rgba(21,55,137,.95)) !important;
            color:#fff !important;
            font-weight:800 !important;
            box-shadow:0 0 26px rgba(65,60,255,.22), inset 0 1px 0 rgba(255,255,255,.10);
            transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }}

        .stButton > button:hover,
        [data-testid="stDownloadButton"] button:hover {{
            transform:translateY(-10px);
            border-color:rgba(81,171,255,.85) !important;
            box-shadow:0 0 34px rgba(50,145,255,.30), inset 0 1px 0 rgba(255,255,255,.14);
        }}

        [data-testid="stCheckbox"] label {{
            background:rgba(6,14,30,.36);
            border:1px solid rgba(94,148,220,.16);
            border-radius:12px;
            padding:12px 14px;
            width:100%;
        }}

        hr {{
            border-color:rgba(75,151,255,.24) !important;
            margin:1.4rem 0 !important;
        }}

        [data-testid="stAlert"] {{
            border-radius:12px;
            border:0 !important;
            background:transparent !important;
            box-shadow:none !important;
            padding-left:0 !important;
            padding-right:0 !important;
        }}

        .cess-status {{
            margin:16px 0 6px;
            padding:0;
            border:0;
            background:transparent;
            color:#cfe0ff;
            font-size:.94rem;
            font-weight:600;
        }}
        .cess-status.success {{ color:#53f29a; }}
        .cess-status.warning {{ color:#ffd166; }}
        .cess-status.error {{ color:#ff7676; }}
        .cess-status.info {{ color:#65b7ff; }}

        .cess-footer {{
            display:flex;
            justify-content:flex-end;
            align-items:center;
            gap:10px;
            color:#eef4ff;
            font-size:.84rem;
            margin-top:24px;
        }}

        .cess-footer span {{
            background:rgba(255,255,255,.08);
            border-radius:999px;
            padding:5px 12px;
            font-weight:800;
        }}

        [data-testid="stCaptionContainer"] {{
            text-align:center;
            color:rgba(225,236,255,.76) !important;
        }}

        @media (max-width:900px) {{
            .block-container,
            [data-testid="stMainBlockContainer"] {{
                margin:1.2rem auto 1.2rem auto !important;
                padding-top:2.5rem !important;
                padding-left:1rem !important;
                padding-right:1rem !important;
            }}
            .cess-panel {{ padding:24px 20px; }}
            .cess-top {{ display:grid; grid-template-columns:1fr; }}
            .steps {{ grid-template-columns:1fr; }}
            .step {{ justify-content:flex-start; }}
            .cess-title {{ font-size:1.45rem; }}
        }}
    </style>
    """, unsafe_allow_html=True)

def render_header(etapa=1):
    active_1 = "active" if etapa == 1 else ""
    active_2 = "active" if etapa == 2 else ""
    active_3 = "active" if etapa == 3 else ""
    logo_html = f'<div class="cess-logo-wrap"><img src="data:image/png;base64,{LOGO_B64}" alt="Logo CESS Automation"></div>' if LOGO_B64 else ''
    st.markdown(f"""
    <div class="cess-panel">
        <div class="cess-top">
            <div class="cess-brand">
                {logo_html}
                <div>
                    <h1 class="cess-title">CESS • Gerador de Fluxos</h1>
                    <div class="cess-subtitle">Gere e baixe seus arquivos JSON de automação de forma simples e rápida.</div>
                </div>
            </div>
            <div class="cess-badge">CESS Automation System · 2026</div>
        </div>
        <div class="steps">
            <div class="step {active_1}"><span>1</span> Configurar</div>
            <div class="step {active_2}"><span>2</span> Gerar Fluxo</div>
            <div class="step {active_3}"><span>3</span> Download</div>
        </div>
        <div class="section-title">Vamos começar</div>
        <div class="section-copy">Preencha as informações abaixo para gerar seu fluxo de automação.</div>
    </div>
    """, unsafe_allow_html=True)

def status_visual(mensagem, tipo="info"):
    st.markdown(f'<div class="cess-status {tipo}">{mensagem}</div>', unsafe_allow_html=True)


def ativar_enter_proximo_botao():
    """
    Atalho de produtividade: ao pressionar Enter, clica no próximo botão
    lógico do processo.

    Observação: Streamlit renderiza alguns componentes de forma assíncrona,
    então o script abaixo registra o evento no documento pai e usa uma pequena
    trava de tempo para evitar cliques duplicados.
    """
    components.html(
        """
        <script>
        const doc = window.parent.document;

        function isVisible(el) {
          if (!el) return false;
          const style = window.parent.getComputedStyle(el);
          const rect = el.getBoundingClientRect();
          return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
        }

        function isDisabled(btn) {
          return btn.disabled ||
                 btn.getAttribute('aria-disabled') === 'true' ||
                 btn.closest('[aria-disabled="true"]');
        }

        function findButtonByText(textParts) {
          const buttons = Array.from(doc.querySelectorAll('button'));
          return buttons.find(btn => {
            const text = (btn.innerText || btn.textContent || '').toLowerCase();
            return !isDisabled(btn) && isVisible(btn) && textParts.every(part => text.includes(part));
          });
        }

        function clickNextButton(event) {
          if (event.key !== 'Enter' && event.code !== 'Enter' && event.code !== 'NumpadEnter') return;
          if (event.shiftKey || event.ctrlKey || event.altKey || event.metaKey) return;

          const target = event.target;
          const tag = (target && target.tagName ? target.tagName : '').toLowerCase();
          if (tag === 'textarea') return;

          const now = Date.now();
          if (window.parent.__cessLastEnterClick && now - window.parent.__cessLastEnterClick < 900) return;

          let nextButton = null;

          // Quando o foco está no campo de data, o Enter deve aplicar o valor
          // e já acionar a busca na planilha. O pequeno atraso ajuda o Streamlit
          // a sincronizar o texto digitado antes do clique.
          if (tag === 'input') {
            nextButton = findButtonByText(['buscar', 'planilha']);
          }

          if (!nextButton) {
            nextButton =
              findButtonByText(['gerar', 'zip']) ||
              findButtonByText(['baixar']) ||
              findButtonByText(['buscar', 'planilha']);
          }

          if (nextButton) {
            window.parent.__cessLastEnterClick = now;
            event.preventDefault();
            event.stopPropagation();
            setTimeout(() => nextButton.click(), tag === 'input' ? 260 : 40);
          }
        }

        if (!window.parent.__cessEnterShortcutInstalledV3) {
          window.parent.__cessEnterShortcutInstalledV3 = true;
          doc.addEventListener('keydown', clickNextButton, true);
          window.parent.addEventListener('keydown', clickNextButton, true);
        }
        </script>
        """,
        height=0,
        width=0,
    )

def identificar_tipo_evento(nome_item):
    """Congressos começam com número; cursos começam com letra."""
    nome = str(nome_item or "").strip()
    return "congresso" if nome[:1].isdigit() else "curso"


def normalizar_nome_busca(texto):
    """
    Normaliza nomes de cursos para comparação flexível entre abas.

    O objetivo é evitar falhas por acento, caixa alta/baixa, hífen, pontuação
    ou espaços extras. Ex.: "AUTOCAD - BÁSICO" vira "autocad basico".
    """
    texto = str(texto or "").strip().casefold()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(ch for ch in texto if unicodedata.category(ch) != "Mn")
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def remover_prefixo_numero_congresso(texto):
    """
    Remove número/ordinal no começo do nome para ajudar a localizar congressos
    quando uma aba está com "1º Congresso..." e outra só com "Congresso...".
    """
    texto = str(texto or "").strip()
    return re.sub(r"^\s*\d+\s*[º°ª]?\s*[-–—.]?\s*", "", texto).strip()


def buscar_info_instagram_por_curso(nome_curso, instagram_infos):
    """
    Busca o número do fluxo na aba Instagram_Infos sem depender de nome 100% exato.

    Ordem de decisão:
      1. match exato simples;
      2. match exato normalizado;
      3. match exato removendo número inicial de congresso;
      4. match por prefixo único, priorizando o nome mais específico;
      5. match aproximado seguro.

    Se houver empate/ambiguidade, retorna aviso para não escolher errado.
    """
    if not nome_curso or not instagram_infos:
        return None, "sem dados"

    # Compatibilidade com o formato antigo: dicionário por chave.
    info_exata = instagram_infos.get(normalizar_chave(nome_curso))
    if info_exata:
        return info_exata, None

    candidatos = [v for k, v in instagram_infos.items() if not str(k).startswith("__") and isinstance(v, dict)]
    if not candidatos:
        return None, "sem candidatos"

    alvo_original = str(nome_curso).strip()
    alvo_norm = normalizar_nome_busca(alvo_original)
    alvo_sem_num_norm = normalizar_nome_busca(remover_prefixo_numero_congresso(alvo_original))

    def norm_candidato(info):
        return normalizar_nome_busca(info.get("curso", ""))

    # 1/2. exato normalizado
    for info in candidatos:
        if norm_candidato(info) == alvo_norm:
            return info, None

    # 3. exato sem prefixo numérico/ordinal
    if alvo_sem_num_norm and alvo_sem_num_norm != alvo_norm:
        for info in candidatos:
            if norm_candidato(info) == alvo_sem_num_norm:
                return info, None

    # 4. prefixo: útil para casos como AUTOCAD x AUTOCAD - BÁSICO AO INTERMEDIÁRIO.
    prefixos = []
    for info in candidatos:
        cand_norm = norm_candidato(info)
        if not cand_norm:
            continue
        if alvo_norm.startswith(cand_norm + " ") or cand_norm.startswith(alvo_norm + " "):
            prefixos.append((len(cand_norm), info))
        elif alvo_sem_num_norm and (alvo_sem_num_norm.startswith(cand_norm + " ") or cand_norm.startswith(alvo_sem_num_norm + " ")):
            prefixos.append((len(cand_norm), info))

    if prefixos:
        prefixos.sort(key=lambda item: item[0], reverse=True)
        maior = prefixos[0][0]
        melhores = [info for tamanho, info in prefixos if tamanho == maior]
        if len(melhores) == 1:
            return melhores[0], None
        nomes = ", ".join(info.get("curso", "") for info in melhores[:5])
        return None, f"ambíguo entre: {nomes}"

    # 5. aproximação segura. Só aceita se o melhor estiver bem acima do segundo.
    scores = []
    for info in candidatos:
        cand_norm = norm_candidato(info)
        if not cand_norm:
            continue
        score = max(
            SequenceMatcher(None, alvo_norm, cand_norm).ratio(),
            SequenceMatcher(None, alvo_sem_num_norm, cand_norm).ratio() if alvo_sem_num_norm else 0,
        )
        scores.append((score, info))

    scores.sort(key=lambda item: item[0], reverse=True)
    if scores and scores[0][0] >= 0.86:
        segundo = scores[1][0] if len(scores) > 1 else 0
        if scores[0][0] - segundo >= 0.08:
            return scores[0][1], None

    return None, "não encontrado com segurança"


def buscar_infos_instagram(client, spreadsheet_name="Informações Webhook", worksheet_name="Instagram_Infos"):
    """
    Lê a aba Instagram_Infos e devolve:
        { curso_normalizado: {"curso": Curso, "num_fluxo": Num} }

    Estrutura esperada:
        Coluna A: Curso
        Coluna B: Num
    """
    try:
        aba = client.open(spreadsheet_name).worksheet(worksheet_name)
        linhas = aba.get_all_values(value_render_option="FORMATTED_VALUE")
    except Exception as e:
        status_visual(f"⚠️ Não consegui ler a aba {worksheet_name}: {e}", "warning")
        return {}

    infos = {}
    for linha in linhas[1:]:
        if len(linha) < 2:
            continue
        curso = str(linha[0]).strip()
        num_fluxo = str(linha[1]).strip()
        if curso and num_fluxo:
            infos[normalizar_chave(curso)] = {
                "curso": curso,
                "num_fluxo": num_fluxo,
            }
    return infos


aplicar_design()
ativar_enter_proximo_botao()

# Mapeamento Global dos Fluxos
TEMPLATES = {
    "1":  {"nome": "Inscrição",     "path": template_path("esqueleto_fluxo_insc.json"),    "subpasta": "Fluxo_insc"},
    "2":  {"nome": "Pré-Inscrição", "path": template_path("esqueleto_fluxo_pre_insc.json"),"subpasta": "Fluxo_pre_insc"},
    "3":  {"nome": "Fluxo 1",       "path": template_path("esqueleto_fluxo_1.json"),        "subpasta": "Fluxo_1"},
    "4":  {"nome": "Fluxo 2",       "path": template_path("esqueleto_fluxo_2.json"),        "subpasta": "Fluxo_2"},
    "15": {"nome": "F2.1",          "path": template_path("esqueleto_fluxo_2.1.json"),      "subpasta": "Fluxo_F2_1"},
    "5":  {"nome": "Fluxo 3",       "path": template_path("esqueleto_fluxo_3.json"),        "subpasta": "Fluxo_3"},
    "6":  {"nome": "Fluxo 4",       "path": template_path("esqueleto_fluxo_4.json"),        "subpasta": "Fluxo_4"},
    "7":  {"nome": "Fluxo 5",       "path": template_path("esqueleto_fluxo_5.json"),        "subpasta": "Fluxo_5"},
    "17": {"nome": "F5.1",          "path": template_path("esqueleto_fluxo_5.1.json"),      "subpasta": "Fluxo_F5_1"},
    "8":  {"nome": "Fluxo 6",       "path": template_path("esqueleto_fluxo_6.json"),        "subpasta": "Fluxo_6"},
    "9":  {"nome": "Fluxo 7",       "path": template_path("esqueleto_fluxo_7.json"),        "subpasta": "Fluxo_7"},
    "19": {"nome": "SC0",           "path": template_path("esqueleto_fluxo_sc3.json"),      "subpasta": "Fluxo_SC0"},
    "11": {"nome": "SC1",           "path": template_path("esqueleto_fluxo_sc1.json"),      "subpasta": "Fluxo_SC1"},
    "12": {"nome": "SC2",           "path": template_path("esqueleto_fluxo_sc2.json"),      "subpasta": "Fluxo_SC2"},
    "13": {"nome": "SC3",           "path": template_path("esqueleto_fluxo_sc3.json"),      "subpasta": "Fluxo_SC3"},
    "18": {"nome": "Retroativo",    "path": template_path("esqueleto_fluxo_sc3.json"),      "subpasta": "Fluxo_Retroativo"},
    "16": {"nome": "RETOMADA",      "path": template_path("esqueleto_retomada.json"),       "subpasta": "Fluxo_Retomada"},
    "20": {"nome": "Entrega - Certificado Digital", "path": template_path("esqueleto_entrega_certificado_digital.json"), "subpasta": "Fluxo_Entrega_Certificado_Digital"},
    "21": {"nome": "Instagram Comentário", "path": template_path("esqueleto_instagram_comentario.json"), "subpasta": "Fluxo_Instagram_Comentario", "tipo": "instagram", "origem": "Comentário"},
    "22": {"nome": "Instagram Story", "path": template_path("esqueleto_instagram_story.json"), "subpasta": "Fluxo_Instagram_Story", "tipo": "instagram", "origem": "Story"},
    "23": {"nome": "Instagram Comentário + Story", "path": None, "subpasta": "Fluxo_Instagram", "tipo": "instagram_duplo"},
    "14": {"nome": "Docs",          "path": template_path("esqueleto_docs.json"),           "subpasta": "Fluxo_Docs"}
}

etapa_atual = 3 if "zip_gerado" in st.session_state else (2 if "cursos" in st.session_state else 1)
render_header(etapa_atual)


# Opções exibidas na interface. Agora é multiseleção para permitir gerar
# combinações específicas sem precisar baixar um fluxo por vez.
OPCOES_FLUXO = [
    "GERAR TODOS",
    "Inscrição", "Pré-Inscrição", "F1", "F2", "F2.1", "F3", "F4", "F5", "F5.1", "F6", "F7",
    "SC0", "SC1", "SC2", "SC3",
    "Retroativo", "RETOMADA", "Entrega - Certificado Digital",
    "Instagram Comentário", "Instagram Story", "Instagram Comentário + Story",
    "Docs (Em breve) 🔒",
]

MAP_LABELS = {
    "Inscrição":"1", "Pré-Inscrição":"2", "F1":"3", "F2":"4", "F2.1":"15", "F3":"5",
    "F4":"6", "F5":"7", "F5.1":"17", "F6":"8", "F7":"9", "SC0":"19", "SC1":"11", "SC2":"12",
    "SC3":"13", "Retroativo":"18", "RETOMADA":"16", "Entrega - Certificado Digital":"20",
    "Instagram Comentário":"21", "Instagram Story":"22", "Instagram Comentário + Story":"23",
    "Docs (Em breve) 🔒": "14", "GERAR TODOS":"99"
}

# O botão/seleção "GERAR TODOS" passa a gerar somente os fluxos principais
# do WhatsApp, sem Instagram, Entrega de Certificado, Retomada, Retroativo ou Docs.
IDS_GERAR_TODOS_FLUXOS = ["2", "1", "3", "4", "15", "5", "6", "7", "17", "8", "9", "19", "11", "12", "13"]

# --- 1. CONFIGURAÇÃO DE ENTRADA ---
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        fluxo_labels = st.multiselect(
            "Selecione o(s) Fluxo(s):",
            OPCOES_FLUXO,
            placeholder="Escolha uma ou mais opções"
        )

        # Compatibilidade: várias partes do app usam id_fluxo.
        # Agora ele representa a lista completa de IDs selecionados.
        ids_fluxos = [MAP_LABELS[label] for label in fluxo_labels if label in MAP_LABELS]
        id_fluxo = ids_fluxos[0] if len(ids_fluxos) == 1 else None
        fluxo_label = fluxo_labels[0] if len(fluxo_labels) == 1 else None

    with col2:
        data_semana = st.text_input("Data do Curso (para as tags de Clique):", value="", placeholder="Ex: 16/02")

# --- LÓGICA ESPECÍFICA PARA RETOMADA ---
ano_retomada = None
if "RETOMADA" in fluxo_labels:
    status_visual("📂 Configuração de Retomada", "info")
    nome_fluxo_retomada = st.text_input("Nome do Fluxo (Ex: Retomada - T 2023):", placeholder="Retomada - T 2023")
    match_ano = re.search(r"202\d", nome_fluxo_retomada)
    if match_ano:
        ano_retomada = match_ano.group(0)
    else:
        status_visual("⚠️ Digite o ano no campo acima para gerar os links corretamente.", "warning")

# --- LÓGICA DE FLUXO RETROATIVO ---
st.divider()
is_retro = st.checkbox("🔄 Este fluxo é retroativo? (Ex: curso de Janeiro rodando agora)")
data_disparo_manual = None

if is_retro:
    data_disparo_manual = st.text_input("Data da Segunda-feira que vai RODAR (DD/MM):", placeholder="Ex: 02/02")
    if data_disparo_manual:
        status_visual(f"💡 Modo retroativo ativo: disparos em {data_disparo_manual} e identidade do fluxo mantida como safra de {data_semana}.", "info")

# --- 2. BUSCA DE DADOS ---
if st.button("🔍 Buscar Cursos na Planilha", use_container_width=True, disabled=not (fluxo_labels and data_semana)):
    with st.spinner("Acessando Google Sheets..."):
        client = conectar_planilha("Informações Webhook")
        if client:
            try:
                aba = client.open("Informações Webhook").worksheet("Cursos 2026")
                dados = aba.get_all_values(value_render_option='FORMATTED_VALUE')
                
                inicio = next((i + 2 for i, l in enumerate(dados) if len(l) > 1 and data_semana in str(l[1])), None)
                
                if inicio:
                    cursos_encontrados = []
                    for i in range(inicio, len(dados)):
                        linha = dados[i]
                        if not linha or not linha[0].strip() or (len(linha) > 1 and "Semana" in str(linha[1])):
                            break
                        cursos_encontrados.append(linha[0].strip())
                    
                    # Lê as cores das linhas e monta o mapeamento de cores -> contas
                    with st.spinner("Lendo cores das contas na planilha..."):
                        mapeamento_contas = buscar_mapeamento_contas(client, "Informações Webhook")

                        cores_lista = buscar_cores_linhas(
                            client,
                            "Informações Webhook",
                            "Cursos 2026",
                            inicio + 1,
                            len(cursos_encontrados),
                        )

                    cores_por_indice = {
                        inicio + j: cor
                        for j, cor in enumerate(cores_lista)
                    }

                    st.session_state['cursos'] = cursos_encontrados
                    st.session_state['dados_planilha'] = dados
                    st.session_state['index_inicio'] = inicio
                    st.session_state['mapeamento_contas'] = mapeamento_contas
                    st.session_state['cores_por_indice'] = cores_por_indice

                    with st.spinner("Lendo informações do Instagram..."):
                        st.session_state['instagram_infos'] = buscar_infos_instagram(client)

                    if mapeamento_contas:
                        contas = ", ".join(sorted(set(mapeamento_contas.values())))
                        status_visual(f"✅ {len(cursos_encontrados)} cursos encontrados. Contas detectadas: {contas}.", "success")
                    else:
                        status_visual(f"✅ {len(cursos_encontrados)} cursos encontrados. ⚠️ As cores das contas não foram detectadas.", "warning")
                else:
                    status_visual(f"❌ A data '{data_semana}' não foi encontrada na Coluna B da planilha.", "error")
            except Exception as e:
                status_visual(f"❌ Erro ao abrir a planilha/aba: {e}", "error")

# --- 3. FILTRO E GERAÇÃO ---
if 'cursos' in st.session_state:
    st.divider()
    st.subheader("Configuração da Geração")
    
    curso_filtro = st.multiselect(
        "Selecione cursos específicos (ou deixe vazio para todos):", 
        st.session_state['cursos']
    )

    if "14" in ids_fluxos:
        status_visual("🔒 O fluxo de Docs ainda está em desenvolvimento e será ignorado na geração.", "warning")

    btn_disabled = not bool(ids_fluxos)

    if st.button("🏗️ Gerar Arquivos e Preparar ZIP", use_container_width=True, disabled=btn_disabled):
        zip_buffer = io.BytesIO()
        arquivos_criados = 0
        mapeamento_contas = st.session_state.get('mapeamento_contas', {})
        cores_por_indice = st.session_state.get('cores_por_indice', {})
        instagram_infos = st.session_state.get('instagram_infos', {})

        todos_os_cursos = st.session_state['cursos']
        cursos_selecionados_set = set(curso_filtro if curso_filtro else todos_os_cursos)
        
        ids_geracao = []
        for fluxo_id in ids_fluxos:
            if fluxo_id == "99":
                ids_geracao.extend(IDS_GERAR_TODOS_FLUXOS)
            elif fluxo_id == "23":
                ids_geracao.extend(["21", "22"])
            elif fluxo_id != "14":
                ids_geracao.append(fluxo_id)

        # Remove duplicados preservando a ordem selecionada.
        ids_geracao = list(dict.fromkeys(ids_geracao))

        fluxos_alvo = [TEMPLATES[fluxo_id] for fluxo_id in ids_geracao if fluxo_id in TEMPLATES]

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for config in fluxos_alvo:
                contadores_por_conta = {}
                nome_fluxo_ativo = config['nome']

                # Para RETOMADA: conta o total de cursos ANTES do loop para calcular o delay certo
                total_cursos_semana = None
                if nome_fluxo_ativo == "RETOMADA":
                    total_cursos_semana = 0
                    for i in range(st.session_state['index_inicio'], len(st.session_state['dados_planilha'])):
                        linha_aux = st.session_state['dados_planilha'][i]
                        if not linha_aux or not linha_aux[0].strip() or (len(linha_aux) > 1 and "Semana" in str(linha_aux[1])):
                            break
                        nome_aux = linha_aux[0].strip()
                        if nome_aux in cursos_selecionados_set:
                            total_cursos_semana += 1
                
                for i in range(st.session_state['index_inicio'], len(st.session_state['dados_planilha'])):
                    linha = st.session_state['dados_planilha'][i]
                    if not linha or not linha[0].strip() or (len(linha) > 1 and "Semana" in str(linha[1])):
                        break
                    
                    nome_curso = linha[0].strip()
                    if nome_curso not in cursos_selecionados_set:
                        continue

                    tipo_evento = identificar_tipo_evento(nome_curso)
                    modo_congresso = tipo_evento == "congresso"

                    cor_curso = cores_por_indice.get(i, "#FFFFFF")
                    conta_pasta = mapeamento_contas.get(cor_curso, "Sem_Conta")

                    if conta_pasta not in contadores_por_conta:
                        contadores_por_conta[conta_pasta] = 0

                    contador_delay_conta = contadores_por_conta[conta_pasta]
                    dados_template_whatsapp = obter_template_whatsapp(conta_pasta, config["nome"], tipo_evento=tipo_evento)

                    try:
                        if config.get("tipo") == "instagram":
                            info_ig, motivo_ig = buscar_info_instagram_por_curso(nome_curso, instagram_infos)
                            if not info_ig:
                                status_visual(
                                    f"⚠️ Instagram: curso '{nome_curso}' não encontrado na aba Instagram_Infos ({motivo_ig}).",
                                    "warning"
                                )
                                continue

                            json_data = processar_instagram(
                                linha,
                                data_semana,
                                config["path"],
                                info_ig["num_fluxo"],
                                config["origem"],
                            )
                        else:
                            json_data = processar_curso(
                                linha, 
                                data_semana, 
                                config['path'], 
                                contador_delay_conta, 
                                tipo_fluxo=nome_fluxo_ativo,
                                data_disparo=data_disparo_manual,
                                ano_retomada=ano_retomada,
                                total_cursos=total_cursos_semana,
                                dados_template_whatsapp=dados_template_whatsapp,
                                usar_delay_retomada=(nome_fluxo_ativo == "RETOMADA"),
                                modo_congresso=modo_congresso
                            )

                        nome_limpo = nome_curso.replace(" ", "_").replace("/", "-").replace(":", "")

                        if config.get("tipo") == "instagram":
                            # Instagram é sempre organizado por curso, porque Comentário e Story
                            # são criados juntos no processo da equipe.
                            nome_origem = str(config.get("origem", "Instagram")).replace("á", "a").replace("ó", "o")
                            caminho_zip = f"Fluxo_Instagram/{nome_limpo}/{nome_origem}.json"
                        else:
                            caminho_zip = f"{config['subpasta']}/{conta_pasta}/{nome_limpo}.json"

                        zip_file.writestr(caminho_zip, json.dumps(json_data, indent=2, ensure_ascii=False))
                        arquivos_criados += 1
                        contadores_por_conta[conta_pasta] += 1
                    except Exception as e:
                        tipo_label = "congresso" if modo_congresso else "curso"
                        status_visual(f"Erro no {tipo_label} '{nome_curso}': {e}", "error")
        
        if arquivos_criados > 0:
            st.session_state["zip_gerado"] = zip_buffer.getvalue()
            st.session_state["zip_nome"] = f"automacao_cess_{data_semana.replace('/','-')}.zip"
            st.session_state["arquivos_criados"] = arquivos_criados
            status_visual(f"🚀 {arquivos_criados} arquivos processados.", "success")
        else:
            status_visual("Nenhum arquivo gerado.", "warning")

if "zip_gerado" in st.session_state:
    st.divider()
    st.subheader("Download")
    status_visual(f"✅ Pronto! {st.session_state.get('arquivos_criados', 0)} arquivos estão preparados para baixar.", "success")
    st.download_button(
        label="⬇️ Baixar Arquivos (.ZIP)",
        data=st.session_state["zip_gerado"],
        file_name=st.session_state.get("zip_nome", "automacao_cess.zip"),
        mime="application/zip",
        use_container_width=True
    )

st.markdown("""<div class="cess-footer"><strong>CESS Automation System</strong><span>2026</span><div>Versão Web Estável</div></div>""", unsafe_allow_html=True)
st.caption("CESS Automation System 2026 - Versão Web Estável")
