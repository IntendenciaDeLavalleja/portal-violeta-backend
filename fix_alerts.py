import os
import glob
import re

for filepath in glob.glob('app/templates/**/*.html', recursive=True):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = re.sub(
        r'if\(\s*confirm\((.*?)\)\s*\)\s*\\.submit\(\)',
        r'customConfirm(\1).then(res => { if(res) .submit(); })',
        content,
        flags=re.DOTALL
    )

    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {filepath}")
