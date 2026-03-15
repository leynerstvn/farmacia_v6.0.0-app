import os
import re

DIR = r'c:\Users\user\.gemini\antigravity\scratch\farmacia\templates'

for root, _, files in os.walk(DIR):
    for f in files:
        if f.endswith('.html'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Replaces that are safe to do globally
            # In HTML UI (like table headers or text)
            content = content.replace('Precio ($)', 'Precio (S/.)')
            content = content.replace('($)', '(S/.)')
            content = content.replace('>$0.00', '>S/.0.00')
            content = content.replace('>$', '>S/.')
            content = content.replace('{{ \'$\'', '{{ \'S/.\'')
            
            # Precise currency Jinja formats: ${{ "%.2f"|format(x) }}
            content = content.replace('${{ ', 'S/.{{ ')
            
            # Precise JS UI Strings: '$' + variable
            content = content.replace('\'$\'', '\'S/.\'')
            
            with open(path, 'w', encoding='utf-8') as file:
                file.write(content)
