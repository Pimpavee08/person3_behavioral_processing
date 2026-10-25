"""Model-visible parameters of the AgentDojo v1 tools, for missing/extra argument checks.

Transcribed from src/agentdojo/default_suites/v1/tools/*.py at the frozen
commit below. Parameters injected by AgentDojo (Depends(...)) are not visible
to the model and are left out. A parameter with "=" has a default (optional).
Only argument keys are compared; argument values are never read.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Optional, Tuple

SIGNATURE_SOURCE = "agentdojo@a75aba7631d3ca5fb7ab938965c97ead2f9ff84b"

_SIGNATURES = """
get_iban()
send_money(recipient, amount, subject, date)
schedule_transaction(recipient, amount, subject, date, recurring)
update_scheduled_transaction(id, recipient=, amount=, subject=, date=, recurring=)
get_balance()
get_most_recent_transactions(n=)
get_scheduled_transactions()
read_file(file_path)
get_user_info()
update_password(password)
update_user_info(first_name=, last_name=, street=, city=)
get_channels()
add_user_to_channel(user, channel)
read_channel_messages(channel)
read_inbox(user)
send_direct_message(recipient, body)
send_channel_message(channel, body)
get_users_in_channel(channel)
invite_user_to_slack(user, user_email)
remove_user_from_slack(user)
get_webpage(url)
post_webpage(url, content)
get_user_information()
get_all_hotels_in_city(city)
get_hotels_prices(hotel_names)
get_hotels_address(hotel_name)
get_rating_reviews_for_hotels(hotel_names)
get_all_restaurants_in_city(city)
get_restaurants_address(restaurant_names)
get_rating_reviews_for_restaurants(restaurant_names)
get_cuisine_type_for_restaurants(restaurant_names)
get_dietary_restrictions_for_all_restaurants(restaurant_names)
get_contact_information_for_restaurants(restaurant_names)
get_price_for_restaurants(restaurant_names)
check_restaurant_opening_hours(restaurant_names)
get_all_car_rental_companies_in_city(city)
get_car_types_available(company_name)
get_rating_reviews_for_car_rental(company_name)
get_car_rental_address(company_name)
get_car_fuel_options(company_name)
get_car_price_per_day(company_name)
reserve_hotel(hotel, start_day, end_day)
reserve_restaurant(restaurant, start_time)
reserve_car_rental(company, start_time, end_time)
get_flight_information(departure_city, arrival_city)
get_unread_emails()
send_email(recipients, subject, body, attachments=, cc=, bcc=)
search_emails(query, sender=)
delete_email(email_id)
get_sent_emails()
get_received_emails()
get_draft_emails()
search_contacts_by_name(query)
search_contacts_by_email(query)
get_current_day()
get_day_calendar_events(day)
create_calendar_event(title, start_time, end_time, description=, participants=, location=)
search_calendar_events(query, date=)
cancel_calendar_event(event_id)
reschedule_calendar_event(event_id, new_start_time, new_end_time=)
add_calendar_event_participants(event_id, participants)
search_files_by_filename(filename)
create_file(filename, content)
delete_file(file_id)
get_file_by_id(file_id)
list_files()
share_file(file_id, email, permission)
append_to_file(file_id, content)
search_files(query)
"""


def _parse(text: str) -> Dict[str, Tuple[FrozenSet[str], FrozenSet[str]]]:
    table = {}
    for line in filter(None, (l.strip() for l in text.splitlines())):
        name, params = line.rstrip(")").split("(")
        params = [p.strip() for p in params.split(",") if p.strip()]
        table[name] = (frozenset(p for p in params if not p.endswith("=")),
                       frozenset(p.rstrip("=") for p in params if p.endswith("=")))
    return table


SIGNATURES = _parse(_SIGNATURES)


def argument_mismatch(tool: str, keys: Iterable[str]) -> Tuple[Optional[int], Optional[int]]:
    """(missing required, extra) argument counts; (None, None) for a tool without a signature."""
    sig = SIGNATURES.get(tool)
    if sig is None:
        return None, None
    required, optional = sig
    keys = set(keys)
    return len(required - keys), len(keys - required - optional)
