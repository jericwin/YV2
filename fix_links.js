const fs = require('fs');
const path = '.';
const files = fs.readdirSync(path).filter(f => f.endsWith('.html'));

files.forEach(f => {
  let p = path + '/' + f;
  let content = fs.readFileSync(p, 'utf8');
  const regex = /<button class="action-btn" title="Notifications">([\s\S]*?)<\/button>/g;
  if (regex.test(content)) {
    content = content.replace(regex, '<a href="seller-notifications.html" class="action-btn" title="Notifications">$1</a>');
    fs.writeFileSync(p, content);
  }
});
