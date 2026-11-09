import httpx
from fastapi import APIRouter

from app.providers.manager import provider_manager
from app.services.provider_resilience_service import provider_resilience_service

router = APIRouter(prefix="/api/diagnostics", tags=["Diagnostics"])


@router.get("/providers")
async def provider_diagnostics() -> dict:
    states = provider_resilience_service.snapshot()
    providers = []
    for provider_id in provider_manager.registry.list_ids():
        state = states.get(provider_id, {
            "state": "available", "cooldown_remaining_seconds": 0.0,
            "consecutive_failures": 0, "last_error_kind": None,
            "last_error": None, "last_success": False, "probe_in_flight": False,
        })
        connected = None
        if state["state"] == "half_open":
            if provider_resilience_service.begin_recovery_probe(provider_id):
                try:
                    connected = await provider_manager.health(provider_id)
                    if connected:
                        provider_resilience_service.record_success(provider_id)
                    else:
                        provider_resilience_service.record_failure(
                            provider_id, httpx.ConnectError("Provider health check failed")
                        )
                except Exception as exc:
                    provider_resilience_service.record_failure(provider_id, exc)
                state = provider_resilience_service.snapshot().get(provider_id, state)
        elif state["state"] == "available":
            try:
                connected = await provider_manager.health(provider_id)
            except Exception:
                connected = False

        recommendations = []
        if connected is False:
            recommendations.append({
                "code": "connection_check", "level": "warning",
                "message": "Provider javob bermadi. Xizmat holati, endpoint manzili va autentifikatsiyani tekshiring."
            })
        if state["state"] == "cooldown":
            recommendations.append({
                "code": "wait_or_switch", "level": "warning",
                "message": "Provider vaqtincha kutish rejimida. Kutish tugashini kuzating yoki ruxsat etilgan boshqa provider’ni tanlang.",
            })
        elif state["state"] == "half_open":
            recommendations.append({
                "code": "recovery_probe", "level": "warning",
                "message": "Provider tiklanishi avtomatik tekshirilmoqda. Tekshiruv yakunlangach holat yangilanadi.",
            })
        if state["last_error_kind"] == "rate_limit" and state["state"] == "cooldown":
            recommendations.append({
                "code": "rate_limit", "level": "warning",
                "message": "So‘rovlar limiti oshgan. Retry-After muddati tugamaguncha yangi so‘rov yubormang.",
            })
        elif state["last_error_kind"] == "authentication":
            recommendations.append({
                "code": "credentials", "level": "error",
                "message": "Autentifikatsiya rad etildi. API kaliti va endpoint ruxsatlarini tekshiring; avtomatik retry bajarilmaydi.",
            })
        elif state["last_error_kind"] in ("timeout", "network_error", "server_error"):
            recommendations.append({
                "code": "connectivity", "level": "warning",
                "message": "Ulanish yoki server holatini tekshiring. Vaqtinchalik xatolar uchun cooldown avtomatik qo‘llanadi.",
            })
        providers.append({"provider_id": provider_id, "connected": connected, **state, "recommendations": recommendations})
    return {"providers": providers}
