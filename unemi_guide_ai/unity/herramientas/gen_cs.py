from campus_data import *
def f(v): return f"{v}f"
def q(s): return '"' + s.replace('"','\\"') + '"'
out=[]
w=out.append
w("// ARCHIVO GENERADO a partir del plano del campus UNEMI (Milagro).")
w("// Unidades: metros. X = Este, Z = Norte. Rotación en grados (horario visto desde arriba).")
w(f"// Escala usada: {S} m por píxel del plano. Origen (0,0,0) = centro aproximado del campus.")
w("// Colores: cada edificio trae su color en formato #RRGGBB (último parámetro).")
w("// Puedes corregir cualquier valor aquí y volver a ejecutar  UNEMI > Generar Campus 3D.")
w("using UnityEngine;\n\nnamespace UNEMI.Campus\n{")
w("    public static class CampusData\n    {")
w("        public const float MetrosPorPixelPlano = %sf;\n" % S)
COL=colores()
w("        public static readonly EdificioDef[] Edificios =\n        {")
for (i,n,t,cx,cy,wd,d,r,h,st) in EDIFICIOS:
    x,z=m(cx,cy)
    w(f"            new EdificioDef({q(i)}, {q(n)}, TipoLugar.{t}, {f(x)}, {f(z)}, {f(L(wd))}, {f(L(d))}, {f(r)}, {f(h)}, {q(COL[i])}),")
w("        };\n")
w("        public static readonly ArcoDef[] Arcos =\n        {")
for (i,n,cx,cy,ri,ro,a0,a1,h,st) in ARCOS:
    x,z=m(cx,cy)
    w(f"            new ArcoDef({q(i)}, {q(n)}, {f(x)}, {f(z)}, {f(L(ri))}, {f(L(ro))}, {f(a0)}, {f(a1)}, {f(h)}, {q(COL[i])}),")
w("        };\n")
w("        public static readonly AreaDef[] Areas =\n        {")
for (i,n,t,cx,cy,wd,d,r,st) in AREAS:
    x,z=m(cx,cy)
    w(f"            new AreaDef({q(i)}, {q(n)}, TipoLugar.{t}, {f(x)}, {f(z)}, {f(L(wd))}, {f(L(d))}, {f(r)}, {q(st)}),")
w("        };\n")
i,n,cx,cy,wd,d,r=ESTADIO; x,z=m(cx,cy)
w(f"        public static readonly AreaDef Estadio = new AreaDef({q(i)}, {q(n)}, TipoLugar.Deportivo, {f(x)}, {f(z)}, {f(L(wd))}, {f(L(d))}, {f(r)}, \"pista\");\n")
w("        public static readonly PuntoDef[] Entradas =\n        {")
for (i,n,t,cx,cy) in ENTRADAS:
    x,z=m(cx,cy); w(f"            new PuntoDef({q(i)}, {q(n)}, TipoLugar.{t}, {f(x)}, {f(z)}),")
w("        };\n")
i,n,cx,cy=MONUMENTO; x,z=m(cx,cy)
w(f"        public static readonly PuntoDef Monumento = new PuntoDef({q(i)}, {q(n)}, TipoLugar.Monumento, {f(x)}, {f(z)});\n")
def pts(P): return "new[] { " + ", ".join(f"new Vector2({f(m(a,b)[0])}, {f(m(a,b)[1])})" for a,b in P) + " }"
w("        public static readonly LineaDef[] Calles =\n        {")
for (n,wd,st,P) in CALLES:
    w(f"            new LineaDef({q(n)}, {f(wd)}, {q(st)}, {pts(P)}),")
w("        };\n")
n,wd,P=ESTERO
w(f"        public static readonly LineaDef Estero = new LineaDef({q(n)}, {f(wd)}, \"estero\", {pts(P)});")
w("    }\n}")
# Se escribe junto a los scripts de Unity, sin importar desde qué carpeta se ejecute
import os
destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Assets", "UNEMI", "Scripts", "CampusData.cs")
with open(destino, "w", encoding="utf-8", newline="\n") as archivo:
    archivo.write("\n".join(out) + "\n")
print("Generado:", os.path.normpath(destino))

# El mismo campus para la web y Django (backend/web/static/web/data/campus_unemi.json)
import gen_web
gen_web.main()
