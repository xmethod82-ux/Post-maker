"""FSM states for the post creation wizard."""

from aiogram.fsm.state import State, StatesGroup


class PostStates(StatesGroup):
    # Step 1 — content
    waiting_content = State()

    # Step 2 — button builder (cyclic; repeated per button)
    waiting_button_type = State()   # url | webapp
    waiting_button_url = State()
    waiting_button_style = State()  # primary | success | danger
    waiting_button_label = State()
    waiting_button_row = State()    # same_row | new_row

    # Step 3 — rename draft
    waiting_draft_name = State()

    # Step 4 — preview / publish
    preview = State()
