const fs = require('fs');
const path = require('path');

// Create build directory
const buildDir = path.join(__dirname, '..', 'build');
if (!fs.existsSync(buildDir)) {
  fs.mkdirSync(buildDir, { recursive: true });
}

// Copy manifest
fs.copyFileSync(
  path.join(__dirname, '..', 'manifest.json'),
  path.join(buildDir, 'manifest.json')
);

// Copy directories
const dirsToCopy = [
  { src: 'src/background', dest: 'background' },
  { src: 'src/content', dest: 'content' },
  { src: 'src/popup', dest: 'popup' },
  { src: 'src/options', dest: 'options' },
  { src: 'src/shared', dest: 'shared' },
  { src: 'src/config', dest: 'config' },
  { src: 'assets', dest: 'assets' }
];

function copyDir(src, dest) {
  const srcPath = path.join(__dirname, '..', src);
  const destPath = path.join(buildDir, dest);
  
  if (!fs.existsSync(destPath)) {
    fs.mkdirSync(destPath, { recursive: true });
  }
  
  if (!fs.existsSync(srcPath)) {
    console.warn(`Source directory ${srcPath} does not exist, skipping...`);
    return;
  }
  
  const files = fs.readdirSync(srcPath);
  
  files.forEach(file => {
    const srcFile = path.join(srcPath, file);
    const destFile = path.join(destPath, file);
    
    const stat = fs.statSync(srcFile);
    
    if (stat.isDirectory()) {
      copyDir(path.join(src, file), path.join(dest, file));
    } else {
      fs.copyFileSync(srcFile, destFile);
    }
  });
}

dirsToCopy.forEach(({ src, dest }) => {
  console.log(`Copying ${src} to ${dest}...`);
  copyDir(src, dest);
});

console.log('Build complete! Extension files copied to ./build/');
console.log('Load the extension from Chrome by pointing to the build directory.');