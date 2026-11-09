from typing import Literal

from pydantic import BaseModel


class UIPreferences(BaseModel):
    theme: Literal["dark", "light"] = "dark"
    sound_enabled: bool = False
    language: Literal["uz", "en"] = "uz"
