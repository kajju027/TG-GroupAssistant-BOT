from aiogram.fsm.state import State, StatesGroup


class PanelInput(StatesGroup):
    """Text-input steps used by the private settings panels."""
    antilink_domain = State()      # allow a domain in anti-link
    antilink_remove = State()      # remove a whitelisted domain
    antiword_add = State()         # add a banned word
    antiword_remove = State()      # remove a banned word
    welcome_text = State()         # set the welcome message
    goodbye_text = State()         # set the goodbye message
    filter_keyword = State()       # add filter: keyword step
    filter_reply = State()         # add filter: reply step
