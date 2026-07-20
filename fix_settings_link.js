const fs = require('fs');
const path = '.';
const files = fs.readdirSync(path).filter(f => f.endsWith('.html'));

files.forEach(f => {
  let p = path + '/' + f;
  let content = fs.readFileSync(p, 'utf8');
  const regex = /<a href="#" class="nav-item">\s*<i data-lucide="settings"><\/i><span>Settings<\/span>\s*<\/a>/g;
  if (regex.test(content)) {
    content = content.replace(regex, '<a href="seller-settings.html" class="nav-item">\n        <i data-lucide="settings"></i><span>Settings</span>\n      </a>');
    fs.writeFileSync(p, content);
  }
});
