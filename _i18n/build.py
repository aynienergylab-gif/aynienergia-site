#!/usr/bin/env python3
"""Gera as versões em espanhol (/es/) e inglês (/en/) a partir das páginas em português.

As páginas em português são a fonte. Os textos traduzidos ficam em _i18n/es.json e
_i18n/en.json (chave = texto em português). O script copia o HTML original byte a byte e
só reescreve: textos e atributos traduzíveis, caminhos relativos, <html lang>, canonical,
hreflang, og:locale, o seletor de idioma e os avisos de idioma.

Uso (a partir da raiz do repositório):
    python3 _i18n/build.py            gera /es, /en, sitemap.xml e atualiza hreflang/seletor em PT
    python3 _i18n/build.py --dump     lista os textos extraídos (para conferir ou traduzir)
    python3 _i18n/build.py --csv      gera _i18n/revisao.csv (PT | ES | EN lado a lado)

Falha (código 1) se algum texto não tiver tradução, ou se houver chaves sem uso.
"""
import csv
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "_i18n"
SITE = "https://aynienergia.com.br"

LANGS = ["pt", "es", "en"]
PREFIX = {"pt": "", "es": "es/", "en": "en/"}
HREFLANG = {"pt": "pt-BR", "es": "es", "en": "en"}
LANG_ATTR = {"pt": "pt-BR", "es": "es", "en": "en"}
OG_LOCALE = {"pt": "pt_BR", "es": "es_CO", "en": "en_US"}
LANG_NAME = {"pt": "Português", "es": "Español", "en": "English"}
LANG_BUTTON = {"pt": "PT", "es": "ES", "en": "EN"}
SWITCH_LABEL = {"pt": "Idioma", "es": "Idioma", "en": "Language"}

# chave da página -> nome do arquivo em cada idioma
SLUGS = {
    "pt": {"inicio": "index.html", "portfolio": "portfolio.html", "producao": "producao.html", "blog": "analises.html"},
    "es": {"inicio": "index.html", "portfolio": "portafolio.html", "producao": "produccion.html", "blog": "blog.html"},
    "en": {"inicio": "index.html", "portfolio": "portfolio.html", "producao": "production.html", "blog": "blog.html"},
}
PT_TO_KEY = {v: k for k, v in SLUGS["pt"].items()}

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
TR_ATTRS = {"alt", "aria-label", "title", "placeholder",
            "data-rotulo-abrir", "data-rotulo-fechar", "data-rotulo-caso", "data-rotulo-todos", "data-rotulo-navegar"}
META_TR = {("name", "description"), ("name", "twitter:title"), ("name", "twitter:description"),
           ("property", "og:title"), ("property", "og:description"), ("property", "og:image:alt")}
PATH_ATTRS = {"href", "src", "srcset", "poster"}
ABSOLUTE = re.compile(r"^(?:[a-z][a-z0-9+.\-]*:|//|#)", re.I)
HAS_LETTER = re.compile(r"[^\W\d_]")


# ----------------------------------------------------------------------------------------
# Léxico: tokens com posição exata no texto original (nada é reserializado)
# ----------------------------------------------------------------------------------------
class Tok:
    def __init__(self, kind, start, tag=None, attrs=None, self_close=False, data=None):
        self.kind, self.start, self.tag, self.attrs = kind, start, tag, attrs
        self.self_close, self.data = self_close, data
        self.end = self.raw = self.stack = None

    def attr(self, name, default=None):
        for k, v in self.attrs or []:
            if k == name:
                return v
        return default


class Lexer(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.toks = []
        self.line_starts = [0] + [m.end() for m in re.finditer("\n", src)]

    def _pos(self):
        line, col = self.getpos()
        return self.line_starts[line - 1] + col

    def handle_starttag(self, tag, attrs):
        self.toks.append(Tok("start", self._pos(), tag=tag, attrs=attrs))

    def handle_startendtag(self, tag, attrs):
        self.toks.append(Tok("start", self._pos(), tag=tag, attrs=attrs, self_close=True))

    def handle_endtag(self, tag):
        self.toks.append(Tok("end", self._pos(), tag=tag))

    def handle_data(self, data):
        self.toks.append(Tok("data", self._pos(), data=data))

    def handle_comment(self, data):
        self.toks.append(Tok("comment", self._pos(), data=data))

    def handle_decl(self, decl):
        self.toks.append(Tok("decl", self._pos()))

    def handle_pi(self, data):
        self.toks.append(Tok("decl", self._pos()))

    def unknown_decl(self, data):
        self.toks.append(Tok("decl", self._pos()))


def lex(src, nome):
    lx = Lexer(src)
    lx.feed(src)
    lx.close()
    toks = lx.toks
    assert toks and toks[0].start == 0, f"{nome}: o documento não começa com um token"
    for i, t in enumerate(toks):
        t.end = toks[i + 1].start if i + 1 < len(toks) else len(src)
        t.raw = src[t.start:t.end]
    assert "".join(t.raw for t in toks) == src, f"{nome}: os tokens não reconstroem o original"
    stack = []
    for t in toks:
        t.stack = tuple(stack)
        if t.kind == "start" and not t.self_close and t.tag not in VOID:
            stack.append(t)
        elif t.kind == "end":
            for j in range(len(stack) - 1, -1, -1):
                if stack[j].tag == t.tag:
                    del stack[j:]
                    break
    assert not stack, f"{nome}: elementos sem fechamento: {[s.tag for s in stack]}"
    return toks


# ----------------------------------------------------------------------------------------
# Traduções
# ----------------------------------------------------------------------------------------
class Dict:
    def __init__(self, lang):
        self.lang = lang
        self.path = I18N / f"{lang}.json"
        data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        self.manter = set(data.get("manter", []))
        self.textos = data.get("textos", {})
        self.inserir = data.get("inserir", {})
        self.used = set()

    def lookup(self, text, ctx):
        if text in self.manter:
            self.used.add(("manter", text))
            return text
        for k in ((f"{text} @{ctx}" if ctx else None), text):
            if k and k in self.textos:
                self.used.add(("textos", k))
                return self.textos[k]
        return None


def has_letters(s):
    # também conta números com vírgula decimal (9,8%), que mudam de formato em inglês
    return bool(HAS_LETTER.search(s)) or bool(re.search(r"\d,\d", s))


def norm(s):
    return " ".join(s.split())


def first_class(tok):
    c = (tok.attr("class") or "").split()
    return c[0] if c else None


def ctx_of(stack, own=None):
    if own is not None and first_class(own):
        return first_class(own)
    for a in reversed(stack):
        if first_class(a):
            return first_class(a)
    return None


def skipped(stack, own=None):
    chain = list(stack) + ([own] if own is not None else [])
    for a in chain:
        if a.tag in ("script", "style"):
            return True
        if (a.attr("lang") or "").lower().startswith("en"):
            return True
        if a.attr("translate") == "no":
            return True
        if a.tag == "li" and "nav-idioma" in (a.attr("class") or "").split():
            return True
    return False


def esc_text(v):
    return v.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def esc_attr(v):
    return v.replace("&", "&amp;").replace('"', "&quot;")


def render_value(v):
    # valores com marcação (ex.: <span lang="pt-BR">…</span>) entram como HTML; o resto é texto
    return v if "<" in v else esc_text(v)


def render_start(tag, attrs, self_close):
    parts = [tag]
    for k, v in attrs:
        parts.append(k if v is None else f'{k}="{esc_attr(v)}"')
    return "<" + " ".join(parts) + (" />" if self_close else ">")


# ----------------------------------------------------------------------------------------
# URLs
# ----------------------------------------------------------------------------------------
def page_rel(lang, key):
    return PREFIX[lang] + SLUGS[lang][key]


def page_abs(lang, key):
    return SITE + "/" + (PREFIX[lang] if key == "inicio" else page_rel(lang, key))


def rel_link(from_lang, to_lang, key):
    start = PREFIX[from_lang].rstrip("/") or "."
    return os.path.relpath(page_rel(to_lang, key), start=start)


def map_href(v, lang):
    if v == "" or ABSOLUTE.match(v):
        return v
    path, rest = re.match(r"^([^?#]*)(.*)$", v).groups()
    if path in PT_TO_KEY:
        return SLUGS[lang][PT_TO_KEY[path]] + rest
    return "../" + v


def map_srcset(v, lang):
    out = []
    for cand in v.split(","):
        cand = cand.strip()
        if not cand:
            continue
        url, _, desc = cand.partition(" ")
        out.append((map_href(url, lang) + (" " + desc.strip() if desc.strip() else "")))
    return ", ".join(out)


# ----------------------------------------------------------------------------------------
# Blocos gerados
# ----------------------------------------------------------------------------------------
def switcher_html(lang, key):
    parts = [f'<li class="nav-idioma"><span class="visually-hidden">{SWITCH_LABEL[lang]}</span>']
    for L in LANGS:
        cur = ' aria-current="true"' if L == lang else ""
        parts.append(
            f'<a href="{rel_link(lang, L, key)}" hreflang="{HREFLANG[L]}" lang="{LANG_ATTR[L]}"{cur} '
            f'aria-label="{LANG_NAME[L]}" title="{LANG_NAME[L]}">{LANG_BUTTON[L]}</a>')
    parts.append("</li>")
    return "".join(parts)


def hreflang_block(lang, key, indent):
    lines = ["<!-- i18n:hreflang -->"]
    for L in LANGS:
        lines.append(f'<link rel="alternate" hreflang="{HREFLANG[L]}" href="{page_abs(L, key)}" />')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{page_abs("pt", key)}" />')
    for L in LANGS:
        if L != lang:
            lines.append(f'<meta property="og:locale:alternate" content="{OG_LOCALE[L]}" />')
    lines.append("<!-- /i18n:hreflang -->")
    return ("\n" + indent).join(lines)


def indent_before(toks, i):
    """Recuo (espaços após a última quebra de linha) do token anterior, se for só espaço."""
    if i > 0 and toks[i - 1].kind == "data" and not toks[i - 1].data.strip():
        return toks[i - 1].raw.split("\n")[-1]
    return ""


# ----------------------------------------------------------------------------------------
# Transformação de uma página
# ----------------------------------------------------------------------------------------
class Result:
    def __init__(self):
        self.missing = {}   # (texto, ctx) -> páginas
        self.units = []     # (página, tipo, ctx, texto) na ordem em que aparecem


def transform(src, key, lang, tr, res):
    """Devolve o HTML da página `key` no idioma `lang`. Em 'pt' só regenera os blocos gerados."""
    nome = SLUGS["pt"][key]
    toks = lex(src, nome)
    pt = lang == "pt"
    out = []

    has_marker = any(t.kind == "comment" and t.data.strip() == "i18n:hreflang" for t in toks)
    has_switch = any(t.kind == "start" and t.tag == "li" and "nav-idioma" in (t.attr("class") or "").split() for t in toks)

    def unit(kind, ctx, text):
        res.units.append((nome, kind, ctx, text))

    def tr_value(text, ctx):
        val = tr.lookup(text, ctx)
        if val is None:
            res.missing.setdefault((text, ctx), set()).add(nome)
        return val

    i = 0
    while i < len(toks):
        t = toks[i]

        # --- bloco hreflang entre marcadores ---
        if t.kind == "comment" and t.data.strip() == "i18n:hreflang":
            j = next(k for k in range(i, len(toks)) if toks[k].kind == "comment" and toks[k].data.strip() == "/i18n:hreflang")
            out.append(hreflang_block(lang, key, indent_before(toks, i)))
            i = j + 1
            continue

        # --- avisos de idioma (só ES/EN) ---
        if t.kind == "comment" and t.data.strip().startswith("i18n:nota"):
            if pt:
                out.append(t.raw)
            else:
                html = tr.inserir.get(t.data.strip().split(":", 1)[1])
                if html:
                    tr.used.add(("inserir", t.data.strip().split(":", 1)[1]))
                    out.append(html)
            i += 1
            continue

        if t.kind == "start":
            # --- seletor de idioma: substitui (ou insere depois de .nav-contato) ---
            cls = (t.attr("class") or "").split()
            if t.tag == "li" and "nav-idioma" in cls:
                j = next(k for k in range(i + 1, len(toks)) if toks[k].kind == "end" and toks[k].tag == "li")
                out.append(switcher_html(lang, key))
                i = j + 1
                continue
            if t.tag == "li" and "nav-contato" in cls and not has_switch:
                j = next(k for k in range(i + 1, len(toks)) if toks[k].kind == "end" and toks[k].tag == "li")
                ind = indent_before(toks, i)
                out.append("".join(x.raw for x in toks[i:j + 1]))
                out.append("\n" + ind + switcher_html(lang, key))
                i = j + 1
                continue

            # --- hreflang: se ainda não há marcadores, entram depois do canonical ---
            is_canonical = t.tag == "link" and t.attr("rel") == "canonical"
            attrs = list(t.attrs)
            new = []
            for k, v in attrs:
                nv = v
                if v is not None and not pt:
                    if t.tag == "html" and k == "lang":
                        nv = LANG_ATTR[lang]
                    elif is_canonical and k == "href":
                        nv = page_abs(lang, key)
                    elif t.tag == "meta" and k == "content" and t.attr("property") == "og:url":
                        nv = page_abs(lang, key)
                    elif t.tag == "meta" and k == "content" and t.attr("property") == "og:locale":
                        nv = OG_LOCALE[lang]
                    elif t.tag == "meta" and k == "content" and any(t.attr(a) == b for a, b in META_TR):
                        if has_letters(v):
                            ctx = "meta"
                            unit("meta", ctx, norm(v))
                            r = tr_value(norm(v), ctx)
                            nv = r if r is not None else v
                    elif k in TR_ATTRS and has_letters(v) and not skipped(t.stack, t):
                        ctx = ctx_of(t.stack, t)
                        unit("attr:" + k, ctx, norm(v))
                        r = tr_value(norm(v), ctx)
                        nv = r if r is not None else v
                    elif k in PATH_ATTRS and not is_canonical:
                        if t.tag == "link" and t.attr("rel") == "alternate":
                            pass
                        else:
                            nv = map_srcset(v, lang) if k == "srcset" else map_href(v, lang)
                    elif k == "style" and "url(" in v:
                        raise SystemExit(f"{nome}: atributo style com url() não é tratado: {v}")
                new.append((k, nv))
            if new != attrs:
                out.append(render_start(t.tag, new, t.self_close))
            else:
                out.append(t.raw)
            if is_canonical and not has_marker:
                out.append("\n" + indent_before(toks, i) + hreflang_block(lang, key, indent_before(toks, i)))
            i += 1
            continue

        if t.kind == "data" and not pt:
            parent = t.stack[-1] if t.stack else None
            if parent is not None and parent.tag == "style":
                out.append(re.sub(r"url\((['\"]?)(assets/)", r"url(\1../\2", t.raw))
                i += 1
                continue
            text = norm(t.data)
            if text and has_letters(text) and not skipped(t.stack):
                ctx = ctx_of(t.stack)
                unit("text", ctx, text)
                val = tr_value(text, ctx)
                if val is not None:
                    lead = re.match(r"^(?:\s|&nbsp;|&#160;)*", t.raw).group(0)
                    trail = re.search(r"(?:\s|&nbsp;|&#160;)*$", t.raw).group(0)
                    out.append(lead + render_value(val) + trail)
                    i += 1
                    continue
            out.append(t.raw)
            i += 1
            continue

        out.append(t.raw)
        i += 1

    return "".join(out)


# ----------------------------------------------------------------------------------------
# Sitemap e robots
# ----------------------------------------------------------------------------------------
def sitemap():
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for L in LANGS:
        for key in SLUGS["pt"]:
            linhas.append("  <url>")
            linhas.append(f"    <loc>{page_abs(L, key)}</loc>")
            for M in LANGS:
                linhas.append(f'    <xhtml:link rel="alternate" hreflang="{HREFLANG[M]}" href="{page_abs(M, key)}" />')
            linhas.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{page_abs("pt", key)}" />')
            linhas.append("  </url>")
    linhas.append("</urlset>")
    return "\n".join(linhas) + "\n"


# ----------------------------------------------------------------------------------------
# Principal
# ----------------------------------------------------------------------------------------
def main(argv):
    dump = "--dump" in argv
    want_csv = "--csv" in argv
    dicts = {L: Dict(L) for L in ("es", "en")}
    res = {L: Result() for L in ("es", "en")}
    changed = []

    # 1) português: só atualiza hreflang e seletor
    pt_src, pt_disk = {}, {}
    for key, nome in SLUGS["pt"].items():
        src = (ROOT / nome).read_text(encoding="utf-8")
        pt_disk[key] = src
        pt_src[key] = transform(src, key, "pt", None, Result())

    # 2) ES e EN
    outputs = {}
    for L in ("es", "en"):
        for key in SLUGS["pt"]:
            outputs[(L, key)] = transform(pt_src[key], key, L, dicts[L], res[L])

    if dump:
        vistos = {}
        for (nome, kind, ctx, text) in res["es"].units:
            vistos.setdefault(text, []).append((nome, kind, ctx))
        print(f"# {len(vistos)} textos únicos")
        for text, ocs in vistos.items():
            ctxs = sorted({c or "-" for _, _, c in ocs})
            pags = sorted({n for n, _, _ in ocs})
            print(f"{json.dumps(text, ensure_ascii=False)}  # {','.join(p.split('.')[0] for p in pags)} | ctx={'/'.join(ctxs)} | {len(ocs)}x")
        return 0

    erro = False
    for L in ("es", "en"):
        if res[L].missing:
            erro = True
            print(f"\n[{L}] {len(res[L].missing)} texto(s) sem tradução em _i18n/{L}.json:")
            for (text, ctx), pags in sorted(res[L].missing.items(), key=lambda x: sorted(x[1])):
                print(f"  {json.dumps(text, ensure_ascii=False)}  (ctx={ctx}; {','.join(sorted(pags))})")
        usadas = dicts[L].used
        for k in list(dicts[L].textos):
            if ("textos", k) not in usadas:
                erro = True
                print(f"[{L}] chave sem uso (erro de digitação ou texto removido do PT?): {json.dumps(k, ensure_ascii=False)}")
        for k in dicts[L].manter:
            if ("manter", k) not in usadas:
                erro = True
                print(f"[{L}] item de 'manter' sem uso: {json.dumps(k, ensure_ascii=False)}")
    if erro:
        return 1

    for key, nome in SLUGS["pt"].items():
        if pt_src[key] != pt_disk[key]:
            (ROOT / nome).write_text(pt_src[key], encoding="utf-8")
            changed.append(nome)
    for (L, key), html in outputs.items():
        p = ROOT / PREFIX[L] / SLUGS[L][key]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(html, encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(sitemap(), encoding="utf-8")
    if not (ROOT / "robots.txt").exists():
        (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"OK: {len(outputs)} páginas geradas; português atualizado em: {', '.join(changed) or 'nada (já em dia)'}")

    if want_csv:
        pt_units = {}
        for (nome, kind, ctx, text) in res["es"].units:
            pt_units.setdefault((text, ctx), set()).add(nome)
        with open(I18N / "revisao.csv", "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Página", "Contexto", "Português (original)", "Español", "English", "Correção ES", "Correção EN", "Comentário"])
            for (text, ctx), pags in pt_units.items():
                es = dicts["es"].lookup(text, ctx)
                en = dicts["en"].lookup(text, ctx)
                w.writerow([", ".join(sorted(p.split(".")[0] for p in pags)), ctx or "", text, es, en, "", "", ""])
        print("CSV de revisão: _i18n/revisao.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
