# Reading Map

Where each area of this project lives. bee-capturing owns this file: it is
updated whenever an area spec is created or moved. Read this before any broad
search — it answers "where does X live" without a grep.

| Area | Spec | Code entry points |
|---|---|---|
| Trang hướng dẫn Forbidden Memories | `docs/specs/guide-site.md` | `index.html` (dữ liệu nhúng giữa `/* FM_DATA:BEGIN */` và `/* FM_DATA:END */`), `tools/extract_cards.py`, `tools/check.py` |
| Nguồn dữ liệu bài | `docs/specs/guide-site.md` § Nguồn dữ liệu và ranh giới | `data/cards.json`, `scripts/fetch_yugipedia_cards.py`, `images/cards/` |
| Nguồn nội dung hướng dẫn | `docs/specs/guide-site.md` § Hướng dẫn, § Fusion | `docs/guide/*.md` (3 file tiếng Việt, chỉ đọc) |
