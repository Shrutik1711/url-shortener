from flask import Blueprint, jsonify, redirect, request
from sqlalchemy.exc import IntegrityError

from . import db
from .models import Link
from .utils import (
    generate_short_code,
    is_valid_alias,
    is_valid_url,
    iso,
    parse_expiry,
    utcnow,
)

bp = Blueprint("main", __name__)


def error(status, message):
    return jsonify({"error": message}), status

def save_link(code, original_url, expires_at):
    
    link = Link(code=code, original_url=original_url, expires_at=expires_at)
    db.session.add(link)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return None
    return link


@bp.route("/ping")
def ping():
    return {"status": "ok"}


@bp.route("/links", methods=["POST"])
def create_link():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return error(400, "Request body must be a JSON object")

    original_url = data.get("original_url")
    custom_alias = data.get("custom_alias")
    expires_at_str = data.get("expires_at")  

  
    if not is_valid_url(original_url):
        return error(400, "Invalid URL. Must be a valid http/https URL.")

    
    if custom_alias is not None and not is_valid_alias(custom_alias):
        return error(
            400,
            "Invalid alias. Use 3-32 letters, digits, '-' or '_' "
            "(and not a reserved word like 'links').",
        )

    expires_at = None
    if expires_at_str is not None:
        try:
            expires_at = parse_expiry(expires_at_str)
        except ValueError:
            return error(400, "Invalid expires_at. Use ISO format, e.g. 2026-12-31T23:59:59Z")
        if expires_at <= utcnow():
            return error(400, "expires_at must be in the future")

    if custom_alias is not None:
        link = save_link(custom_alias, original_url, expires_at)
        if link is None:
            return error(
                409,
                f"Alias '{custom_alias}' is already in use. "
                "Choose a different alias or leave it out to get a generated code.",
            )
    else:
        link = None
        for _ in range(5): 
            link = save_link(generate_short_code(), original_url, expires_at)
            if link is not None:
                break
        if link is None:
            return error(503, "Could not generate a unique code, please try again")

    return jsonify({
        "short_code": link.code,
        "short_url": f"{request.host_url}{link.code}",
        "original_url": link.original_url,
        "expires_at": iso(link.expires_at),
    }), 201


@bp.route("/<code>", methods=["GET"])
def redirect_link(code):
    link = Link.query.filter_by(code=code).first()

    if not link:
        return error(404, f"Short code '{code}' not found")


    now = utcnow()
    if link.is_expired(now):
        return error(410, f"This link expired at {iso(link.expires_at)}")


    target = link.original_url
    Link.query.filter_by(code=code).update(
        {Link.click_count: Link.click_count + 1, Link.last_clicked_at: now}
    )
    db.session.commit()

    response = redirect(target, code=307)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.route("/links/<code>/stats", methods=["GET"])
def get_stats(code):
    link = Link.query.filter_by(code=code).first()
    if not link:
        return error(404, f"Short code '{code}' not found")

    return jsonify({
        "short_code": link.code,
        "original_url": link.original_url,
        "total_clicks": link.click_count,
        "last_clicked_at": iso(link.last_clicked_at),
        "created_at": iso(link.created_at),
        "expires_at": iso(link.expires_at),
        "expired": link.is_expired(utcnow()),
    })