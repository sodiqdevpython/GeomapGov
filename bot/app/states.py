from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    waiting_first_name = State()
    waiting_last_name = State()
    waiting_phone = State()


class ReportCreate(StatesGroup):
    waiting_description = State()
    collecting_media = State()
    waiting_location = State()
    confirm = State()


class BrowseReports(StatesGroup):
    browsing = State()
    choosing_file = State()
