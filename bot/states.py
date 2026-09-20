from aiogram.fsm.state import State, StatesGroup


class PanelInput(StatesGroup):
    antilink_allow_domain = State()
    antilink_disallow_domain = State()
    antiword_add_word = State()
    antiword_remove_word = State()
    antifake_add_prefix = State()
    antifake_remove_prefix = State()
    welcome_message = State()
    goodbye_message = State()
    reaction_custom_emojis = State()
    filter_add_keyword = State()
    filter_add_reply = State()
    filter_remove_keyword = State()
