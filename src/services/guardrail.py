"""Guardrail de entrada: verifica o prontuario antes de qualquer chamada ao modelo.

A verificacao e deterministica (expressoes regulares, sem LLM): e rapida, nao custa
chamadas e nao pode ser enganada por uma instrucao escrita no proprio prontuario.

- Segredos (chaves de API, tokens, chaves privadas): mascarados.
- PII (CPF, CNS, e-mail, telefone etc.): mascarados.
- Injecao de prompt: bloqueia o prontuario.
- Prontuario vazio ou grande demais: bloqueia.

Os achados guardam so o tipo, a regra e a quantidade: o valor encontrado nunca e
copiado para o state, para nao vazar o dado que o guardrail acabou de esconder.
"""

import re
import unicodedata
from collections import Counter
from collections.abc import Callable

from src.state import AchadoGuardrail, ResultadoGuardrail

TAMANHO_MAXIMO = 20_000  # caracteres

# --------------------------------------------------------------------------------------
# Segredos: (regra, padrao). Substituidos por "[SEGREDO]".
# --------------------------------------------------------------------------------------
PADROES_SEGREDO: list[tuple[str, re.Pattern[str]]] = [
    ("chave_privada", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S)),
    ("chave_openai", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}")),
    ("chave_langsmith", re.compile(r"\blsv2_(?:pt|sk)_[A-Za-z0-9_]{20,}")),
    ("chave_aws", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("token_github", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("chave_google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("token_slack", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("string_conexao", re.compile(
        r"\b(?:AccountKey|SharedAccessKey|Password|Pwd)=[^;\s]{8,}", re.I)),
    # "api_key = ...", "senha: ...", "token=..."
    ("atribuicao_segredo", re.compile(
        r"\b(?:api[_-]?key|apikey|secret|client[_-]?secret|senha|password|passwd|token)"
        # (?!\[SEGREDO\]): o valor ja pode ter sido mascarado por uma regra anterior.
        r"\s*[:=]\s*[\"']?(?!\[SEGREDO\])[^\s\"']{6,}", re.I)),
    # Sequencia longa sem espacos, misturando letras e digitos (chaves do Azure etc.).
    ("token_longo", re.compile(r"\b(?=[A-Za-z0-9+/_-]*\d)(?=[A-Za-z0-9+/_-]*[A-Za-z])[A-Za-z0-9+/_-]{40,}={0,2}")),
]

# --------------------------------------------------------------------------------------
# PII: (regra, padrao, marcador, validador opcional). Quando o padrao tem o grupo
# "valor", so ele e mascarado e o rotulo fica ("Paciente: [NOME]").
# --------------------------------------------------------------------------------------


def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


def _cpf_valido(texto: str) -> bool:
    d = _digitos(texto)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for tamanho in (9, 10):
        soma = sum(int(d[i]) * (tamanho + 1 - i) for i in range(tamanho))
        if (soma * 10 % 11) % 10 != int(d[tamanho]):
            return False
    return True


def _cns_valido(texto: str) -> bool:
    """Cartao Nacional de Saude: 15 digitos, soma ponderada multipla de 11."""
    d = _digitos(texto)
    if len(d) != 15 or d[0] not in "12789":
        return False
    return sum(int(c) * (15 - i) for i, c in enumerate(d)) % 11 == 0


PADROES_PII: list[tuple[str, re.Pattern[str], str, Callable[[str], bool] | None]] = [
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"), "[EMAIL]", None),
    ("cnpj", re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "[CNPJ]", None),
    ("cpf", re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]", _cpf_valido),
    ("cns", re.compile(r"\b[12789]\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\b"), "[CNS]", _cns_valido),
    ("rg", re.compile(r"\bRG\b\s*(?:n[º°o.]?\s*)?[:\-]?\s*(?P<valor>[\d.\-]{5,12}[\dxX]?)", re.I), "[RG]", None),
    ("telefone", re.compile(
        r"(?:\+55\s?)?(?:\(\d{2}\)\s?|\b\d{2}\s)9?\d{4}[-\s]?\d{4}\b"), "[TELEFONE]", None),
    ("cep", re.compile(r"\b\d{5}-\d{3}\b"), "[CEP]", None),
    ("data_nascimento", re.compile(
        r"\b(?:nascid[oa]\s+em|data\s+de\s+nascimento|DN)\s*:?\s*(?P<valor>\d{1,2}/\d{1,2}/\d{2,4})", re.I),
     "[DATA_NASCIMENTO]", None),
    # Nome so quando rotulado ("Paciente: Joao da Silva"): sem rotulo, regex nao
    # distingue nome proprio de termo medico.
    ("nome", re.compile(
        # Rotulo sem diferenciar maiusculas; o nome em si precisa comecar com maiuscula.
        r"\b(?i:nome|paciente|m[aã]e|pai|respons[aá]vel)\s*:\s*"
        r"(?P<valor>[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+(?:\s+(?:d[aeo]s?\s+)?[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+)+)"),
     "[NOME]", None),
]

# --------------------------------------------------------------------------------------
# Injecao de prompt: aplicada ao texto normalizado (minusculo, sem acentos).
# --------------------------------------------------------------------------------------
PADROES_INJECAO: list[tuple[str, re.Pattern[str]]] = [
    ("ignorar_instrucoes", re.compile(
        r"\b(?:ignor\w*|desconsider\w*|esquec\w*|disregard|forget)\s+(?:\w+\s+){0,3}?"
        r"(?:instruc\w*|regras|ordens|prompt|instructions|rules|tudo\s+(?:o\s+que|acima))")),
    ("troca_de_papel", re.compile(
        r"\b(?:voce\s+agora\s+e|a\s+partir\s+de\s+agora\s+voce|you\s+are\s+now|act\s+as|"
        r"aja\s+como|finja\s+(?:ser|que)|pretend\s+(?:to\s+be|you))\b")),
    ("prompt_do_sistema", re.compile(
        r"\b(?:system\s+prompt|developer\s+message|(?:prompt|instrucoes|mensagem)\s+do\s+sistema|"
        r"(?:revele|mostre|repita|imprima)\s+(?:\w+\s+){0,3}?(?:prompt|instrucoes))\b")),
    ("marcador_de_papel", re.compile(
        r"<\|?(?:im_start|im_end|system|assistant|user)\|?>|\[/?inst\]|</?system>|"
        r"^\s*#{2,}\s*(?:system|sistema|instruc\w*)\b", re.M)),
    ("jailbreak", re.compile(r"\b(?:jailbreak|modo\s+desenvolvedor|developer\s+mode|\bdan\s+mode)\b")),
    # Instrucoes dirigidas aos agentes deste sistema: um prontuario descreve o paciente,
    # nao diz ao modelo como classificar ou responder.
    ("manipular_triagem", re.compile(
        r"\b(?:classifique|classifica|considere|marque|trate)\s+(?:\w+\s+){0,3}?"
        r"(?:como\s+)?(?:nao\s+urgente|urgente|nao_urgente|cardiolog\w*|neurolog\w*|geral)\b")),
    ("manipular_resposta", re.compile(
        r"\b(?:responda|retorne|devolva)\s+(?:apenas|somente|so)\b|"
        r"\bnao\s+(?:use|chame|utilize|consulte)\s+(?:a\s+)?(?:ferramenta|tool|buscar_cid10)\b|"
        r"\b(?:sugira|use|coloque|informe)\s+(?:o\s+)?(?:cid|codigo)\s+[a-z]\d{2}\b")),
]


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


def _mascarar_segredos(texto: str, contagem: Counter) -> str:
    for regra, padrao in PADROES_SEGREDO:
        texto, n = padrao.subn("[SEGREDO]", texto)
        if n:
            contagem[("segredo", regra)] += n
    return texto


def _mascarar_pii(texto: str, contagem: Counter) -> str:
    for regra, padrao, marcador, valido in PADROES_PII:
        def trocar(achado: re.Match[str]) -> str:
            if valido and not valido(achado.group(0)):
                return achado.group(0)
            contagem[("pii", regra)] += 1
            if "valor" in achado.re.groupindex:
                inicio, fim = achado.span("valor")
                base = achado.start()
                trecho = achado.group(0)
                return trecho[: inicio - base] + marcador + trecho[fim - base :]
            return marcador

        texto = padrao.sub(trocar, texto)
    return texto


def verificar_prontuario(prontuario: str) -> tuple[str, ResultadoGuardrail]:
    """Devolve o prontuario sanitizado e o resultado da verificacao."""
    if not prontuario or not prontuario.strip():
        return prontuario, ResultadoGuardrail(
            bloqueado=True, motivo="Prontuario vazio",
            achados=[AchadoGuardrail(tipo="tamanho", regra="vazio", quantidade=1)],
        )
    if len(prontuario) > TAMANHO_MAXIMO:
        return "", ResultadoGuardrail(
            bloqueado=True, motivo=f"Prontuario com mais de {TAMANHO_MAXIMO} caracteres",
            achados=[AchadoGuardrail(tipo="tamanho", regra="tamanho_maximo", quantidade=1)],
        )

    contagem: Counter = Counter()
    # Segredos antes de PII: um token longo nao deve ser lido como telefone ou CPF.
    sanitizado = _mascarar_segredos(prontuario, contagem)
    sanitizado = _mascarar_pii(sanitizado, contagem)

    normalizado = _normalizar(prontuario)
    for regra, padrao in PADROES_INJECAO:
        n = len(padrao.findall(normalizado))
        if n:
            contagem[("injecao", regra)] += n

    achados = [
        AchadoGuardrail(tipo=tipo, regra=regra, quantidade=n)
        for (tipo, regra), n in contagem.items()
    ]
    injecoes = sorted(a.regra for a in achados if a.tipo == "injecao")
    if injecoes:
        # Bloqueado: nada segue para o modelo, nem a versao sanitizada.
        return "", ResultadoGuardrail(
            bloqueado=True,
            motivo="Possivel injecao de prompt: " + ", ".join(injecoes),
            achados=achados,
        )
    return sanitizado, ResultadoGuardrail(bloqueado=False, motivo=None, achados=achados)
