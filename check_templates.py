# check_templates.py
import os
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

errors = 0
for root, _, files in os.walk(TEMPLATE_DIR):
    for name in files:
        if not name.endswith('.html'):
            continue
        rel = os.path.relpath(os.path.join(root, name), TEMPLATE_DIR).replace('\\', '/')
        try:
            env.get_template(rel)
            print(f'OK   {rel}')
        except TemplateSyntaxError as e:
            errors += 1
            print(f'FAIL {rel}: строка {e.lineno} — {e.message}')

print()
print('Ошибок:', errors)