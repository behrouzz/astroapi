from fastapi import APIRouter, HTTPException
from starlette import status
from ..core.eopcalc import utc_to_eop


router = APIRouter(
    prefix='/eop',
    tags=['eop']
)


@router.get('/{utc_str}', status_code=status.HTTP_200_OK)
def get_eop_for_one_utc(utc_str: str):
    try:
        dc = utc_to_eop(utc_str)
        return dc
    except:
        raise HTTPException(status_code=404, detail="Can't find EOP. Time should be entered like this: 2024-02-10T22:32:37")