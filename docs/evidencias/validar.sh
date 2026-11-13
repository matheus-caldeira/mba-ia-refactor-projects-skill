#!/usr/bin/env bash
# Sobe os 3 projetos refatorados, executa um roteiro de requisições e imprime o log.
# Uso (na raiz do repo): bash docs/evidencias/validar.sh "$PWD" "$(mktemp -d)"
set -u
ROOT=$1; TMP=$2; rm -f "$TMP"/*.db
K=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
noise='blake2|Traceback|File "|globals\(\)|return __|raise Value|ValueError|^[[:space:]]+\^'
req(){ # req LABEL curl-args...
  local label=$1; shift
  local out code body
  out=$(curl -s -w $'\n%{http_code}' "$@"); code=${out##*$'\n'}; body=${out%$'\n'*}
  printf '%-58s -> %s | %.110s\n' "$label" "$code" "$body"
}
tok(){ python3 -c 'import sys,json;print(json.load(sys.stdin).get("token",""))'; }
wait_up(){ for _ in $(seq 1 40); do curl -s -o /dev/null "$1" && return; perl -e 'select(undef,undef,undef,0.25)'; done; }
J='Content-Type: application/json'

echo "### Projeto 1 — code-smells-project (Python/Flask)"
echo '$ APP_ENV=development SECRET_KEY=<aleatória> PORT=5191 ./venv/bin/python app.py'
(cd "$ROOT/code-smells-project" && APP_ENV=development SECRET_KEY=$K DB_PATH=$TMP/loja.db PORT=5191 ./venv/bin/python app.py >"$TMP/p1.log" 2>&1 &)
wait_up localhost:5191/health
grep -vE "$noise" "$TMP/p1.log" | grep -v werkzeug | head -3
A=$(curl -s -X POST localhost:5191/login -H "$J" -d '{"email":"admin@loja.com","senha":"admin123"}' | tok)
C=$(curl -s -X POST localhost:5191/login -H "$J" -d '{"email":"joao@email.com","senha":"123456"}' | tok)
req "GET  /health" localhost:5191/health
req "GET  /produtos" localhost:5191/produtos
req "GET  /produtos/busca?q=mouse" "localhost:5191/produtos/busca?q=mouse"
req "GET  /produtos/1" localhost:5191/produtos/1
req "POST /login (SQL injection: admin@loja.com' --)" -X POST localhost:5191/login -H "$J" -d "{\"email\":\"admin@loja.com' --\",\"senha\":\"x\"}"
req "GET  /usuarios (sem token)" localhost:5191/usuarios
req "GET  /usuarios (admin)" -H "Authorization: Bearer $A" localhost:5191/usuarios
req "GET  /usuarios/1 (cliente joao)" -H "Authorization: Bearer $C" localhost:5191/usuarios/1
req "POST /pedidos (cliente joao)" -X POST -H "Authorization: Bearer $C" -H "$J" localhost:5191/pedidos -d '{"itens":[{"produto_id":2,"quantidade":1}]}'
req "POST /pedidos (quantidade negativa)" -X POST -H "Authorization: Bearer $C" -H "$J" localhost:5191/pedidos -d '{"itens":[{"produto_id":2,"quantidade":-5}]}'
req "GET  /pedidos (admin)" -H "Authorization: Bearer $A" localhost:5191/pedidos
req "GET  /relatorios/vendas (admin)" -H "Authorization: Bearer $A" localhost:5191/relatorios/vendas
req "POST /admin/query (removida)" -X POST localhost:5191/admin/query -H "$J" -d '{"sql":"SELECT 1"}'
echo

echo "### Projeto 2 — ecommerce-api-legacy (Node.js/Express)"
echo '$ NODE_ENV=development PAYMENT_GATEWAY_KEY=<teste> AUTH_SECRET=<aleatório> PORT=3191 node src/app.js'
(cd "$ROOT/ecommerce-api-legacy" && NODE_ENV=development PORT=3191 PAYMENT_GATEWAY_KEY=pk_test_local AUTH_SECRET=$K node src/app.js >"$TMP/p2.log" 2>&1 &)
wait_up localhost:3191/
head -2 "$TMP/p2.log"
A=$(curl -s -X POST localhost:3191/api/auth/login -H "$J" -d '{"email":"admin@lms.local","password":"admin-dev-only"}' | tok)
req "POST /api/checkout (cartão 4...)" -X POST localhost:3191/api/checkout -H "$J" -d '{"usr":"Gui","eml":"gui@x.com","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
req "POST /api/checkout (cartão 5..., recusado)" -X POST localhost:3191/api/checkout -H "$J" -d '{"usr":"Ana","eml":"ana@x.com","pwd":"senhaforte","c_id":1,"card":"5111222233334444"}'
req "POST /api/checkout (card numérico; antes derrubava)" -X POST localhost:3191/api/checkout -H "$J" -d '{"usr":"Bob","eml":"bob@x.com","pwd":"senhaforte","c_id":1,"card":4111222233334444}'
req "POST /api/auth/login (admin)" -X POST localhost:3191/api/auth/login -H "$J" -d '{"email":"admin@lms.local","password":"admin-dev-only"}'
req "GET  /api/admin/financial-report (sem token)" localhost:3191/api/admin/financial-report
req "GET  /api/admin/financial-report (admin)" -H "Authorization: Bearer $A" localhost:3191/api/admin/financial-report
req "DELETE /api/users/1 (sem token)" -X DELETE localhost:3191/api/users/1
req "DELETE /api/users/999 (admin)" -X DELETE -H "Authorization: Bearer $A" localhost:3191/api/users/999
echo "log do servidor:"; grep -E 'payment' "$TMP/p2.log" | head -2
echo

echo "### Projeto 3 — task-manager-api (Python/Flask)"
echo '$ APP_ENV=development SECRET_KEY=<aleatória> ./venv/bin/python seed.py && PORT=5193 ./venv/bin/python app.py'
(cd "$ROOT/task-manager-api" && APP_ENV=development SECRET_KEY=$K DATABASE_URL=sqlite:///$TMP/tasks.db ./venv/bin/python seed.py 2>&1 | grep -vE "$noise")
(cd "$ROOT/task-manager-api" && APP_ENV=development SECRET_KEY=$K DATABASE_URL=sqlite:///$TMP/tasks.db PORT=5193 ./venv/bin/python app.py >"$TMP/p3.log" 2>&1 &)
wait_up localhost:5193/health
A=$(curl -s -X POST localhost:5193/login -H "$J" -d '{"email":"joao@email.com","password":"1234"}' | tok)
U=$(curl -s -X POST localhost:5193/login -H "$J" -d '{"email":"maria@email.com","password":"abcd"}' | tok)
req "GET  /health" localhost:5193/health
req "GET  /tasks (sem token)" localhost:5193/tasks
req "POST /login (token: fake-jwt-token → assinado)" -X POST localhost:5193/login -H "$J" -d '{"email":"maria@email.com","password":"abcd"}'
for p in tasks tasks/1 tasks/stats "tasks/search?q=a" users users/1 categories reports/summary reports/user/1; do
  req "GET  /$p (admin)" -H "Authorization: Bearer $A" "localhost:5193/$p"
done
req "GET  /reports/summary (user comum)" -H "Authorization: Bearer $U" localhost:5193/reports/summary
req "POST /users com role=admin (anônimo)" -X POST localhost:5193/users -H "$J" -d '{"name":"X","email":"x@y.com","password":"abcdef12","role":"admin"}'
req "PUT  /users/1 role=user (user comum)" -X PUT -H "Authorization: Bearer $U" -H "$J" localhost:5193/users/1 -d '{"role":"user"}'
printf '%-58s -> %s\n' 'ocorrências de "password" em GET /users/1' "$(curl -s -H "Authorization: Bearer $A" localhost:5193/users/1 | grep -c '"password"')"

lsof -ti:5191,3191,5193 | xargs kill 2>/dev/null
rm -f "$TMP"/*.db
