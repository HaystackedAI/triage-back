from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.auth import get_zjwt
from app.db.conn.pgconn import get_rls_conn
from app.schemas.sch_acc_coa import COACreate, COAOut, COATreeOut, COAUpdate
from app.schemas.sch_ai import JWType
from app.service.acc.coa import (
    apply_coa_template,
    apply_generic_coa_template,
    create_coa_account,
    delete_coa_account,
    get_coa_account,
    get_coa_template_response,
    get_generic_coa_template,
    list_coa,
    list_coa_tree,
    list_coa_template_summaries,
    update_coa_account,
)

router = APIRouter(prefix="/coa", tags=["coa"])


@router.get("/get_list_all", response_model=list[COAOut])
async def list_coa_all(
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> list[COAOut]:
    return await list_coa(conn=conn, active_only=False)


@router.get("/get_list_active", response_model=list[COAOut])
async def list_coa_active(
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> list[COAOut]:
    return await list_coa(conn=conn)


@router.get("/get_tree", response_model=list[COATreeOut])
async def get_coa_tree(
    active_only: bool = False,
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> list[COATreeOut]:
    return await list_coa_tree(conn=conn, active_only=active_only)


@router.get("/get_one/{coa_id}", response_model=COAOut)
async def get_coa(
    coa_id: UUID,
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> COAOut:
    return await get_coa_account(conn=conn, coa_id=coa_id)





@router.post("/post_new", response_model=COAOut, status_code=status.HTTP_201_CREATED)
async def create_coa(
    payload: COACreate,
    zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> COAOut:
    return await create_coa_account(conn=conn, zjwt=zjwt, payload=payload)


@router.patch("/patch/{coa_id}", response_model=COAOut)
async def update_coa(
    coa_id: UUID,
    payload: COAUpdate,
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> COAOut:
    return await update_coa_account(conn=conn, coa_id=coa_id, payload=payload)


@router.delete("/delete/{coa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coa(
    coa_id: UUID,
    _zjwt: JWType = Depends(get_zjwt),
    conn: AsyncConnection = Depends(get_rls_conn),
) -> None:
    await delete_coa_account(conn=conn, coa_id=coa_id)




# @router.get("/templates")
# async def get_templates() -> dict[str, object]:
#     return list_coa_template_summaries()


# @router.get("/templates/generic")
# async def get_generic_template() -> dict[str, object]:
#     return get_generic_coa_template()


# @router.get("/templates/{template_key}")
# async def get_template(template_key: str) -> dict[str, object]:
#     return get_coa_template_response(template_key)


# @router.post("/templates/generic/apply")
# async def apply_generic_template(
#     zjwt: JWType = Depends(get_zjwt),
#     conn: AsyncConnection = Depends(get_pgconn),
# ) -> dict:
#     return await apply_generic_coa_template(conn=conn, zjwt=zjwt)


# @router.post("/templates/{template_key}/apply")
# async def apply_template(
#     template_key: str,
#     zjwt: JWType = Depends(get_zjwt),
#     conn: AsyncConnection = Depends(get_pgconn),
# ) -> dict:
#     return await apply_coa_template(conn=conn, zjwt=zjwt, template_key=template_key)


