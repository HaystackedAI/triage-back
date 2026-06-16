from fastapi import APIRouter

from .fee import feeRou
from .item import itemRou
from .tax import taxRou
from .payment_method import pmRou

settingsRou = APIRouter()


settingsRou.include_router(feeRou,)
settingsRou.include_router(itemRou)
settingsRou.include_router(taxRou,)
settingsRou.include_router(pmRou, )