const fs = require('fs');
const path = require('path');

const dir = 'c:\\Users\\E36250409\\Desktop\\Nano Sam\\ussop\\frontend\\src';

function walk(dir, callback) {
    fs.readdirSync(dir).forEach(f => {
        let dirPath = path.join(dir, f);
        let isDirectory = fs.statSync(dirPath).isDirectory();
        isDirectory ? walk(dirPath, callback) : callback(path.join(dir, f));
    });
}

walk(dir, function (filePath) {
    if (filePath.endsWith('.tsx') || filePath.endsWith('.ts')) {
        let content = fs.readFileSync(filePath, 'utf-8');
        let original = content;

        // regex to match uppercase and tracking classes
        // replace uppercase and adjacent tracking
        content = content.replace(/\buppercase\s+tracking-[A-Za-z0-9\.\[\]-]+\b/g, 'capitalize');
        content = content.replace(/\btracking-[A-Za-z0-9\.\[\]-]+\s+uppercase\b/g, 'capitalize');
        content = content.replace(/\buppercase\b/g, 'capitalize');

        // some places we had tracking on the same line but separated, let's just also remove tracking if it's right next to capitalize
        content = content.replace(/\bcapitalize\s+tracking-[A-Za-z0-9\.\[\]-]+\b/g, 'capitalize');
        content = content.replace(/\btracking-[A-Za-z0-9\.\[\]-]+\s+capitalize\b/g, 'capitalize');

        if (content !== original) {
            fs.writeFileSync(filePath, content, 'utf-8');
            console.log('Updated', filePath);
        }
    }
});
