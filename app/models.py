from . import db
from .utils import utcnow


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(32), unique=True, nullable=False)
    original_url = db.Column(db.String(2048), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    click_count = db.Column(db.Integer, default=0, nullable=False)
    last_clicked_at = db.Column(db.DateTime, nullable=True)

    def is_expired(self, now):
        return self.expires_at is not None and now >= self.expires_at