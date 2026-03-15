import os

DIR = r'c:\Users\user\.gemini\antigravity\scratch\farmacia\templates'

for f in ['nueva.html', 'editar.html']:
    path = os.path.join(DIR, 'ventas', f)
    with open(path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Restore the broken literals
    content = content.replace('<h6></h6>', '<h6></h6>')
    content = content.replace('<span style=\"min-width: 30px; text-align: center; font-weight: 600; color: white;\"></span>', '<span style=\"min-width: 30px; text-align: center; font-weight: 600; color: white;\"></span>')
    content = content.replace('\'\'S/.\'', '\'S/.\'')
    content = content.replace('\'S/.\' +', '\'S/.\' +')
    
    with open(path, 'w', encoding='utf-8') as file:
        file.write(content)
