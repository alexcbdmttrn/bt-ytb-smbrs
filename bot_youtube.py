# ANTES (v5.2) — abortaba con cualquier error de channels().list()
try:
    yt.channels().list(part="id", mine=True).execute()
except Exception as e:
    print(f"❌ El token de YouTube no responde...: {e}")
    sys.exit(1)
print("✅ Credenciales válidas (DeepSeek, Pexels, YouTube)")

# AHORA (v5.3) — tolera insufficientPermissions
try:
    yt.channels().list(part="id", mine=True).execute()
    print("✅ Credenciales válidas (DeepSeek, Pexels, YouTube con lectura).")
except HttpError as e:
    if "insufficientPermissions" in str(e) or "insufficient authentication scopes" in str(e):
        print("⚠️ El token no tiene permiso de LECTURA del canal (youtube.readonly).")
        print("   El bot publicará igual, pero SIN analytics ni búsqueda de demanda.")
        print("   elegir_tema usará solo scoring random + histórico propio vacío.")
        print("   ℹ️ Regenera el token con scope youtube.readonly para activar esas features.")
    elif "401" in str(e) or "invalid_grant" in str(e) or "invalid_token" in str(e):
        print(f"❌ YouTube token expirado o revocado: {e}")
        sys.exit(1)
    else:
        print(f"❌ Error inesperado autenticando YouTube: {e}")
        sys.exit(1)
