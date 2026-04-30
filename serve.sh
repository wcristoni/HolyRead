#!/bin/bash
# Servidor local SOMENTE para o frontend (sem backend, sem módulo Original).
# Para a stack V1 completa (front + back + QR LAN), use ./scripts/dev.sh.
cd "$(dirname "$0")"
echo "🌐 HolyRead frontend em http://localhost:8080"
echo "   ⚠  Sem backend, o módulo Original não funciona."
echo "   Para V1 completo: ./scripts/dev.sh"
echo "   Pressione Ctrl+C para parar"
python3 -m http.server -d frontend 8080
