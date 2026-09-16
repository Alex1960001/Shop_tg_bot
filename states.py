from aiogram.fsm.state import State, StatesGroup


class CheckoutState(StatesGroup):
    name = State()
    phone = State()
    delivery = State()
    address = State()
    payment = State()
    confirmation = State()


class AdminCategoryCreateState(StatesGroup):
    name_ru = State()
    name_cs = State()
    name_uk = State()
    sort_order = State()


class AdminCategoryEditState(StatesGroup):
    name_ru = State()
    name_cs = State()
    name_uk = State()
    sort_order = State()


class AdminProductCreateState(StatesGroup):
    name_ru = State()
    name_cs = State()
    name_uk = State()
    description_ru = State()
    description_cs = State()
    description_uk = State()
    price = State()
    photo = State()


class AdminProductEditState(StatesGroup):
    name_ru = State()
    name_cs = State()
    name_uk = State()
    description_ru = State()
    description_cs = State()
    description_uk = State()
    price = State()


class AdminProductPhotoState(StatesGroup):
    photo = State()
