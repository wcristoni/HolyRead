#!/bin/bash
# Servidor local para HolyRead
# Inicia em http://localhost:8080
cd "$(dirname "$0")"
echo "🌐 HolyRead rodando em http://localhost:8080"
echo "   Pressione Ctrl+C para parar"
python3 -m http.server 8080
