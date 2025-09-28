const { app, BrowserWindow, Menu, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

class SignalScopeApp {
  constructor() {
    this.mainWindow = null;
    this.serverProcess = null;
    this.isServerRunning = false;
  }

  createWindow() {
    // Create the browser window
    this.mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false,
        enableRemoteModule: true
      },
      icon: path.join(__dirname, 'assets', 'icon.png'),
      title: 'SignalScope Desktop'
    });

    // Load the app
    this.mainWindow.loadFile('index.html');

    // Open DevTools in development
    if (process.env.NODE_ENV === 'development') {
      this.mainWindow.webContents.openDevTools();
    }

    // Handle window closed
    this.mainWindow.on('closed', () => {
      this.mainWindow = null;
      this.stopServer();
    });
  }

  createMenu() {
    const template = [
      {
        label: 'File',
        submenu: [
          {
            label: 'Settings',
            accelerator: 'CmdOrCtrl+,',
            click: () => this.showSettings()
          },
          { type: 'separator' },
          {
            label: 'Exit',
            accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => app.quit()
          }
        ]
      },
      {
        label: 'Server',
        submenu: [
          {
            label: 'Start Server',
            click: () => this.startServer()
          },
          {
            label: 'Stop Server',
            click: () => this.stopServer()
          },
          { type: 'separator' },
          {
            label: 'Server Status',
            click: () => this.showServerStatus()
          }
        ]
      },
      {
        label: 'Help',
        submenu: [
          {
            label: 'About SignalScope',
            click: () => this.showAbout()
          },
          {
            label: 'Documentation',
            click: () => this.openDocumentation()
          }
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  startServer() {
    if (this.isServerRunning) {
      dialog.showMessageBox(this.mainWindow, {
        type: 'info',
        title: 'Server Status',
        message: 'SignalScope server is already running on port 8000'
      });
      return;
    }

    try {
      // Start the Python server
      const serverPath = path.join(__dirname, '..', 'servers', 'simple_telegram_server.py');
      
      if (!fs.existsSync(serverPath)) {
        dialog.showErrorBox('Error', 'Server file not found. Please ensure the installation is complete.');
        return;
      }

      this.serverProcess = spawn('python', [serverPath], {
        cwd: path.join(__dirname, '..'),
        stdio: 'pipe'
      });

      this.serverProcess.stdout.on('data', (data) => {
        console.log(`Server: ${data}`);
        this.mainWindow.webContents.send('server-log', data.toString());
      });

      this.serverProcess.stderr.on('data', (data) => {
        console.error(`Server Error: ${data}`);
        this.mainWindow.webContents.send('server-error', data.toString());
      });

      this.serverProcess.on('close', (code) => {
        console.log(`Server process exited with code ${code}`);
        this.isServerRunning = false;
        this.mainWindow.webContents.send('server-stopped', code);
      });

      this.isServerRunning = true;
      this.mainWindow.webContents.send('server-started');

      dialog.showMessageBox(this.mainWindow, {
        type: 'info',
        title: 'Server Started',
        message: 'SignalScope server is now running on http://localhost:8000'
      });

    } catch (error) {
      dialog.showErrorBox('Error', `Failed to start server: ${error.message}`);
    }
  }

  stopServer() {
    if (this.serverProcess) {
      this.serverProcess.kill();
      this.serverProcess = null;
      this.isServerRunning = false;
      this.mainWindow.webContents.send('server-stopped');
    }
  }

  showSettings() {
    // Open settings dialog
    const settingsWindow = new BrowserWindow({
      width: 600,
      height: 400,
      parent: this.mainWindow,
      modal: true,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false
      }
    });

    settingsWindow.loadFile('settings.html');
  }

  showServerStatus() {
    const status = this.isServerRunning ? 'Running' : 'Stopped';
    dialog.showMessageBox(this.mainWindow, {
      type: 'info',
      title: 'Server Status',
      message: `SignalScope server is ${status}`
    });
  }

  showAbout() {
    dialog.showMessageBox(this.mainWindow, {
      type: 'info',
      title: 'About SignalScope',
      message: 'SignalScope Desktop v1.3.0',
      detail: 'A comprehensive trading signal capture and forwarding system.\n\nFeatures:\n• Chrome Extension Integration\n• Telegram Bridge Server\n• Message Deduplication\n• Image/Chart Support'
    });
  }

  openDocumentation() {
    const { shell } = require('electron');
    shell.openExternal('https://github.com/your-repo/SignalScope');
  }
}

// App event handlers
const signalScopeApp = new SignalScopeApp();

app.whenReady().then(() => {
  signalScopeApp.createWindow();
  signalScopeApp.createMenu();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      signalScopeApp.createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  signalScopeApp.stopServer();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  signalScopeApp.stopServer();
});

// IPC handlers
ipcMain.handle('start-server', () => {
  signalScopeApp.startServer();
});

ipcMain.handle('stop-server', () => {
  signalScopeApp.stopServer();
});

ipcMain.handle('get-server-status', () => {
  return signalScopeApp.isServerRunning;
});
