from fastapi import APIRouter, Depends

from homelab_monitor.auth.dependencies import require_roles
from homelab_monitor.remote_access import RemoteAccessService
from homelab_monitor.schemas import RemoteAccessResponse

router = APIRouter(prefix="/api/v1/system", tags=["system"])
READ = Depends(require_roles("admin", "operator", "viewer"))
service = RemoteAccessService()


@router.get(
    "/remote-access",
    response_model=RemoteAccessResponse,
    dependencies=[READ],
    summary="Read Tailscale remote-access status",
)
def get_remote_access() -> RemoteAccessResponse:
    return service.snapshot()
