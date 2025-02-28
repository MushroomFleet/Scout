# 🔍 Scout File Organizer 📂

> Clean up your messy directories by sorting files into organized extension-based folders! 🧹✨

## Scout2 - Now Available! 🚀

Scout2 is an enhanced version with numerous improvements:

- ✅ **Copy mode** - Choose to either move or copy files
- 🎨 **Color-coded output** - Visually enhanced terminal experience
- ⚡ **Multi-threading** - Significantly faster processing of files
- 📊 **Enhanced reporting** - JSON/CSV export options for operation data
- 💾 **Configuration system** - Remembers your last used settings
- 🔄 **Rollback capability** - Automatic recovery from failed operations
- 📋 **Command-line interface** - Run with options without interactive prompts
- 🔧 **Better error handling** - Improved stability and reliability

## What is Scout? 🤔

Scout is a powerful yet simple file organization tool that takes the chaos of cluttered directories and transforms them into a neatly organized structure. 🌪️➡️🏗️

Scout will **look** 👀 at your target directory, **create** 🏗️ extension-based folders in your destination directory, and **move** 🚚 your files automatically!

## ✨ Features

- 📁 **Automatic organization** - Instantly sorts files by their extension types
- 🧠 **Smart sorting** - Creates subdirectories for each extension found
- 🚀 **Progress tracking** - Visual progress bars show you exactly what's happening
- 🔄 **Conflict resolution** - Intelligently handles duplicate filenames
- 🚫 **Subdirectory ignoring** - Focuses only on files in the target directory
- 🔍 **File extension analysis** - Identifies all unique file types in your directories
- 📊 **Summary statistics** - Provides a complete breakdown when finished

## 🛠️ Installation

### Easy Installation (Windows) 💻

1. Clone or download this repository 📥
2. Run the `install.bat` file by double-clicking it 🖱️
3. Wait for the setup to complete! ⏳
4. That's it! 🎉

The installation script will:
- 🔮 Create a Python virtual environment
- 📦 Install all required dependencies
- 🔧 Set everything up for you automatically

### Manual Installation 🛠️

If you prefer to install manually or are using a non-Windows system:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## 🚀 How to Use

### Quick Start (Windows) 🪄

1. Run `run.bat` by double-clicking it 🖱️
2. Enter the **source directory path** when prompted 📂
   - Example: `C:\Users\YourName\Downloads`
3. Enter the **destination directory path** when prompted 🏁
   - Example: `D:\OrganizedFiles`
4. Watch as Scout organizes your files! ✨

### Manual Usage 📝

If you prefer to run Scout manually or are using a non-Windows system:

```bash
# Activate the virtual environment if not already activated
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Run the script
python scout.py
```

## 🧩 How It Works

Scout will:

1. 🔍 Scan your specified source directory
2. 📊 Identify all unique file extensions
3. 🏗️ Create folders for each extension in your destination directory
4. 🚚 Move each file to its corresponding extension folder
5. 📝 Provide a detailed summary when complete

### Example 📋

If your source directory contains:
- document.pdf
- vacation.jpg
- notes.txt
- profile.jpg
- archive.zip

Scout will create the following structure in your destination:
```
destination/
├── pdf/
│   └── document.pdf
├── jpg/
│   ├── vacation.jpg
│   └── profile.jpg
├── txt/
│   └── notes.txt
└── zip/
    └── archive.zip
```

## 🐞 Troubleshooting

- ❓ **"Module not found" error**: Make sure you've run the installation script or manually installed the dependencies
- ❓ **Permission errors**: Ensure you have the necessary permissions to access the source and destination directories
- ❓ **Path not found**: Double-check that the paths you entered exist and are correctly formatted

## 📝 License

This project is open source and available under the MIT License. Feel free to use and modify it! 🆓

## 🙏 Acknowledgments

- 🌟 Thanks to the `tqdm` library for the awesome progress bars!
- 💻 Python's `pathlib` and `shutil` for making file operations a breeze!
- 🧙‍♂️ And YOU for using Scout to organize your digital life!

---

*Happy organizing!* 🎉🎊 *Never lose a file in the chaos again!* 🕵️‍♀️
