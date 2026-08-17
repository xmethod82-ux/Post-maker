"""FSM states for channel connection flow."""

from aiogram.fsm.state import State, StatesGroup


class ChannelStates(StatesGroup):
    waiting_channel_input = State()   # User provides @username or -100id
    confirming_disconnect = State()   # Confirm before removing a channel
