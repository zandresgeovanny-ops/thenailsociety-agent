"""Extrae el JS de las páginas HTML del backend y lo valida con node.
Esto es lo que hay que correr SIEMPRE que se toque el JS embebido."""
import ast, re, subprocess, sys, pathlib

fallos = 0
for archivo in ["agent/panel.py", "agent/reservas.py", "agent/auth.py"]:
    src = pathlib.Path(archivo).read_text(encoding="utf-8")
    for n in ast.parse(src).body:
        if not (isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str) and len(n.value.value) > 2000):
            continue
        const = n.targets[0].id
        for i, js in enumerate(re.findall(r"<script>(.*?)</script>", n.value.value, re.S)):
            ruta = f"/tmp/chk_{const}_{i}.js"
            pathlib.Path(ruta).write_text(js, encoding="utf-8")
            r = subprocess.run(["node", "--check", ruta], capture_output=True, text=True)
            etiqueta = f"{archivo} · {const}[{i}]"
            if r.returncode == 0:
                print(f"  OK   {etiqueta}  ({len(js.splitlines())} lineas)")
            else:
                fallos += 1
                print(f"  FALLA {etiqueta}")
                print("       " + r.stderr.strip().splitlines()[1][:120])
sys.exit(1 if fallos else 0)
