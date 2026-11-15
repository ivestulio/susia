"""Base de conhecimento CID-10: le o PDF, indexa as categorias e faz a busca semantica."""

import re
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from pypdf import PdfReader

from src.services.llm import RAIZ, embeddings

PDF_CID10 = RAIZ / "CID-10.pdf"
ARQUIVO_INDICE = RAIZ / ".cache" / "cid10_index.json"

# Uma categoria por linha: codigo de 3 caracteres e, em geral, a descricao ("A00 Colera").
LINHA_CATEGORIA = re.compile(r"^([A-Z]\d{2})(?:\s+(.+))?$")

# Linhas de cabecalho que se repetem nas paginas e nao fazem parte de nenhuma categoria.
CABECALHOS = (
    "Código Descrição do CID",
    "Classificação Internacional de Doenças",
    "Versão 2008",
    "Saúde: www.datasus",
    "Sergipe",
)


# As ligaduras "fi" e "fl" do PDF sao extraidas como o mesmo caractere nulo
# ("classi\x00cadas", "in\x00amatorios"). Estes sao os trechos em que ele vale "fl";
# em todos os outros vale "fi".
TRECHOS_FL = ("n\x00a", "n\x00u", "n\x00i", "trombo\x00e", "re\x00u", "a\x00at", "ri\x00e")


def _restaurar_ligaduras(texto: str) -> str:
    for trecho in TRECHOS_FL:
        texto = texto.replace(trecho, trecho.replace("\x00", "fl"))
    return texto.replace("\x00", "fi")


def carregar_categorias() -> list[Document]:
    """Le o PDF e devolve um Document por categoria do CID-10."""
    texto = "\n".join(pagina.extract_text() for pagina in PdfReader(PDF_CID10).pages)
    texto = _restaurar_ligaduras(texto)

    categorias: list[list[str]] = []  # [codigo, descricao]
    for linha in texto.splitlines():
        linha = linha.strip()
        if not linha or linha.startswith(CABECALHOS):
            continue
        achado = LINHA_CATEGORIA.match(linha)
        if achado:
            categorias.append([achado.group(1), achado.group(2) or ""])
        elif categorias:
            # Descricao longa quebrada em mais de uma linha: continua a categoria anterior.
            categorias[-1][1] = f"{categorias[-1][1]} {linha}".strip()

    return [
        Document(
            page_content=f"{codigo} {descricao}",
            metadata={"codigo": codigo, "descricao": descricao},
        )
        for codigo, descricao in categorias
    ]


@lru_cache(maxsize=1)
def indice() -> InMemoryVectorStore:
    """O indice vetorial do CID-10: gerado na primeira vez, depois lido do disco."""
    if ARQUIVO_INDICE.exists():
        return InMemoryVectorStore.load(str(ARQUIVO_INDICE), embeddings())

    store = InMemoryVectorStore(embeddings())
    store.add_documents(carregar_categorias())
    ARQUIVO_INDICE.parent.mkdir(exist_ok=True)
    store.dump(str(ARQUIVO_INDICE))
    return store


def buscar(consulta: str, k: int = 5) -> list[dict[str, str]]:
    """As k categorias do CID-10 mais proximas da consulta."""
    return [doc.metadata for doc in indice().similarity_search(consulta, k=k)]
