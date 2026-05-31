"""Backward-compatible wrapper around messenger_api for Bale-only call sites."""

from __future__ import annotations

from balebot.models import Platform
from balebot.services import messenger_api

BaleAPIError = messenger_api.MessengerAPIError

call_method = lambda method, **kwargs: messenger_api.call_method(Platform.BALE, method, **kwargs)
get_me = lambda: messenger_api.get_me(Platform.BALE)
send_message = lambda chat_id, text, **kwargs: messenger_api.send_message(Platform.BALE, chat_id, text, **kwargs)
send_photo = lambda chat_id, **kwargs: messenger_api.send_photo(Platform.BALE, chat_id, **kwargs)
send_video = lambda chat_id, **kwargs: messenger_api.send_video(Platform.BALE, chat_id, **kwargs)
send_voice = lambda chat_id, **kwargs: messenger_api.send_voice(Platform.BALE, chat_id, **kwargs)
send_document = lambda chat_id, **kwargs: messenger_api.send_document(Platform.BALE, chat_id, **kwargs)
edit_message_reply_markup = lambda chat_id, message_id, **kwargs: messenger_api.edit_message_reply_markup(
    Platform.BALE, chat_id, message_id, **kwargs
)
answer_callback_query = lambda callback_query_id, **kwargs: messenger_api.answer_callback_query(
    Platform.BALE, callback_query_id, **kwargs
)
get_file = lambda file_id: messenger_api.get_file(Platform.BALE, file_id)
file_download_url = lambda file_path: messenger_api.file_download_url(Platform.BALE, file_path)
download_file_to_path = lambda file_id, dest: messenger_api.download_file_to_path(Platform.BALE, file_id, dest)
set_webhook = lambda url: messenger_api.set_webhook(Platform.BALE, url)
delete_webhook = lambda: messenger_api.delete_webhook(Platform.BALE)
sleep_after_rate_limit = messenger_api.sleep_after_rate_limit
