from fastapi import APIRouter, HTTPException

from app.models.module_registry import ModuleRegistryResponse, OsModule
from app.services.module_registry_service import get_module, list_modules


router = APIRouter(prefix="/api/v1/modules", tags=["modules"])


@router.get("", response_model=ModuleRegistryResponse)
def get_modules():
    return ModuleRegistryResponse(modules=list_modules())


@router.get("/{module_id}", response_model=OsModule)
def get_module_detail(module_id: str):
    module = get_module(module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="模块不存在")
    return module
