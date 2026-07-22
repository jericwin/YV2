import os
import re

pattern = re.compile(r'<span\s+class="logo-icon"[^>]*>\s*<i\s+data-lucide="book-open"[^>]*>\s*</i>\s*</span>', re.IGNORECASE)

count = 0
for root, dirs, files in os.walk('.'):
    if 'node_modules' in dirs: dirs.remove('node_modules')
    if '.git' in dirs: dirs.remove('.git')
    for file in files:
        if file.endswith('.html'):
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            new_content = pattern.sub('', content)
            if content != new_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                count += 1
                print(f"Updated {filepath}")
print(f"Done. Replaced in {count} files.")
