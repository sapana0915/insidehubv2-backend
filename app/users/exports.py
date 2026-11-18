import io
from pathlib import Path
from xhtml2pdf import pisa  # or weasyprint

from app.core.config import settings

def build_user_portfolio_pdf(user, posts) -> bytes:
    parts = [
        f"<h1>InsideHub export</h1>",
        f"<p>{user.full_name or user.username} · {user.email}</p>",
        f"<p>Exported posts: {len(posts)}</p><hr/>",
    ]
    if not posts:
        parts.append("<p>No posts or photos to export yet.</p>")
    for post in posts:
        parts.append(f"<h2>{post.title or '(Photography)'}</h2>")
        parts.append(f"<p><em>{post.category} · {post.created_at.date()}</em></p>")
        parts.append(post.content or "")
        for img in post.images:
            # map /media/foo.jpg → media/foo.jpg on disk
            rel = img.image_url.lstrip("/")
            if rel.startswith("media/"):
                path = Path(settings.MEDIA_DIR) / Path(rel).relative_to("media")
                if path.exists():
                    parts.append(f'<img src="{path.resolve().as_uri()}" width="400"/>')
            if img.place_name:
                parts.append(f"<p>{img.place_name}</p>")
        parts.append("<hr/>")

    html = f"<html><body>{''.join(parts)}</body></html>"
    out = io.BytesIO()
    pisa.CreatePDF(html, dest=out)  # weasyprint: HTML(string=html).write_pdf()
    return out.getvalue()
