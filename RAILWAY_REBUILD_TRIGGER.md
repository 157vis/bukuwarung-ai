# Railway Build Trigger 2026-07-16 15:28 UTC+7

Memaksa Railway mendeteksi perubahan dan rebuild image Docker.

Changelog:
- Fix sys.path[0] = bukuwarung-ai (commit c6f7261)
- Fix TenantBridge -> get_tenant_core (commit c974264)

Railway sebelumnya stuck di image lama karena Nixpacks cache.
Force trigger file ini akan memastikan rebuild terjadi.