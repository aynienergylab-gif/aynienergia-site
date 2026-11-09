# Versões em espanhol e inglês

O site tem uma **fonte única em português** (`index.html`, `portfolio.html`, `producao.html`, `analises.html`).
As versões `/es/` e `/en/` são geradas a partir dela, com a mesma marcação e o mesmo CSS, e os textos
traduzidos ficam em dois arquivos:

| Arquivo | Conteúdo |
|---|---|
| `_i18n/es.json` | Espanhol (voz colombiana, tratamento de "usted") |
| `_i18n/en.json` | Inglês (ortografia americana) |
| `_i18n/revisao.csv` | Tabela lado a lado PT / ES / EN para revisar no Excel ou no Google Planilhas |
| `_i18n/build.py` | Gerador (Python 3, sem dependências externas) |

A pasta começa com `_` de propósito: o GitHub Pages não publica pastas assim.

## Como editar um texto

1. Altere o texto **em português** na página `.html` correspondente.
2. Rode `python3 _i18n/build.py`. Se o texto mudou, o script avisa que falta a tradução daquele trecho.
3. Acrescente (ou ajuste) a linha correspondente em `es.json` e `en.json`. A chave é o texto em português.
4. Rode de novo. Quando termina com `OK`, as páginas `/es/` e `/en/` estão atualizadas.

Para corrigir só a tradução, edite o valor em `es.json` ou `en.json` e rode `python3 _i18n/build.py`.
**Não edite os HTML de `es/` e `en/` à mão**: a próxima execução os sobrescreve.

## Estrutura dos arquivos `.json`

- `textos`: `"texto em português": "tradução"`. Quando a mesma palavra muda de sentido conforme o lugar,
  a chave leva o contexto: `"Atuação @nav-lista"` (item do menu) e `"Atuação @pf-atuacao"` (papel em cada caso).
- `manter`: textos que ficam iguais (nomes próprios, siglas, e-mail).
- `inserir`: avisos que só existem nas versões traduzidas (por exemplo, "documentos em português").

Valores com `<span lang='pt-BR'>…</span>` marcam trechos em português dentro da página traduzida
(títulos de documentos e publicações do LinkedIn, que não são traduzidos). Isso ajuda leitores de tela.

## O que o gerador faz sozinho

- Copia o HTML original e troca textos e atributos (`alt`, `aria-label`, `title`, metadados).
- Ajusta `<html lang>`, `canonical`, `og:url`, `og:locale` e os caminhos para `assets/`, `styles.css` e `script.js`.
- Mantém o bloco de `hreflang` e o seletor **PT | ES | EN** em todas as páginas, inclusive as em português.
- Gera `sitemap.xml` (com as alternativas de idioma) e cria `robots.txt` se ele não existir.
- Falha se faltar tradução ou se sobrar uma chave sem uso, para nada ficar em português por descuido.

## Decisões a conferir

- **Nome**: mantido como "Maria José" nas três versões. Para usar "María José" em espanhol, altere as entradas
  do nome em `_i18n/es.json` (lista `manter` e os textos que o contêm).
- **Código de idioma**: `hreflang="es"` (espanhol em geral). O Google não aceita `es-419`.
- **PDF do portfólio**: está em português e os botões avisam isso. Quando houver versões traduzidas, troque o
  link e retire o aviso nas entradas "Descargar el portafolio…" e "Download the portfolio…".
- **Imagem de compartilhamento** (`assets/og-ayni.png`): o texto dentro da imagem está em português.
- **Publicações do LinkedIn**: ficam em português, com aviso na página do blog.
