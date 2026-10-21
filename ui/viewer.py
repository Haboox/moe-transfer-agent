"""Built-in document viewer: a document opens in a window on the page, no download needed (the download stays).

PDF pages are drawn as images with pypdfium2 (no browser PDF plugin, so it looks the same in every browser and in
the online copy); photos (JPG, PNG) are shown as they are. Used by the parent portal and the staff portal.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from ui.i18n import t

MIME = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
MAX_PAGES = 8


@st.cache_data(max_entries=64, show_spinner=False)
def _pdf_pages(path: str, mtime: float) -> tuple[list[bytes], int]:
    """PNG images of the first pages of a PDF, and the page count. Cached per file version: mtime is part of the
    cache key (a name starting with _ would be left out of it), so a replaced file is drawn again."""
    _ = mtime
    import io

    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(path)
    try:
        total = len(pdf)
        out = []
        for i in range(min(total, MAX_PAGES)):
            img = pdf[i].render(scale=1.6).to_pil()
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            out.append(buf.getvalue())
        return out, total
    finally:
        pdf.close()


def _body(path: Path, file_name: str, lang: str, key: str) -> None:
    if not path.exists():
        st.warning(t("view_missing", lang))
        return
    data = path.read_bytes()
    suffix = path.suffix.lower()
    st.caption(file_name)
    if suffix == ".pdf":
        try:
            pages, total = _pdf_pages(str(path), path.stat().st_mtime)
        except Exception:  # noqa: BLE001 - a damaged or unusual file: offer the download instead
            pages, total = [], 0
        if not pages:
            st.info(t("view_cannot", lang))
        for i, png in enumerate(pages, 1):
            st.image(png, caption=t("view_page", lang, n=i, total=total), width="stretch")
        if total > MAX_PAGES:
            st.caption(t("view_more", lang, n=total - MAX_PAGES))
    elif suffix in (".jpg", ".jpeg", ".png"):
        st.image(data, width="stretch")
    else:
        st.info(t("view_cannot", lang))
    st.download_button(t("view_download", lang), data, file_name=file_name,
                       mime=MIME.get(suffix, "application/octet-stream"), icon=":material/download:",
                       width="stretch", key=f"vdl_{key}")


def open_document(path: Path, title: str, file_name: str, lang: str, key: str) -> None:
    """Open the viewer window for one document."""
    st.dialog(title, width="large")(_body)(path, file_name, lang, key)


def view_button(container, path: Path, title: str, file_name: str, lang: str, key: str, label: str | None = None) -> None:
    """A small View button that opens the document in the viewer window."""
    if container.button(label or t("view_btn", lang), key=f"view_{key}", icon=":material/visibility:",
                        type="tertiary", help=t("view_help", lang)):
        open_document(path, title, file_name, lang, key)
