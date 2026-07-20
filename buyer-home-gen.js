const fs = require('fs');

let content = fs.readFileSync('c:/Users/Windows 10 Pro/Documents/YV2/index.html', 'utf8');

// Update paths
content = content.replace(/href="index\.css"/g, 'href="../index.css"');
content = content.replace(/src="index\.js"/g, 'src="../index.js"');
content = content.replace(/src="assets\//g, 'src="../assets/');
content = content.replace(/url\('assets\//g, 'url(\'../assets/');
content = content.replace(/href="login\.html"/g, 'href="../login.html"');

// Remove sections
content = content.replace(/<!-- THE 5Fs FRAMEWORK SECTION -->[\s\S]*?<!-- MEET THE AUTHOR SECTION -->/g, '<!-- MEET THE AUTHOR SECTION -->');
content = content.replace(/<!-- MEET THE AUTHOR SECTION -->[\s\S]*?<!-- MAIN SHOP & BROWSER SECTION -->/g, '<!-- MAIN SHOP & BROWSER SECTION -->');

// Update Nav Links
content = content.replace(/<li><a href="#philosophy-section".*?<\/li>/g, '');
content = content.replace(/<li><a href="#author-section".*?<\/li>/g, '');

// Update Hero text slightly to be purely buyer focused
content = content.replace(/Upgrade Your Life Like You <span class="text-gradient">Upgrade Your Apps<\/span>/, 'Discover Premium Books <span class="text-gradient">Tailored For You</span>');
content = content.replace(/Introducing <strong>YOU VERSION 2<\/strong> by Ollie G. Baldemor. Discover the\s*life-changing principles that apply the six phases of software development to your personal growth, faith, and\s*goals./, 'Welcome to the exclusive YouVersion storefront. Browse our curated selection of premium physical and digital editions designed to upgrade your mindset and skills.');

fs.writeFileSync('c:/Users/Windows 10 Pro/Documents/YV2/buyer/index.html', content);
console.log('done');
