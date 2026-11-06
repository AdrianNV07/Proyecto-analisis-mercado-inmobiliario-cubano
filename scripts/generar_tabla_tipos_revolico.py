import json

def cargar(ruta):
    return [json.loads(l) for l in open(ruta, encoding='utf-8') if l.strip()]

hab = cargar('data/processed/habana_limpio.jsonl')

def tabla(filas, etiqueta):
    print('===', etiqueta, '===')
    grupos = {}
    for r in filas:
        t = r.get('tipo_inmueble')
        grupos.setdefault(t, []).append(r)
    n_total = len(filas)
    print('| Tipo de inmueble | N anuncios | % del total | Precio mediano (USD) |')
    print('|---|---|---|---|')
    for t in sorted(grupos, key=lambda k: -len(grupos[k])):
        g = grupos[t]
        n = len(g)
        pct = 100 * n / n_total if n_total else 0
        precios = sorted([r.get('precio_usd') for r in g if r.get('precio_usd') is not None])
        med = precios[len(precios) // 2] if precios else None
        med_txt = ('%.0f' % med) if med is not None else 'n/d'
        print('| ' + str(t) + ' | ' + str(n) + ' | ' + ('%.1f' % pct) + '% | ' + med_txt + ' |')
    print()

tabla(hab, 'LA HABANA (Pilar 1 - Revolico, todos los municipios) - n=' + str(len(hab)))
tabla([r for r in hab if r.get('municipio') == 'Playa'], 'PLAYA (caso de estudio - Revolico, municipio=Playa) - n=' + str(len([r for r in hab if r.get('municipio') == 'Playa'])))
