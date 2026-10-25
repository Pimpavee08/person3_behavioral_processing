"""Canonical action/tool mapping for the AgentDojo v1 suites.

Every tool is described by properties of the tool itself (what it does, which
resource it touches, who authored the data it returns). The table was written
from the tool semantics only. It was NOT derived from the injection-vector
list, the attacker goals or the expected attack actions, so it can be used for
detector features without leaking the answer key.
"""
from __future__ import annotations

from typing import NamedTuple, Optional

from .descriptors import is_nonempty

TAXONOMY_VERSION = "p3-taxonomy-0.3"

READ, WRITE, UNKNOWN = "read", "write", "unknown"

# Who authored the content a read tool returns.
OWN = "own"                        # the user's own account / profile / system state
STRUCT = "third_party_structured"  # directories and listings: names, prices, addresses
FREE = "third_party_freetext"      # bodies written by other parties: mail, pages, files, reviews

ACTIONS = (
    "retrieve", "list", "search",                    # read
    "create", "update", "delete",                    # write, internal state
    "send_message", "transfer_value", "publish",     # write, leaves the user's boundary
    "reserve", "share", "admin",
)

DOMAINS = (
    "finance", "messaging", "email", "calendar", "file",
    "web", "travel", "account", "contact", "system",
)


class ToolSpec(NamedTuple):
    action: str
    effect: str
    domain: str
    source_trust: Optional[str]  # read tools only
    egress: bool       # transmits data/value to another party, or grants them access
    destructive: bool  # removes or revokes existing data/access
    mapped: bool       # False when the spec comes from the name-prefix fallback


def _r(action: str, domain: str, trust: str) -> ToolSpec:
    return ToolSpec(action, READ, domain, trust, False, False, True)


def _w(action: str, domain: str, egress: bool = False, destructive: bool = False) -> ToolSpec:
    return ToolSpec(action, WRITE, domain, None, egress, destructive, True)


TOOLS = {
    # ---- banking ----
    "get_iban": _r("retrieve", "account", OWN),
    "get_balance": _r("retrieve", "finance", OWN),
    "get_user_info": _r("retrieve", "account", OWN),
    "get_most_recent_transactions": _r("list", "finance", FREE),  # subjects are written by senders
    "get_scheduled_transactions": _r("list", "finance", OWN),
    "read_file": _r("retrieve", "file", FREE),
    "send_money": _w("transfer_value", "finance", egress=True),
    "schedule_transaction": _w("transfer_value", "finance", egress=True),
    "update_scheduled_transaction": _w("update", "finance", egress=True),  # alters an outbound transfer
    "update_password": _w("admin", "account"),
    "update_user_info": _w("admin", "account"),
    # ---- slack ----
    "get_channels": _r("list", "messaging", STRUCT),
    "get_users_in_channel": _r("list", "messaging", STRUCT),
    "read_channel_messages": _r("retrieve", "messaging", FREE),
    "read_inbox": _r("retrieve", "messaging", FREE),
    "get_webpage": _r("retrieve", "web", FREE),
    "send_direct_message": _w("send_message", "messaging", egress=True),
    "send_channel_message": _w("send_message", "messaging", egress=True),
    "post_webpage": _w("publish", "web", egress=True),
    "add_user_to_channel": _w("admin", "messaging", egress=True),
    "invite_user_to_slack": _w("admin", "messaging", egress=True),
    "remove_user_from_slack": _w("admin", "messaging", destructive=True),
    # ---- travel ----
    "get_user_information": _r("retrieve", "account", OWN),
    "get_all_hotels_in_city": _r("list", "travel", STRUCT),
    "get_hotels_prices": _r("retrieve", "travel", STRUCT),
    "get_rating_reviews_for_hotels": _r("retrieve", "travel", FREE),
    "get_hotels_address": _r("retrieve", "travel", STRUCT),
    "get_all_restaurants_in_city": _r("list", "travel", STRUCT),
    "get_cuisine_type_for_restaurants": _r("retrieve", "travel", STRUCT),
    "get_restaurants_address": _r("retrieve", "travel", STRUCT),
    "get_rating_reviews_for_restaurants": _r("retrieve", "travel", FREE),
    "get_dietary_restrictions_for_all_restaurants": _r("retrieve", "travel", STRUCT),
    "get_contact_information_for_restaurants": _r("retrieve", "travel", STRUCT),
    "get_price_for_restaurants": _r("retrieve", "travel", STRUCT),
    "check_restaurant_opening_hours": _r("retrieve", "travel", STRUCT),
    "get_all_car_rental_companies_in_city": _r("list", "travel", STRUCT),
    "get_car_types_available": _r("retrieve", "travel", STRUCT),
    "get_rating_reviews_for_car_rental": _r("retrieve", "travel", FREE),
    "get_car_fuel_options": _r("retrieve", "travel", STRUCT),
    "get_car_rental_address": _r("retrieve", "travel", STRUCT),
    "get_car_price_per_day": _r("retrieve", "travel", STRUCT),
    "get_flight_information": _r("retrieve", "travel", STRUCT),
    "reserve_hotel": _w("reserve", "travel"),
    "reserve_car_rental": _w("reserve", "travel"),
    "reserve_restaurant": _w("reserve", "travel"),
    # ---- shared by travel and workspace ----
    "send_email": _w("send_message", "email", egress=True),
    "search_calendar_events": _r("search", "calendar", FREE),  # descriptions written by organizers
    "get_day_calendar_events": _r("retrieve", "calendar", FREE),
    "create_calendar_event": _w("create", "calendar"),
    "cancel_calendar_event": _w("delete", "calendar", destructive=True),
    # ---- workspace ----
    "delete_email": _w("delete", "email", destructive=True),
    "get_unread_emails": _r("retrieve", "email", FREE),
    "get_received_emails": _r("retrieve", "email", FREE),
    "get_sent_emails": _r("retrieve", "email", OWN),
    "get_draft_emails": _r("retrieve", "email", OWN),
    "search_emails": _r("search", "email", FREE),
    "search_contacts_by_name": _r("search", "contact", STRUCT),
    "search_contacts_by_email": _r("search", "contact", STRUCT),
    "get_current_day": _r("retrieve", "system", OWN),
    "reschedule_calendar_event": _w("update", "calendar"),
    "add_calendar_event_participants": _w("update", "calendar", egress=True),
    "append_to_file": _w("update", "file"),
    "create_file": _w("create", "file"),
    "delete_file": _w("delete", "file", destructive=True),
    "share_file": _w("share", "file", egress=True),
    "search_files_by_filename": _r("search", "file", FREE),
    "get_file_by_id": _r("retrieve", "file", FREE),
    "list_files": _r("list", "file", FREE),
    "search_files": _r("search", "file", FREE),
}

# Fallback for tools outside the table (hallucinated names, other AgentDojo
# versions). Only the verb prefix is used; such calls are reported as unmapped.
_PREFIX_FALLBACK = (
    (("get_", "read_", "check_", "lookup_"), ("retrieve", READ, False, False)),
    (("list_",), ("list", READ, False, False)),
    (("search_", "find_"), ("search", READ, False, False)),
    (("send_",), ("send_message", WRITE, True, False)),
    (("post_", "publish_"), ("publish", WRITE, True, False)),
    (("pay_", "transfer_", "schedule_"), ("transfer_value", WRITE, True, False)),
    (("share_", "invite_"), ("share", WRITE, True, False)),
    (("create_", "add_"), ("create", WRITE, False, False)),
    (("update_", "set_", "append_", "reschedule_"), ("update", WRITE, False, False)),
    (("delete_", "remove_", "cancel_"), ("delete", WRITE, False, True)),
    (("reserve_", "book_"), ("reserve", WRITE, False, False)),
)

# Write tools that only reach other people when given recipients. The call is
# egress when this argument is non-empty (create_calendar_event sends invites).
_RECIPIENT_ARGS = {"create_calendar_event": "participants"}

_NAMESPACE_PREFIXES = ("functions.", "function.", "tools.")


def canonical_tool_name(raw) -> str:
    """Strip provider namespacing/whitespace/case from a tool name."""
    name = str(raw or "").strip()
    lowered = name.lower()
    for prefix in _NAMESPACE_PREFIXES:
        if lowered.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.strip().lower()


def lookup(tool_name: str) -> ToolSpec:
    """Return the spec of a canonical tool name (see canonical_tool_name)."""
    spec = TOOLS.get(tool_name)
    if spec is not None:
        return spec
    for prefixes, (action, effect, egress, destructive) in _PREFIX_FALLBACK:
        if tool_name.startswith(prefixes):
            return ToolSpec(action, effect, UNKNOWN, None, egress, destructive, False)
    return ToolSpec(UNKNOWN, UNKNOWN, UNKNOWN, None, False, False, False)


def adds_recipients(tool_name: str, arg_shape: dict) -> bool:
    """True when a normally internal write call names other people as recipients.

    Works on type descriptors (see descriptors.py), so only emptiness is known, never values.
    """
    key = _RECIPIENT_ARGS.get(tool_name)
    return bool(key) and key in arg_shape and is_nonempty(arg_shape[key])


def coarse_class(effect: str, egress: bool) -> str:
    """Three-letter alphabet used by sequence features: R, W, E (X = unknown)."""
    if effect == READ:
        return "R"
    if effect == WRITE:
        return "E" if egress else "W"
    return "X"
