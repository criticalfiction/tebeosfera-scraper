'''Finds class bodies where a name is assigned and later redefined as a
property/method (which silently replaces the plain value).'''
import ast, glob, sys

found = 0
for path in sorted(glob.glob('src/*.py')):
    src = open(path, encoding='utf-8').read()
    # make py2 syntax parseable: 'except X, e:' and 'print x'
    import re
    src = re.sub(r'except\s+(\w+)\s*,\s*(\w+)\s*:', r'except \1 as \2:', src)
    src = re.sub(r'^(\s*)print (.+)$', r'\1print(\2)', src, flags=re.M)
    tree = ast.parse(src)
    for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
        assigned = {}
        for node in cls.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        assigned[t.id] = node.lineno
            elif isinstance(node, ast.FunctionDef) and node.name in assigned:
                print('%s: class %s: "%s" assigned line %d, redefined line %d'
                      % (path, cls.name, node.name, assigned[node.name], node.lineno))
                found += 1
print('shadowed names:', found)
