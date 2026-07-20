const fs = require('fs');
const path = require('path');

const rootDir = '.';
const sellerDir = path.join(rootDir, 'seller');

if (!fs.existsSync(sellerDir)) {
  fs.mkdirSync(sellerDir);
}

// 1. Move files
const files = fs.readdirSync(rootDir);
const sellerFiles = files.filter(f => f.startsWith('seller-') && f.endsWith('.html'));

sellerFiles.forEach(f => {
  fs.renameSync(path.join(rootDir, f), path.join(sellerDir, f));
});

// 2. Update links inside seller pages
const newSellerFiles = fs.readdirSync(sellerDir).filter(f => f.endsWith('.html'));
newSellerFiles.forEach(f => {
  const filePath = path.join(sellerDir, f);
  let content = fs.readFileSync(filePath, 'utf8');
  
  content = content.replace(/href="index\.css"/g, 'href="../index.css"');
  content = content.replace(/href="index\.html"/g, 'href="../index.html"');
  content = content.replace(/href="login\.html"/g, 'href="../login.html"');
  content = content.replace(/href="signup\.html"/g, 'href="../signup.html"');
  content = content.replace(/src="assets\//g, 'src="../assets/');
  
  fs.writeFileSync(filePath, content);
});

// 3. Update links in root files
const rootHtmlFiles = fs.readdirSync(rootDir).filter(f => f.endsWith('.html') && !f.startsWith('seller-'));
rootHtmlFiles.forEach(f => {
  const filePath = path.join(rootDir, f);
  let content = fs.readFileSync(filePath, 'utf8');
  
  let modified = false;
  sellerFiles.forEach(sf => {
    // match href="seller-..." 
    const regexHref = new RegExp(`href="${sf}"`, 'g');
    if (regexHref.test(content)) {
      content = content.replace(regexHref, `href="seller/${sf}"`);
      modified = true;
    }
    // match js redirects like window.location.href = 'seller-dashboard.html'
    const regexJs = new RegExp(`'${sf}'`, 'g');
    if (regexJs.test(content)) {
      content = content.replace(regexJs, `'seller/${sf}'`);
      modified = true;
    }
    const regexJsDouble = new RegExp(`"${sf}"`, 'g');
    if (regexJsDouble.test(content)) {
      content = content.replace(regexJsDouble, `"seller/${sf}"`);
      modified = true;
    }
  });
  
  if (modified) {
    fs.writeFileSync(filePath, content);
  }
});
console.log("Migration complete!");
